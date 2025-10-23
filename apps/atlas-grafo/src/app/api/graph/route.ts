import { NextResponse } from "next/server";

import { getSupabaseServiceClient } from "@/lib/supabase";

type RawRelation = {
  id: string;
  tipo: string;
  descricao: string | null;
  urn_alvo: string | null;
  criado_em: string | null;
  ato: {
    id: string;
    urn_lexml: string | null;
    titulo: string | null;
    tipo_ato: string | null;
    status_vigencia: string | null;
    data_legislacao: string | null;
  } | null;
  dispositivo_origem: {
    id: string;
    rotulo: string | null;
    texto: string | null;
  } | null;
  dispositivo_alvo: {
    id: string;
    rotulo: string | null;
    texto: string | null;
    ato: {
      id: string;
      urn_lexml: string | null;
      titulo: string | null;
      tipo_ato: string | null;
      status_vigencia: string | null;
      data_legislacao: string | null;
    } | null;
  } | null;
};

type GraphNode = {
  id: string;
  label: string;
  tipo?: string | null;
  status?: string | null;
  data?: string | null;
  count: number;
  unknown?: boolean;
};

type GraphLink = {
  id: string;
  source: string;
  target: string;
  tipo: string;
  descricao?: string | null;
  criadoEm?: string | null;
  origemRotulo?: string | null;
  origemTexto?: string | null;
  alvoTexto?: string | null;
};

function upsertNode(map: Map<string, GraphNode>, payload: GraphNode): GraphNode {
  const existing = map.get(payload.id);
  if (existing) {
    existing.count += 1;
    existing.tipo ??= payload.tipo;
    existing.status ??= payload.status;
    existing.data ??= payload.data;
    existing.label = existing.label || payload.label;
    existing.unknown &&= payload.unknown ?? true;
    return existing;
  }
  map.set(payload.id, payload);
  return payload;
}

export async function GET(request: Request) {
  let supabase: ReturnType<typeof getSupabaseServiceClient>;
  try {
    supabase = getSupabaseServiceClient();
  } catch (error) {
    console.error("Supabase configuration error", error);
    return NextResponse.json(
      { error: "Configuração do Supabase ausente." },
      { status: 500 },
    );
  }

  const { searchParams } = new URL(request.url);
  const limitParam = Number(searchParams.get("limit") ?? "400");
  const limit = Number.isFinite(limitParam) ? Math.min(Math.max(limitParam, 1), 2000) : 400;
  const urnFilter = searchParams.get("urn");

  const relationSelect = `
        id,
        tipo,
        descricao,
        urn_alvo,
        criado_em,
        ato:ato_id (
          id,
          urn_lexml,
          titulo,
          tipo_ato,
          status_vigencia,
          data_legislacao
        ),
        dispositivo_origem:dispositivo_origem_id (
          id,
          rotulo,
          texto
        ),
        dispositivo_alvo:dispositivo_alvo_id (
          id,
          rotulo,
          texto,
          ato:ato_id (
            id,
            urn_lexml,
            titulo,
            tipo_ato,
            status_vigencia,
            data_legislacao
          )
        )
      `;

  let rows: RawRelation[] = [];

  if (urnFilter) {
    const { data: ato, error: atoError } = await supabase
      .from("ato_normativo")
      .select("id")
      .eq("urn_lexml", urnFilter)
      .maybeSingle();

    if (atoError) {
      return NextResponse.json(
        { error: "Falha ao consultar ato_normativo.", details: atoError.message },
        { status: 500 },
      );
    }

    if (!ato) {
      return NextResponse.json({ error: "Ato não encontrado para URN informada." }, { status: 404 });
    }

    const dispositivoIds: string[] = [];
    const { data: dispositivos, error: dispositivoError } = await supabase
      .from("dispositivo")
      .select("id")
      .eq("ato_id", ato.id);
    if (!dispositivoError && dispositivos) {
      dispositivoIds.push(...dispositivos.map((item: { id: string }) => item.id));
    }

    const relationMap = new Map<string, RawRelation>();

    const queries = [
      supabase.from("dispositivo_relacao").select(relationSelect).eq("ato_id", ato.id),
      supabase.from("dispositivo_relacao").select(relationSelect).eq("urn_alvo", urnFilter),
    ];

    if (dispositivoIds.length) {
      const chunkSize = 99;
      for (let i = 0; i < dispositivoIds.length; i += chunkSize) {
        const chunk = dispositivoIds.slice(i, i + chunkSize);
        queries.push(
          supabase.from("dispositivo_relacao").select(relationSelect).in("dispositivo_alvo_id", chunk),
        );
      }
    }

    for await (const query of queries) {
      const { data: result, error: relationError } = await query;
      if (relationError) {
        console.warn("Erro ao consultar relações específicas:", relationError.message);
        continue;
      }
      ((result ?? []) as unknown as RawRelation[]).forEach((row) => relationMap.set(row.id, row));
    }

    rows = Array.from(relationMap.values());
  } else {
    const { data: relations, error } = await supabase
      .from("dispositivo_relacao")
      .select(relationSelect)
      .order("criado_em", { ascending: false })
      .limit(limit);

    if (error) {
      return NextResponse.json(
        { error: "Falha ao consultar relações no Supabase.", details: error.message },
        { status: 500 },
      );
    }

    rows = (relations ?? []) as unknown as RawRelation[];
  }

  const nodes = new Map<string, GraphNode>();
  const links: GraphLink[] = [];

  rows.forEach((row) => {
    const origemAto = row.ato;
    const origemUrn = origemAto?.urn_lexml;
    if (!origemUrn) {
      return;
    }

    const origemNode = upsertNode(nodes, {
      id: origemUrn,
      label: origemAto?.titulo || origemUrn,
      tipo: origemAto?.tipo_ato,
      status: origemAto?.status_vigencia,
      data: origemAto?.data_legislacao,
      count: 1,
    });

    const alvoAto = row.dispositivo_alvo?.ato;
    const alvoUrn = alvoAto?.urn_lexml || row.urn_alvo;
    if (!alvoUrn) {
      return;
    }

    upsertNode(nodes, {
      id: alvoUrn,
      label: alvoAto?.titulo || alvoUrn,
      tipo: alvoAto?.tipo_ato,
      status: alvoAto?.status_vigencia,
      data: alvoAto?.data_legislacao,
      count: 1,
      unknown: !alvoAto,
    });

    links.push({
      id: row.id,
      source: origemNode.id,
      target: alvoUrn,
      tipo: row.tipo,
      descricao: row.descricao,
      criadoEm: row.criado_em ?? undefined,
      origemRotulo: row.dispositivo_origem?.rotulo ?? undefined,
      origemTexto: row.dispositivo_origem?.texto ?? undefined,
      alvoTexto: row.dispositivo_alvo?.texto ?? undefined,
    });
  });

  return NextResponse.json({
    nodes: Array.from(nodes.values()),
    links,
    fetchedAt: new Date().toISOString(),
    totalRelations: links.length,
  });
}

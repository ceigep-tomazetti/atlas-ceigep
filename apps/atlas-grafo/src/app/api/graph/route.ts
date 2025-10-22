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
  } | null;
  dispositivo_alvo: {
    id: string;
    rotulo: string | null;
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

  const { data, error } = await supabase
    .from("dispositivo_relacao")
    .select(
      `
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
          rotulo
        ),
        dispositivo_alvo:dispositivo_alvo_id (
          id,
          rotulo,
          ato:ato_id (
            id,
            urn_lexml,
            titulo,
            tipo_ato,
            status_vigencia,
            data_legislacao
          )
        )
      `,
    )
    .order("criado_em", { ascending: false })
    .limit(limit);

  if (error) {
    return NextResponse.json(
      { error: "Falha ao consultar relações no Supabase.", details: error.message },
      { status: 500 },
    );
  }

  const nodes = new Map<string, GraphNode>();
  const links: GraphLink[] = [];

  const rows = (data ?? []) as unknown as RawRelation[];

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
    });
  });

  return NextResponse.json({
    nodes: Array.from(nodes.values()),
    links,
    fetchedAt: new Date().toISOString(),
    totalRelations: links.length,
  });
}

import { NextResponse } from "next/server";
import { getSupabaseAdmin, hasSupabaseAdmin } from "@/lib/supabaseAdmin";

const DEFAULT_LIMIT = 50;

export async function GET(request: Request) {
  if (!hasSupabaseAdmin) {
    return NextResponse.json(
      { error: "Supabase credentials missing" },
      { status: 503 }
    );
  }

  const client = getSupabaseAdmin();
  if (!client) {
    return NextResponse.json(
      { error: "Supabase client not available" },
      { status: 503 }
    );
  }
  const { searchParams } = new URL(request.url);

  const limit = Number(searchParams.get("limit")) || DEFAULT_LIMIT;
  const originId = searchParams.get("originId");
  const urn = searchParams.get("urn");
  const tipoRelacao = searchParams.get("relationType");

  try {
    const atoQuery = client
      .from("ato_normativo")
      .select("id, urn_lexml, tipo_ato, titulo, status_vigencia")
      .limit(limit)
      .order("criado_em", { ascending: false });

    if (originId) {
      atoQuery.eq("fonte_documento_id", originId);
    }
    if (urn) {
      atoQuery.ilike("urn_lexml", `%${urn}%`);
    }

    const atosResp = await atoQuery;
    if (atosResp.error) throw atosResp.error;
    const atos = atosResp.data ?? [];
    if (atos.length === 0) {
      return NextResponse.json({ nodes: [], links: [] });
    }

    const atoIds = atos.map((a) => a.id);

    const dispositivosResp = await client
      .from("dispositivo")
      .select("id, ato_id, parent_id, id_lexml, tipo, rotulo")
      .in("ato_id", atoIds);
    if (dispositivosResp.error) throw dispositivosResp.error;
    const dispositivos = dispositivosResp.data ?? [];

    const relQuery = client
      .from("dispositivo_relacao")
      .select(
        "id, ato_id, dispositivo_origem_id, dispositivo_alvo_id, urn_alvo, tipo, descricao"
      )
      .in("ato_id", atoIds);
    if (tipoRelacao) {
      relQuery.eq("tipo", tipoRelacao);
    }
    const relacoesResp = await relQuery;
    if (relacoesResp.error) throw relacoesResp.error;
    const relacoes = relacoesResp.data ?? [];

    const nodes: any[] = [];
    const nodeIds = new Set<string>();
    const links: any[] = [];

    for (const ato of atos) {
      const id = `ato:${ato.id}`;
      nodeIds.add(id);
      nodes.push({
        id,
        label: ato.urn_lexml,
        tipo: "ato",
        subtitle: ato.titulo,
        status: ato.status_vigencia,
        tipoAto: ato.tipo_ato
      });
    }

    for (const disp of dispositivos) {
      const id = `disp:${disp.id}`;
      nodeIds.add(id);
      nodes.push({
        id,
        label: disp.rotulo || disp.id_lexml,
        tipo: "dispositivo",
        dispositivoTipo: disp.tipo,
        atoId: disp.ato_id,
        parentId: disp.parent_id
      });
      links.push({
        source: `ato:${disp.ato_id}`,
        target: `disp:${disp.id}`,
        kind: "PERTENCE",
        direction: "down"
      });
      if (disp.parent_id) {
        links.push({
          source: `disp:${disp.parent_id}`,
          target: `disp:${disp.id}`,
          kind: "HIERARQUIA",
          direction: "down"
        });
      }
    }

    for (const rel of relacoes) {
      if (rel.dispositivo_origem_id) {
        links.push({
          source: `disp:${rel.dispositivo_origem_id}`,
          target: rel.dispositivo_alvo_id
            ? `disp:${rel.dispositivo_alvo_id}`
            : rel.urn_alvo
            ? `urn:${rel.urn_alvo}`
            : undefined,
          kind: rel.tipo,
          descricao: rel.descricao
        });
      }
      if (rel.urn_alvo && !rel.dispositivo_alvo_id) {
        const refId = `urn:${rel.urn_alvo}`;
        if (!nodeIds.has(refId)) {
          nodeIds.add(refId);
          nodes.push({
            id: refId,
            label: rel.urn_alvo,
            tipo: "referencia"
          });
        }
      }
    }

    const filteredLinks = links.filter((link) => link.target !== undefined);

    return NextResponse.json({ nodes, links: filteredLinks });
  } catch (error) {
    console.error("/api/graph error", error);
    return NextResponse.json({ error: "Erro ao montar grafo" }, { status: 500 });
  }
}

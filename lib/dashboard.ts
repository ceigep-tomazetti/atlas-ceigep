import { supabaseAdmin, supabaseServiceRoleKey, supabaseUrl } from "./supabaseAdmin";

export type CountEntry = {
  label: string;
  count: number;
};

export type RecentExecucao = {
  id: string;
  origemNome: string;
  periodo: string;
  finalizadoEm: string;
  totais: {
    descobertos: number;
    duplicados: number;
    falhas: number;
  };
};

export type DashboardData = {
  totalOrigens: number;
  totalDocumentos: number;
  totalDispositivos: number;
  documentosPorStatus: CountEntry[];
  parsingPorStatus: CountEntry[];
  normalizacaoPorStatus: CountEntry[];
  dispositivosPorTipo: CountEntry[];
  execucoesRecentes: RecentExecucao[];
};

async function countAll(table: string, column = "*") {
  const { count, error } = await supabaseAdmin
    .from(table)
    .select(column, { count: "exact", head: true });
  if (error) throw error;
  return count ?? 0;
}

async function countGrouped(table: string, column: string): Promise<CountEntry[]> {
  const url = new URL(`${supabaseUrl}/rest/v1/${table}`);
  url.searchParams.set("select", `${column},count:count()`);
  url.searchParams.set("group", column);

  if (!supabaseServiceRoleKey) {
    throw new Error("SUPABASE_SERVICE_ROLE_KEY não definido");
  }

  const headers = new Headers({
    apikey: supabaseServiceRoleKey,
    Authorization: `Bearer ${supabaseServiceRoleKey}`,
    Accept: "application/json"
  });

  const response = await fetch(url.toString(), {
    headers,
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Falha ao agrupar ${table}: ${response.status}`);
  }

  const data = (await response.json()) as Array<Record<string, any>>;

  return data.map((row) => ({
    label: row[column] ?? "(sem valor)",
    count: Number(row.count ?? 0)
  }));
}

export async function fetchDashboardData(): Promise<DashboardData> {
  const [
    totalOrigens,
    totalDocumentos,
    totalDispositivos,
    documentosPorStatus,
    parsingPorStatus,
    normalizacaoPorStatus,
    dispositivosPorTipo,
    execucoesRecentes,
    origemLookup
  ] = await Promise.all([
    countAll("fonte_origem"),
    countAll("fonte_documento"),
    countAll("dispositivo"),
    countGrouped("fonte_documento", "status"),
    countGrouped("fonte_documento", "status_parsing"),
    countGrouped("fonte_documento", "status_normalizacao"),
    countGrouped("dispositivo", "tipo"),
    supabaseAdmin
      .from("fonte_origem_execucao")
      .select(
        "id, fonte_origem_id, periodo_inicio, periodo_fim, finalizado_em, total_descobertos, total_duplicados, total_falhas"
      )
      .order("finalizado_em", { ascending: false })
      .limit(6),
    supabaseAdmin.from("fonte_origem").select("id, nome")
  ]);

  const origemNomeMap = new Map<string, string>(
    (origemLookup.data ?? []).map((row: any) => [row.id, row.nome])
  );

  const execucoes: RecentExecucao[] = (execucoesRecentes.data ?? []).map(
    (row: any) => ({
      id: row.id,
      origemNome: origemNomeMap.get(row.fonte_origem_id) || row.fonte_origem_id,
      periodo: `${row.periodo_inicio ?? "?"} → ${row.periodo_fim ?? "?"}`,
      finalizadoEm: row.finalizado_em,
      totais: {
        descobertos: Number(row.total_descobertos ?? 0),
        duplicados: Number(row.total_duplicados ?? 0),
        falhas: Number(row.total_falhas ?? 0)
      }
    })
  );

  const normalize = (entries: CountEntry[]) =>
    entries
      .map((entry) => ({
        label: entry.label ?? "(sem valor)",
        count: entry.count
      }))
      .sort((a, b) => b.count - a.count);

  return {
    totalOrigens,
    totalDocumentos,
    totalDispositivos,
    documentosPorStatus: normalize(documentosPorStatus),
    parsingPorStatus: normalize(parsingPorStatus),
    normalizacaoPorStatus: normalize(normalizacaoPorStatus),
    dispositivosPorTipo: normalize(dispositivosPorTipo),
    execucoesRecentes: execucoes
  };
}

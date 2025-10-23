"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import styles from "./page.module.css";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false
});

type GraphNode = {
  id: string;
  label: string;
  tipo: string;
  subtitle?: string;
  status?: string;
  tipoAto?: string;
  dispositivoTipo?: string;
  atoId?: string;
  parentId?: string;
};

type GraphLink = {
  source: string;
  target: string;
  kind?: string;
  descricao?: string;
  direction?: string;
};

type GraphResponse = {
  nodes: GraphNode[];
  links: GraphLink[];
};

const NODE_COLORS: Record<string, string> = {
  ato: "#60a5fa",
  dispositivo: "#34d399",
  referencia: "#f59e0b"
};

export default function GraphPage() {
  const [data, setData] = useState<GraphResponse>({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState({
    limit: 60,
    originId: "",
    urn: "",
    relationType: ""
  });

  const fetchGraph = async () => {
    setLoading(true);
    setError(null);
    setSelectedNode(null);

    const params = new URLSearchParams();
    params.set("limit", String(filters.limit));
    if (filters.originId) params.set("originId", filters.originId);
    if (filters.urn) params.set("urn", filters.urn);
    if (filters.relationType) params.set("relationType", filters.relationType);

    try {
      const response = await fetch(`/api/graph?${params.toString()}`, {
        cache: "no-store"
      });
      if (!response.ok) {
        throw new Error("Falha ao consultar o grafo");
      }
      const payload = (await response.json()) as GraphResponse;
      setData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const nodeColor = (node: GraphNode) => NODE_COLORS[node.tipo] ?? "#f8fafc";

  const relatedLinks = useMemo(() => {
    if (!selectedNode) return [];
    return data.links.filter(
      (link) => link.source === selectedNode.id || link.target === selectedNode.id
    );
  }, [data.links, selectedNode]);

  return (
    <div className={styles.container}>
      <form
        className={styles.toolbar}
        onSubmit={(event) => {
          event.preventDefault();
          fetchGraph();
        }}
      >
        <fieldset>
          <label htmlFor="limit">Limite de atos</label>
          <input
            id="limit"
            type="number"
            min={10}
            max={200}
            value={filters.limit}
            onChange={(e) =>
              setFilters((prev) => ({ ...prev, limit: Number(e.target.value) }))
            }
          />
        </fieldset>

        <fieldset>
          <label htmlFor="originId">Origem (UUID)</label>
          <input
            id="originId"
            value={filters.originId}
            onChange={(e) => setFilters((prev) => ({ ...prev, originId: e.target.value }))}
            placeholder="fd64e393-..."
          />
        </fieldset>

        <fieldset>
          <label htmlFor="urn">Filtrar URN</label>
          <input
            id="urn"
            value={filters.urn}
            onChange={(e) => setFilters((prev) => ({ ...prev, urn: e.target.value }))}
            placeholder="br;go;estadual;..."
          />
        </fieldset>

        <fieldset>
          <label htmlFor="relationType">Tipo de relação</label>
          <select
            id="relationType"
            value={filters.relationType}
            onChange={(e) =>
              setFilters((prev) => ({ ...prev, relationType: e.target.value }))
            }
          >
            <option value="">Todas</option>
            <option value="altera">Altera</option>
            <option value="revoga">Revoga</option>
            <option value="regulamenta">Regulamenta</option>
            <option value="consolida">Consolida</option>
            <option value="remete_a">Remete</option>
            <option value="cita">Cita</option>
          </select>
        </fieldset>

        <button type="submit" disabled={loading}>
          {loading ? "Carregando..." : "Atualizar"}
        </button>
      </form>

      {error && <p style={{ color: "#f87171" }}>{error}</p>}

      <div className={styles.legend}>
        <span>
          <span className={styles.legendColor} style={{ background: NODE_COLORS.ato }} /> Ato
        </span>
        <span>
          <span
            className={styles.legendColor}
            style={{ background: NODE_COLORS.dispositivo }}
          />
          Dispositivo
        </span>
        <span>
          <span
            className={styles.legendColor}
            style={{ background: NODE_COLORS.referencia }}
          />
          Referência externa
        </span>
      </div>

      <section className={styles.graphSection}>
        <div className={styles.graphCanvas}>
          <ForceGraph2D
            graphData={data as any}
            nodeLabel={(node: any) => (node as GraphNode).label}
            nodeAutoColorBy={(node: any) => (node as GraphNode).tipo}
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              const graphNode = node as GraphNode & { x: number; y: number };
              const label = graphNode.label;
              const fontSize = 12 / globalScale;
              ctx.fillStyle = nodeColor(graphNode);
              ctx.beginPath();
              ctx.arc(graphNode.x, graphNode.y, 6, 0, 2 * Math.PI, false);
              ctx.fill();
              ctx.font = `${fontSize}px Sans-Serif`;
              ctx.fillStyle = "#e2e8f0";
              ctx.fillText(label, graphNode.x + 8, graphNode.y + 4);
            }}
            linkColor={(link: any) =>
              link.kind === "revoga"
                ? "#f87171"
                : link.kind === "altera"
                ? "#facc15"
                : "rgba(148, 163, 184, 0.6)"
            }
            linkDirectionalArrowLength={4}
            cooldownTicks={50}
            onNodeClick={(node: any) => {
              setSelectedNode(node as GraphNode);
            }}
          />
        </div>

        <aside className={styles.detailsPanel}>
          <h2>Detalhes</h2>
          {selectedNode ? (
            <>
              <div>
                <h3>{selectedNode.label}</h3>
                {selectedNode.subtitle && <p>{selectedNode.subtitle}</p>}
                <ul>
                  <li>Tipo: {selectedNode.tipo}</li>
                  {selectedNode.status && <li>Status: {selectedNode.status}</li>}
                  {selectedNode.tipoAto && <li>Tipo de ato: {selectedNode.tipoAto}</li>}
                  {selectedNode.dispositivoTipo && (
                    <li>Tipo de dispositivo: {selectedNode.dispositivoTipo}</li>
                  )}
                </ul>
              </div>
              <div>
                <h4>Relações</h4>
                {relatedLinks.length === 0 ? (
                  <p className={styles.empty}>Sem relações diretas</p>
                ) : (
                  <ul>
                    {relatedLinks.map((link) => (
                      <li key={`${link.source}-${link.target}-${link.kind}`}>
                        <strong>{link.kind ?? "rel"}</strong>
                        {link.descricao && <p>{link.descricao}</p>}
                        <small>
                          {String(link.source)} → {String(link.target)}
                        </small>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          ) : (
            <p className={styles.empty}>
              Clique em um nó para visualizar suas informações detalhadas.
            </p>
          )}
        </aside>
      </section>
    </div>
  );
}

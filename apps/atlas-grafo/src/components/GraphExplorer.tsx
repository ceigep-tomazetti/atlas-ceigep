"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

type GraphNode = {
  id: string;
  label: string;
  tipo?: string | null;
  status?: string | null;
  data?: string | null;
  count?: number;
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

type GraphResponse = {
  nodes: GraphNode[];
  links: GraphLink[];
  fetchedAt: string;
  totalRelations: number;
};

type ActDetails = {
  urn: string;
  titulo: string | null;
  status_vigencia: string | null;
  data_legislacao: string | null;
  tipo_ato?: string | null;
  textoBruto: string | null;
  dispositivos: { id: string; rotulo: string | null; texto: string | null }[];
};

type ForceGraphNode = GraphNode & {
  id: string | number;
};

type ForceGraphLink = GraphLink & {
  source: string | number | GraphNode;
  target: string | number | GraphNode;
};

const relationOptions: { value: string; label: string }[] = [
  { value: "all", label: "Todos os tipos" },
  { value: "altera", label: "Altera" },
  { value: "revoga", label: "Revoga" },
  { value: "regulamenta", label: "Regulamenta" },
  { value: "consolida", label: "Consolida" },
  { value: "remete_a", label: "Remete a" },
  { value: "cita", label: "Cita" },
];

const fetcher = (url: string) =>
  fetch(url).then((res) => {
    if (!res.ok) {
      throw new Error(`Falha ao consultar ${url}: ${res.status}`);
    }
    return res.json();
  });

export function GraphExplorer() {
  const [selectedRelation, setSelectedRelation] = useState<string>("all");
  const [actFilter, setActFilter] = useState<string>("all");

  const graphKey = actFilter === "all" ? "/api/graph" : `/api/graph?urn=${encodeURIComponent(actFilter)}`;
  const { data, error, isLoading, mutate } = useSWR<GraphResponse>(graphKey, fetcher, {
    revalidateOnFocus: false,
  });

  const { data: baseData } = useSWR<GraphResponse>("/api/graph", fetcher, {
    revalidateOnFocus: false,
  });

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedLinkId, setSelectedLinkId] = useState<string | null>(null);
  const [actError, setActError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({
    width: 960,
    height: 540,
  });

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        setDimensions({
          width: Math.max(clientWidth, 320),
          height: Math.max(clientHeight, 280),
        });
      }
    };

    updateSize();

    const observer = new ResizeObserver(updateSize);
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    window.addEventListener("resize", updateSize);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateSize);
    };
  }, []);

  const actOptions = useMemo(() => {
    const baseNodes = baseData?.nodes ? [...baseData.nodes] : [];
    if (actFilter !== "all" && data) {
      const exists = baseNodes.some((node) => node.id === actFilter);
      if (!exists) {
        const node = data.nodes.find((item) => item.id === actFilter);
        if (node) {
          baseNodes.push(node);
        } else {
          baseNodes.push({
            id: actFilter,
            label: actFilter,
            tipo: undefined,
            status: undefined,
            data: undefined,
            count: 0,
            unknown: false,
          } as GraphNode);
        }
      }
    }
    const uniqueNodes = Array.from(new Map(baseNodes.map((node) => [node.id, node])).values());
    return uniqueNodes
      .map((node) => ({
        value: node.id,
        label: node.label || node.id,
      }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [baseData, data, actFilter]);

  const filteredLinks = useMemo(() => {
    if (!data) {
      return [];
    }
    let links = data.links;
    if (selectedRelation !== "all") {
      links = links.filter((link) => link.tipo === selectedRelation);
    }
    if (actFilter !== "all") {
      links = links.filter((link) => link.source === actFilter || link.target === actFilter);
    }
    return links;
  }, [data, selectedRelation, actFilter]);

  const visibleNodes = useMemo(() => {
    if (!data) {
      return [];
    }
    if (selectedRelation === "all" && actFilter === "all") {
      return data.nodes;
    }
    const ids = new Set<string>();
    filteredLinks.forEach((link) => {
      ids.add(String(link.source));
      ids.add(String(link.target));
    });
    if (actFilter !== "all") {
      ids.add(actFilter);
    }
    return data.nodes.filter((node) => ids.has(node.id));
  }, [data, filteredLinks, selectedRelation, actFilter]);

  const selectedNode = useMemo(
    () => data?.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [data, selectedNodeId],
  );

  const selectedLink = useMemo(
    () => data?.links.find((link) => link.id === selectedLinkId) ?? null,
    [data, selectedLinkId],
  );

  const {
    data: actDetails,
    isLoading: isActLoading,
  } = useSWR<ActDetails>(
    selectedNodeId ? `/api/act?urn=${encodeURIComponent(selectedNodeId)}` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      onError: (err) => setActError(err.message),
      onSuccess: () => setActError(null),
    },
  );

  const graphData = useMemo(() => {
    return {
      nodes: visibleNodes as ForceGraphNode[],
      links: filteredLinks as ForceGraphLink[],
    };
  }, [visibleNodes, filteredLinks]);

  const resetSelections = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedLinkId(null);
    setActError(null);
  }, []);

  if (error) {
    return (
      <div className="graph-wrapper error">
        <p>Não foi possível carregar as relações normativas.</p>
        <p className="muted">{error.message}</p>
        <button type="button" onClick={() => mutate()} className="action">
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className="graph-wrapper">
      <header className="graph-header">
        <div>
          <h1>Atlas CEIGEP · Relações Normativas</h1>
          <p>
            Visualize como atos normativos se relacionam — repetições indicam possíveis cadeias de alteração
            e citações relevantes para exploração posterior.
          </p>
        </div>
        <div className="controls">
          <label>
            Tipo de relação
            <select
              value={selectedRelation}
              onChange={(event) => {
                setSelectedRelation(event.target.value);
                resetSelections();
              }}
            >
              {relationOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
              </label>
          <label>
            Ato específico
            <select
              value={actFilter}
              onChange={(event) => {
                const value = event.target.value;
                setActFilter(value);
                if (value === "all") {
                  resetSelections();
                } else {
                  setSelectedNodeId(value);
                  setSelectedLinkId(null);
                }
              }}
            >
              <option value="all">Todos os atos</option>
              {actOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="action ghost" onClick={() => mutate()}>
            Atualizar dados
          </button>
        </div>
      </header>

      <section className="graph-canvas" ref={containerRef}>
        {isLoading && <div className="overlay">Carregando relações…</div>}
        <ForceGraph2D
          graphData={graphData}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor="#0f172a"
          linkColor={() => "rgba(148, 163, 184, 0.45)"}
          linkWidth={1}
          linkDirectionalArrowColor={() => "rgba(96, 165, 250, 0.7)"}
          linkDirectionalArrowLength={4}
          linkDirectionalParticles={1}
          linkDirectionalParticleSpeed={0.004}
          linkDirectionalParticleColor={() => "rgba(56, 189, 248, 0.8)"}
          nodeLabel={(node) => {
            const typed = node as GraphNode;
            const lines = [
              `<strong>${typed.label}</strong>`,
              typed.tipo ? `Tipo: ${typed.tipo}` : null,
              typed.status ? `Vigência: ${typed.status}` : null,
              typed.data ? `Data: ${typed.data}` : null,
              typed.count ? `Relações mapeadas: ${typed.count}` : null,
            ].filter(Boolean);
            return lines.join("<br/>");
          }}
          linkLabel={(link) => {
            const typed = link as GraphLink;
            const parts = [
              `<strong>${typed.tipo}</strong>`,
              typed.descricao,
              typed.origemRotulo ? `Dispositivo de origem: ${typed.origemRotulo}` : null,
              typed.criadoEm ? `Capturado em: ${typed.criadoEm}` : null,
            ].filter(Boolean);
            return parts.join("<br/>");
          }}
          nodeAutoColorBy={(node) => (node as GraphNode).tipo ?? "desconhecido"}
          linkDirectionalParticleWidth={1.5}
          cooldownTime={4000}
          onNodeClick={(node) => {
            setSelectedNodeId(node.id as string);
            setSelectedLinkId(null);
            setActError(null);
          }}
          onLinkClick={(link) => {
            setSelectedLinkId(link.id as string);
            setSelectedNodeId(null);
            setActError(null);
          }}
        />
      </section>

      <section className="graph-details">
        {selectedNode ? (
          <div>
            <h2>Atos relacionados</h2>
            <dl>
              <div>
                <dt>URN</dt>
                <dd>{selectedNode.id}</dd>
              </div>
              <div>
                <dt>Título</dt>
                <dd>{selectedNode.label}</dd>
              </div>
              {selectedNode.tipo && (
                <div>
                  <dt>Tipo</dt>
                  <dd>{selectedNode.tipo}</dd>
                </div>
              )}
              {selectedNode.status && (
                <div>
                  <dt>Vigência</dt>
                  <dd>{selectedNode.status}</dd>
                </div>
              )}
              {selectedNode.data && (
                <div>
                  <dt>Data</dt>
                  <dd>{selectedNode.data}</dd>
                </div>
              )}
              <div>
                <dt>Relações mapeadas</dt>
                <dd>{selectedNode.count ?? 0}</dd>
              </div>
              {selectedNode.unknown && (
                <div>
                  <dt>Observação</dt>
                  <dd>Atos ainda não carregados no Atlas — obtidos apenas pela citação LEXML.</dd>
                </div>
              )}
            </dl>
            {isActLoading && <p className="muted">Carregando texto integral…</p>}
            {actError && <p className="error">Falha ao carregar texto: {actError}</p>}
            {(() => {
              const fallback =
                actDetails?.dispositivos
                  ?.map((disp) => {
                    const header = disp.rotulo ? `${disp.rotulo}\n` : "";
                    return `${header}${disp.texto ?? ""}`.trim();
                  })
                  .filter((chunk) => chunk.length > 0)
                  .join("\n\n") || null;
              const textoIntegral = actDetails?.textoBruto ?? fallback;
              if (!textoIntegral) {
                return null;
              }
              return (
                <section className="full-text">
                  <h3>Texto integral</h3>
                  <pre>{textoIntegral}</pre>
                </section>
              );
            })()}
          </div>
        ) : selectedLink ? (
          <div>
            <h2>Detalhes da relação</h2>
            <dl>
              <div>
                <dt>Tipo</dt>
                <dd>{selectedLink.tipo}</dd>
              </div>
              <div>
                <dt>Descrição</dt>
                <dd>{selectedLink.descricao ?? "—"}</dd>
              </div>
              <div>
                <dt>Ato de origem</dt>
                <dd>{selectedLink.source}</dd>
              </div>
              <div>
                <dt>Ato alvo</dt>
                <dd>{selectedLink.target}</dd>
              </div>
              {selectedLink.origemRotulo && (
                <div>
                  <dt>Dispositivo de origem</dt>
                  <dd>{selectedLink.origemRotulo}</dd>
                </div>
              )}
              {selectedLink.criadoEm && (
                <div>
                  <dt>Registrado em</dt>
                  <dd>{new Date(selectedLink.criadoEm).toLocaleString()}</dd>
                </div>
              )}
            </dl>
            {selectedLink.origemTexto && (
              <section className="full-text">
                <h3>Texto do dispositivo de origem</h3>
                <pre>{selectedLink.origemTexto}</pre>
              </section>
            )}
            {selectedLink.alvoTexto && (
              <section className="full-text">
                <h3>Texto do dispositivo alvo</h3>
                <pre>{selectedLink.alvoTexto}</pre>
              </section>
            )}
          </div>
        ) : (
          <div>
            <h2>Selecione um nó ou ligação</h2>
            <p>
              Clique em um ato normativo para ver metadados, ou em uma ligação para ler a descrição gerada
              pelo parser/loader.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

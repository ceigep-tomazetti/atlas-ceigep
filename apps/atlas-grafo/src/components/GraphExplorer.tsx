"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";

const ForceGraph2D = dynamic(
  () => import("react-force-graph").then((mod) => mod.ForceGraph2D),
  { ssr: false },
);

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
};

type GraphResponse = {
  nodes: GraphNode[];
  links: GraphLink[];
  fetchedAt: string;
  totalRelations: number;
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
  const { data, error, isLoading, mutate } = useSWR<GraphResponse>("/api/graph", fetcher, {
    revalidateOnFocus: false,
  });

  const [selectedRelation, setSelectedRelation] = useState<string>("all");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedLinkId, setSelectedLinkId] = useState<string | null>(null);
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

  const filteredLinks = useMemo(() => {
    if (!data) {
      return [];
    }
    if (selectedRelation === "all") {
      return data.links;
    }
    return data.links.filter((link) => link.tipo === selectedRelation);
  }, [data, selectedRelation]);

  const visibleNodes = useMemo(() => {
    if (!data) {
      return [];
    }
    if (selectedRelation === "all") {
      return data.nodes;
    }
    const ids = new Set<string>();
    filteredLinks.forEach((link) => {
      ids.add(String(link.source));
      ids.add(String(link.target));
    });
    return data.nodes.filter((node) => ids.has(node.id));
  }, [data, filteredLinks, selectedRelation]);

  const selectedNode = useMemo(
    () => data?.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [data, selectedNodeId],
  );

  const selectedLink = useMemo(
    () => data?.links.find((link) => link.id === selectedLinkId) ?? null,
    [data, selectedLinkId],
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
          linkDirectionalArrowLength={6}
          linkDirectionalParticles={2}
          linkDirectionalParticleWidth={2}
          cooldownTime={4000}
          onNodeClick={(node) => {
            setSelectedNodeId(node.id as string);
            setSelectedLinkId(null);
          }}
          onLinkClick={(link) => {
            setSelectedLinkId(link.id as string);
            setSelectedNodeId(null);
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

import { fetchDashboardData } from "../lib/dashboard";
import styles from "./page.module.css";

export default async function Home() {
  const data = await fetchDashboardData();

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <div>
          <h1>Atlas CEIGEP</h1>
          <p>
            Painel de monitoramento geral dos fluxos de descoberta, parsing e
            normalização.
          </p>
        </div>
      </header>

      <section className={styles.grid}>
        <Card title="Origens monitoradas" value={data.totalOrigens} />
        <Card title="Documentos no catálogo" value={data.totalDocumentos} />
        <Card title="Dispositivos normalizados" value={data.totalDispositivos} />
      </section>

     <section className={styles.gridWide}>
       <StatsCard
          title="Descoberta (status)"
          items={data.documentosPorStatus}
        />
        <StatsCard title="Dispositivos por tipo" items={data.dispositivosPorTipo} />
        <StatsCard title="Atos por tipo" items={data.atosPorTipo} />
      </section>

      <section className={styles.pipeline}>
        <h2>Fluxo de processamento</h2>
        <div className={styles.pipelineSteps}>
          <PipelineStep
            title="1. Descoberta"
            description="Documentos coletados via crawler"
            items={data.documentosPorStatus}
          />
          <PipelineStep
            title="2. Parsing"
            description="Textos estruturados pelo LLM"
            items={data.parsingPorStatus}
          />
          <PipelineStep
            title="3. Normalização"
            description="Inserção na base relacional"
            items={data.normalizacaoPorStatus}
          />
        </div>
      </section>

      <section className={styles.execucoes}>
        <h2>Execuções recentes</h2>
        <ul>
          {data.execucoesRecentes.length === 0 && (
            <li className={styles.empty}>Nenhuma execução registrada ainda.</li>
          )}
          {data.execucoesRecentes.map((execucao) => (
            <li key={execucao.id} className={styles.execucaoItem}>
              <div>
                <strong>{execucao.origemNome}</strong>
                <span>{execucao.periodo}</span>
              </div>
              <div className={styles.execucaoTotais}>
                <span>Novos: {execucao.totais.descobertos}</span>
                <span>Duplicados: {execucao.totais.duplicados}</span>
                <span>Falhas: {execucao.totais.falhas}</span>
              </div>
              <small>
                Finalizado em {new Date(execucao.finalizadoEm).toLocaleString("pt-BR")}
              </small>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

function Card({ title, value }: { title: string; value: number }) {
  return (
    <article className={styles.card}>
      <h3>{title}</h3>
      <span>{value.toLocaleString("pt-BR")}</span>
    </article>
  );
}

function StatsCard({
  title,
  items
}: {
  title: string;
  items: { label: string; count: number }[];
}) {
  return (
    <article className={styles.cardList}>
      <h3>{title}</h3>
      <ul>
        {items.length === 0 && (
          <li className={styles.empty}>Sem registros disponíveis.</li>
        )}
        {items.map((item) => (
          <li key={item.label}>
            <span>{item.label}</span>
            <strong>{item.count.toLocaleString("pt-BR")}</strong>
          </li>
        ))}
      </ul>
    </article>
  );
}

function PipelineStep({
  title,
  description,
  items
}: {
  title: string;
  description: string;
  items: { label: string; count: number }[];
}) {
  return (
    <article className={styles.pipelineStep}>
      <header>
        <h3>{title}</h3>
        <p>{description}</p>
      </header>
      <ul>
        {items.length === 0 && (
          <li className={styles.empty}>Sem registros disponíveis.</li>
        )}
        {items.map((item) => (
          <li key={item.label}>
            <span>{item.label}</span>
            <strong>{item.count.toLocaleString("pt-BR")}</strong>
          </li>
        ))}
      </ul>
    </article>
  );
}

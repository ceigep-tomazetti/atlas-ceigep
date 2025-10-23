export default function Home() {
  return (
    <main>
      <h1 style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>Atlas CEIGEP</h1>
      <p style={{ fontSize: "1.1rem", lineHeight: 1.6, marginBottom: "2.5rem" }}>
        Bem-vindo ao painel de gerenciamento do projeto Atlas. Em breve você poderá
        acompanhar indicadores, reprocessar pipelines e visualizar o progresso das
        integrações diretamente por aqui.
      </p>
      <p style={{ fontSize: "0.95rem", opacity: 0.8 }}>
        Enquanto finalizamos a implementação, você pode continuar administrando os fluxos pelo
        Supabase e pelos scripts existentes no repositório. Esta página serve apenas como
        placeholder inicial para validar o deploy na Vercel.
      </p>
    </main>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Atlas CEIGEP · Grafo Normativo",
  description:
    "Visualização interativa das relações normativas ingeridas pelo pipeline do Atlas CEIGEP.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}

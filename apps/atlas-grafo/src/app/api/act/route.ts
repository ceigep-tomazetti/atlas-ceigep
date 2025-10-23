import { NextResponse } from "next/server";

import { getSupabaseServiceClient } from "@/lib/supabase";

function splitBucketPath(path: string): { bucket: string; key: string } | null {
  if (!path.includes("/")) {
    return null;
  }
  const [bucket, ...rest] = path.split("/");
  return { bucket, key: rest.join("/") };
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const urn = searchParams.get("urn");
  if (!urn) {
    return NextResponse.json({ error: "Parâmetro 'urn' é obrigatório." }, { status: 400 });
  }

  let supabase;
  try {
    supabase = getSupabaseServiceClient();
  } catch (error) {
    console.error("Supabase configuration error", error);
    return NextResponse.json({ error: "Configuração do Supabase ausente." }, { status: 500 });
  }

  const { data: ato, error: atoError } = await supabase
    .from("ato_normativo")
    .select("id, titulo, status_vigencia, data_legislacao, fonte_documento_id")
    .eq("urn_lexml", urn)
    .limit(1)
    .maybeSingle();

  if (atoError) {
    return NextResponse.json({ error: "Falha ao consultar ato_normativo.", details: atoError.message }, { status: 500 });
  }

  if (!ato) {
    return NextResponse.json({ error: "Ato não encontrado para a URN informada." }, { status: 404 });
  }

  const { data: fonteDocumento, error: docError } = await supabase
    .from("fonte_documento")
    .select("caminho_texto_bruto, tipo_ato")
    .eq("id", ato.fonte_documento_id)
    .limit(1)
    .maybeSingle();

  if (docError) {
    return NextResponse.json(
      { error: "Falha ao consultar fonte_documento.", details: docError.message },
      { status: 500 },
    );
  }

  let textoBruto: string | null = null;
  if (fonteDocumento?.caminho_texto_bruto) {
    const bucketInfo = splitBucketPath(fonteDocumento.caminho_texto_bruto);
    if (bucketInfo) {
      const { data: arquivo, error: downloadError } = await supabase.storage
        .from(bucketInfo.bucket)
        .download(bucketInfo.key);
      if (!downloadError && arquivo) {
        textoBruto = await arquivo.text();
      }
    }
  }

  const { data: dispositivos, error: dispositivoError } = await supabase
    .from("dispositivo")
    .select("id, parent_id, rotulo, texto, tipo, ordem")
    .eq("ato_id", ato.id)
    .order("ordem", { ascending: true });

  if (dispositivoError) {
    return NextResponse.json(
      { error: "Falha ao consultar dispositivos.", details: dispositivoError.message },
      { status: 500 },
    );
  }

  return NextResponse.json({
    urn,
    titulo: ato.titulo,
    status_vigencia: ato.status_vigencia,
    data_legislacao: ato.data_legislacao,
    tipo_ato: fonteDocumento?.tipo_ato,
    textoBruto,
    dispositivos: dispositivos ?? [],
  });
}

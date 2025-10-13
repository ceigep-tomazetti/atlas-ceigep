# api/main.py
import os
from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega variáveis de ambiente do .env na raiz do projeto
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Gerenciamento do Ciclo de Vida da Aplicação ---

neo4j_driver = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código a ser executado na inicialização
    global neo4j_driver
    try:
        uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "atlas_password")
        neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
        neo4j_driver.verify_connectivity()
        logging.info("Conexão com o Neo4j estabelecida com sucesso.")
    except Exception as e:
        logging.error(f"Erro fatal ao conectar ao Neo4j na inicialização: {e}")
        # Em um ambiente de produção, você pode querer que a aplicação pare se o DB não estiver disponível.
        # Para desenvolvimento, podemos permitir que continue, mas os endpoints falharão.
        neo4j_driver = None
    
    yield
    
    # Código a ser executado no encerramento
    if neo4j_driver:
        neo4j_driver.close()
        logging.info("Conexão com o Neo4j fechada.")

# --- Instância da Aplicação FastAPI ---

app = FastAPI(
    title="Atlas API",
    description="API para consulta ao grafo de conhecimento legislativo do Projeto Atlas.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Endpoints da API ---

@app.get("/", tags=["Status"])
async def read_root():
    """Endpoint raiz para verificar se a API está online."""
    return {"status": "Atlas API online"}

@app.get("/atos/{urn}/relacoes", tags=["Consultas ao Grafo"])
async def get_relationships(urn: str):
    """
    Obtém todas as relações (de entrada e saída) para um Ato Normativo específico, identificado por sua URN.
    
    - **urn**: A URN LexML completa do ato normativo. 
      Exemplo: `br;federal;constituicao;1988-10-05`
    """
    if not neo4j_driver:
        raise HTTPException(status_code=503, detail="Serviço indisponível: não foi possível conectar ao banco de dados do grafo.")

    query = """
    MATCH (origem)-[r]-(destino)
    WHERE (origem:AtoNormativo AND origem.urn_lexml = $urn) OR (destino:AtoNormativo AND destino.urn_lexml = $urn)
    RETURN 
        labels(origem)[0] AS label_origem,
        COALESCE(properties(origem).urn_lexml, properties(origem).id_unico) AS id_origem,
        type(r) as tipo_relacao,
        labels(destino)[0] AS label_destino,
        COALESCE(properties(destino).urn_lexml, properties(destino).id_unico) AS id_destino
    """
    
    try:
        with neo4j_driver.session() as session:
            result = session.run(query, urn=urn)
            records = list(result) # Consome o resultado
            
            if not records:
                # Verifica se o nó ao menos existe
                node_exists = session.run("MATCH (a:AtoNormativo {urn_lexml: $urn}) RETURN a", urn=urn).single()
                if not node_exists:
                    raise HTTPException(status_code=404, detail=f"Ato Normativo com URN '{urn}' não encontrado.")
                else:
                    return [] # Nó existe, mas não tem relações

            # Formata a saída para ser mais clara
            relations = []
            for record in records:
                relations.append({
                    "origem": {"label": record["label_origem"], "id": record["id_origem"]},
                    "relacao": record["tipo_relacao"],
                    "destino": {"label": record["label_destino"], "id": record["id_destino"]}
                })
            return relations
            
    except Exception as e:
        logging.error(f"Erro ao consultar o Neo4j para a URN '{urn}': {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar a consulta no grafo.")

# Para executar localmente:
# uvicorn api.main:app --reload

import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IngestKnowledge")

DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
KNOWLEDGE_FILE = os.path.join(os.path.dirname(__file__), "conocimiento.txt")

def main():
    if not os.path.exists(KNOWLEDGE_FILE):
        logger.error(f"No se encontró el archivo {KNOWLEDGE_FILE}")
        return

    logger.info("Cargando documentos...")
    loader = TextLoader(KNOWLEDGE_FILE, encoding="utf-8")
    documents = loader.load()

    logger.info("Dividiendo el texto en fragmentos (chunks)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "]
    )
    docs = text_splitter.split_documents(documents)
    
    logger.info(f"Se crearon {len(docs)} fragmentos.")

    logger.info("Inicializando modelo de embeddings (nomic-embed-text)...")
    # Utilizamos el modelo nomic-embed-text en Ollama local
    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url="http://127.0.0.1:11434"
    )

    logger.info(f"Construyendo base de datos vectorial en {DB_DIR}...")
    
    # Creamos o actualizamos la base de datos Chroma
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=DB_DIR
    )
    
    logger.info("¡Base de datos vectorial creada y guardada con éxito!")

if __name__ == "__main__":
    main()

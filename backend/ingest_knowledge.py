import os
import logging
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IngestKnowledge")

DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def main():
    if not os.path.exists(DATA_DIR):
        logger.error(f"No se encontró la carpeta {DATA_DIR}")
        return

    logger.info("Cargando documentos...")
    loader = DirectoryLoader(
        DATA_DIR,
        glob="*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()

    if not documents:
        logger.warning(f"No se encontraron documentos .txt en {DATA_DIR}")
        return

    logger.info("Dividiendo el texto en fragmentos (chunks)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "]
    )
    docs = text_splitter.split_documents(documents)
    
    logger.info(f"Se crearon {len(docs)} fragmentos.")

    logger.info("Inicializando modelo de embeddings (nomic-embed-text)...")
    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url="http://127.0.0.1:11434"
    )

    logger.info(f"Construyendo base de datos vectorial en {DB_DIR}...")
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=DB_DIR
    )
    
    logger.info("¡Base de datos vectorial creada y guardada con éxito!")

if __name__ == "__main__":
    main()
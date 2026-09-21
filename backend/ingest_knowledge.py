import hashlib
import logging
import os
import re
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IngestKnowledge")

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "chroma_db"
KNOWLEDGE_FILE = BASE_DIR / "conocimiento.txt"
DATA_DIR = BASE_DIR / "data"


def discover_text_files() -> list[Path]:
    """Encuentra conocimiento.txt y todos los .txt dentro de data."""
    files: list[Path] = []
    if KNOWLEDGE_FILE.is_file():
        files.append(KNOWLEDGE_FILE)
    if DATA_DIR.is_dir():
        files.extend(sorted(DATA_DIR.rglob("*.txt")))
    return files


def load_text_documents(files: list[Path]) -> list[Document]:
    """Lee archivos UTF-8 y conserva su ruta relativa como fuente."""
    documents: list[Document] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as exc:
            logger.warning("No se pudo leer %s: %s", path, exc)
            continue

        if not text:
            logger.warning("Se omitió el archivo vacío: %s", path)
            continue

        documents.append(
            Document(
                page_content=text,
                metadata={"source": path.relative_to(BASE_DIR).as_posix()},
            )
        )
    return documents


def split_and_deduplicate(documents: list[Document]) -> tuple[list[Document], int]:
    """Divide el contenido y elimina fragmentos exactamente repetidos."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=650,
        chunk_overlap=80,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(documents)

    unique_chunks: list[Document] = []
    seen: set[str] = set()
    duplicates = 0

    for chunk in chunks:
        cleaned = re.sub(r"[ \t]+", " ", chunk.page_content)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        normalized = re.sub(r"\s+", " ", cleaned).casefold()
        if len(normalized) < 30:
            continue

        fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if fingerprint in seen:
            duplicates += 1
            continue

        seen.add(fingerprint)
        chunk.page_content = cleaned
        chunk.metadata["chunk_hash"] = fingerprint
        unique_chunks.append(chunk)

    return unique_chunks, duplicates


def replace_vector_database(
    documents: list[Document], embeddings: Embeddings | None = None
) -> None:
    """Reemplaza la colección para evitar datos viejos o duplicados."""
    if embeddings is None:
        embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url="http://127.0.0.1:11434",
        )

    # Verifica el modelo antes de reemplazar la colección que ya funciona.
    embeddings.embed_query("prueba de conexión")

    if DB_DIR.exists():
        current_store = Chroma(
            persist_directory=str(DB_DIR),
            embedding_function=embeddings,
        )
        try:
            current_store.delete_collection()
        except ValueError:
            pass

    logger.info("Construyendo la base vectorial en %s...", DB_DIR)
    Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(DB_DIR),
    )


def main() -> None:
    files = discover_text_files()
    if not files:
        logger.error("No se encontraron archivos de conocimiento .txt.")
        return

    logger.info("Archivos encontrados: %s", len(files))
    documents = load_text_documents(files)
    if not documents:
        logger.error("No se pudo cargar ningún documento con contenido.")
        return

    chunks, duplicates = split_and_deduplicate(documents)
    if not chunks:
        logger.error("No se generaron fragmentos útiles.")
        return

    logger.info("Documentos cargados: %s", len(documents))
    logger.info("Fragmentos repetidos eliminados: %s", duplicates)
    logger.info("Fragmentos que se guardarán: %s", len(chunks))

    replace_vector_database(chunks)
    logger.info("¡Base de datos vectorial creada y reemplazada con éxito!")


if __name__ == "__main__":
    main()

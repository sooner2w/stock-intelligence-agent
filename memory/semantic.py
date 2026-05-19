from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

CHROMA_DIR = Path(__file__).parent.parent / "chroma_store"
EMBED_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "agent_memories"


class SemanticMemory:
    """
    Chroma-backed vector store for semantic recall.
    Uses sentence-transformers locally — no API call, no cost.
    """

    def __init__(
        self,
        chroma_dir: Path = CHROMA_DIR,
        collection_name: str = COLLECTION_NAME,
        embed_model: str = EMBED_MODEL,
    ):
        self._embedder = SentenceTransformer(embed_model)
        self._client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(collection_name)

    # ------------------------------------------------------------------ #

    def add(self, text: str, metadata=None) -> None:
        """Embed and store a piece of text."""
        doc_id = _stable_id(text)
        embedding = self._embed(text)
        self._collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata or {}],
        )

    def search(self, query: str, n_results: int = 3) -> list[str]:
        """Return the top-n most semantically similar stored texts."""
        if self._collection.count() == 0:
            return []
        embedding = self._embed(query)
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, self._collection.count()),
            include=["documents"],
        )
        return results["documents"][0] if results["documents"] else []

    # ------------------------------------------------------------------ #

    def _embed(self, text: str) -> list[float]:
        return self._embedder.encode(text, convert_to_numpy=True).tolist()


def _stable_id(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()[:16]

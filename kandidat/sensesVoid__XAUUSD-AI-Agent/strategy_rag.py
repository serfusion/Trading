import chromadb
from chromadb.utils import embedding_functions

class StrategyRAG:
    def __init__(self, persist_dir: str = "./strategy_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.embedder = embedding_functions.OllamaEmbeddingFunction(
            url="http://localhost:11434/api/embeddings",
            model_name="nomic-embed-text",
        )
        self.collection = self.client.get_or_create_collection(
            name="trading_strategy", embedding_function=self.embedder
        )

    def ingest_strategy_doc(self, doc_id: str, text: str, metadata: dict | None = None):
        chunks = self._chunk(text, size=400, overlap=60)
        self.collection.upsert(
            ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
            documents=chunks,
            metadatas=[metadata or {}] * len(chunks),
        )

    def retrieve_relevant_rules(self, market_context: str, k: int = 4) -> list[str]:
        results = self.collection.query(query_texts=[market_context], n_results=k)
        return results["documents"][0]

    @staticmethod
    def _chunk(text: str, size: int, overlap: int) -> list[str]:
        words = text.split()
        chunks = []
        step = size - overlap
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + size])
            if chunk:
                chunks.append(chunk)
        return chunks
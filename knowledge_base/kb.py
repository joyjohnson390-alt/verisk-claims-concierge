import os
import glob
from typing import List
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = os.environ.get("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = "verisk_kb"
DOCS_DIR = "./data/knowledge_docs/"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

_model = None
_collection = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def init_kb():
    global _collection

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    model = _get_model()

    _collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if _collection.count() > 0:
        return _collection

    doc_files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    if not doc_files:
        print(f"No .txt files found in {DOCS_DIR}")
        return _collection

    documents = []
    metadatas = []
    ids = []
    doc_id = 0

    for filepath in doc_files:
        filename = os.path.basename(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = _chunk_text(text)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            documents.append(chunk)
            metadatas.append({"source": filename})
            ids.append(f"doc_{doc_id}")
            doc_id += 1

    if documents:
        embeddings = model.encode(documents).tolist()
        _collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        print(f"Ingested {len(documents)} chunks from {len(doc_files)} files into '{COLLECTION_NAME}'.")

    return _collection


def query_kb(question: str, n_results: int = 3) -> List[dict]:
    global _collection

    if _collection is None:
        init_kb()

    model = _get_model()
    query_embedding = model.encode([question]).tolist()

    results = _collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        output.append({
            "content": doc,
            "source": meta.get("source", "unknown"),
            "distance": float(dist),
        })

    return output

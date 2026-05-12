import os
import logging
import uuid
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION = os.getenv("QDRANT_COLLECTION", "aicc_docs")
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

_embedder = None
_qdrant = None


def get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
            _embedder = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Embedding model loaded")
        except Exception as e:
            logger.error("Failed to load embedding model: %s", str(e))
            logger.error("To fix: ensure internet access for model download, or set HF_HUB_OFFLINE=1 and mount model")
            raise HTTPException(
                status_code=503,
                detail=f"Embedding model unavailable: {str(e)}. Check RAG API logs for fix instructions.",
            )
    return _embedder


def get_qdrant():
    global _qdrant
    if _qdrant is None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            _qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            collections = [c.name for c in _qdrant.get_collections().collections]
            if COLLECTION not in collections:
                _qdrant.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
                logger.info("Created Qdrant collection: %s", COLLECTION)
        except Exception as e:
            logger.error("Qdrant connection failed: %s", str(e))
            raise HTTPException(status_code=503, detail=f"Qdrant unavailable: {str(e)}")
    return _qdrant


def _chunk_text(text: str, source: str) -> List[dict]:
    words = text.split()
    chunks = []
    i = 0
    chunk_num = 0
    while i < len(words):
        chunk_words = words[i:i + CHUNK_SIZE]
        chunk_text = " ".join(chunk_words)
        chunks.append({"text": chunk_text, "source": source, "chunk_num": chunk_num})
        chunk_num += 1
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning("Cannot read %s: %s", path, str(e))
        return None


class IngestRequest(BaseModel):
    path: str
    collection: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    collection: Optional[str] = None


@app.get("/health")
async def health():
    qdrant_status = "unknown"
    try:
        qc = get_qdrant()
        qc.get_collections()
        qdrant_status = "ok"
    except Exception:
        qdrant_status = "unavailable"

    return {
        "status": "ok",
        "service": "rag-api",
        "version": "0.1.0",
        "qdrant": qdrant_status,
        "embedding_model": EMBEDDING_MODEL,
    }


@app.post("/ingest")
async def ingest(req: IngestRequest):
    collection = req.collection or COLLECTION
    ingest_path = Path(req.path)

    if not ingest_path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {req.path}")

    files = []
    if ingest_path.is_dir():
        files = list(ingest_path.glob("**/*.md")) + list(ingest_path.glob("**/*.txt"))
    elif ingest_path.is_file():
        files = [ingest_path]

    if not files:
        return {"ingested": 0, "chunks": 0, "message": "No .md or .txt files found"}

    embedder = get_embedder()
    qc = get_qdrant()

    from qdrant_client.models import PointStruct

    total_chunks = 0
    ingested_files = []

    for file_path in files:
        content = _read_file(str(file_path))
        if not content:
            continue
        chunks = _chunk_text(content, str(file_path.name))
        points = []
        for chunk in chunks:
            embedding = embedder.encode(chunk["text"]).tolist()
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={"text": chunk["text"], "source": chunk["source"], "chunk_num": chunk["chunk_num"]},
            ))
        if points:
            qc.upsert(collection_name=collection, points=points)
            total_chunks += len(points)
            ingested_files.append(str(file_path.name))
        logger.info("Ingested %s: %d chunks", file_path.name, len(points))

    return {
        "ingested": len(ingested_files),
        "chunks": total_chunks,
        "files": ingested_files,
        "collection": collection,
    }


@app.post("/search")
async def search(req: SearchRequest):
    collection = req.collection or COLLECTION

    embedder = get_embedder()
    qc = get_qdrant()

    query_vector = embedder.encode(req.query).tolist()
    results = qc.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=req.limit,
    )

    hits = [
        {
            "score": round(r.score, 4),
            "text": r.payload.get("text", ""),
            "source": r.payload.get("source", ""),
            "chunk_num": r.payload.get("chunk_num", 0),
        }
        for r in results
    ]

    return {"query": req.query, "results": hits, "count": len(hits), "collection": collection}


@app.get("/collections")
async def list_collections():
    qc = get_qdrant()
    cols = qc.get_collections().collections
    return {"collections": [{"name": c.name} for c in cols]}


@app.delete("/collections/{name}")
async def delete_collection(name: str, confirm: Optional[str] = None):
    if confirm != "CONFIRM DANGEROUS":
        raise HTTPException(
            status_code=403,
            detail="Deleting a collection requires confirm=CONFIRM DANGEROUS query param",
        )
    qc = get_qdrant()
    qc.delete_collection(name)
    logger.warning("Collection deleted: %s", name)
    return {"deleted": name, "message": "Collection removed from Qdrant"}

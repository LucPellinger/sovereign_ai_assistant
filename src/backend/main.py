# backend/main.py
'''Main FastAPI application for iiRDS RAG system.
Provides endpoints for health check, document ingestion, and querying.
'''
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel, Field
import logging
from backend.rag.chroma_store import ChromaStore
from backend.rag.neo4j_store import Neo4jStore
from backend.iirds.ingest import IirdsIngestor
from backend.rag.pipeline import IirdsRagPipeline
from backend.llm_router import LLMRouter

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
CHROMA_PATH = os.getenv("CHROMA_PATH", "/data/chroma")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/uploads")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="iiRDS RAG API")

# stores & pipeline
chroma = ChromaStore(path=CHROMA_PATH)
neo4j  = Neo4jStore(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
neo4j.ensure_constraints()
ingestor = IirdsIngestor(chroma, neo4j)
pipeline = IirdsRagPipeline(chroma, neo4j)
llm_router = LLMRouter()

class QueryPayload(BaseModel):
    '''Payload model for query endpoint.'''
    question: str
    filters: dict = Field(default_factory=dict)
    mode: str = Field(default="local")
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int | None = None
    system_prompt: str | None = None
    debug: bool = False  

@app.get("/health")
def health():
    '''Health check endpoint.'''
    return {"status": "ok"}

@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    '''Ingest an iiRDS ZIP package.'''
    try:
        blob = await file.read()
        # optional: keep a copy of uploaded file
        try:
            with open(os.path.join(UPLOAD_DIR, file.filename), "wb") as f:
                f.write(blob)
        except Exception:
            pass

        stats = ingestor.ingest_zip_bytes(blob, file.filename)
        return {"status": "ok", **stats}
    except KeyError as e:
        raise HTTPException(400, f"Bad package: {e}")
    except Exception as e:
        import traceback
        print("🔥 INGEST ERROR 🔥")
        traceback.print_exc()            # <-- add this to print full stack trace
        raise HTTPException(500, f"Ingest failed: {e}")

@app.post("/query")
async def query(payload: QueryPayload, response: Response):
    '''Query endpoint to answer questions using RAG.'''
    ctx, cites, hits = pipeline.answer_context(
        payload.question, filters=payload.filters, k=8, return_hits=True  # ← return hits
    )

    # Tell clients if RAG was used
    rag_used = bool(hits)
    response.headers["X-RAG-Used"] = "true" if rag_used else "false"

    system_text = payload.system_prompt or (
        "You are a technical documentation assistant.\n"
        "Use ONLY the supplied Context to answer. If the Context is empty or insufficient, reply with 'NO_CONTEXT'.\n"
        "Add short citations as (parent_iri | path)."
    )
    messages = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": f"Context:\n{ctx}\n\nQuestion: {payload.question}"},
    ]

    try:
        llm = llm_router.pick(mode=payload.mode, model_override=payload.model)
    except RuntimeError as e:
        raise HTTPException(400, str(e))

    resp = llm.invoke(messages, temperature=payload.temperature, max_tokens=payload.max_tokens)

    out = {
        "answer": resp.content,
        "citations": cites,
        "used_mode": payload.mode,
        "used_model": payload.model or (llm_router.remote_model if payload.mode == "remote" else llm_router.local_model),
    }

    if payload.debug:
        # include retrieval diagnostics
        out["debug"] = {
            "rag_used": rag_used,
            "ctx_chars": len(ctx),
            "retrieved": [
                {
                    "id": h["id"],
                    "distance": h.get("distance"),
                    "parent_iri": h["metadata"].get("parent_iri"),
                    "path": h["metadata"].get("path"),
                    "text_preview": (h["text"][:240] + "…") if h["text"] else "",
                } for h in hits
            ],
            "filters": payload.filters,
        }

    return out

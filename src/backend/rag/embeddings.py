import os
from langchain_ollama import OllamaEmbeddings


# Use local embedding model via Ollama; adjust model name as needed
def get_embedder():
    base = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    model = (
        os.getenv("LOCAL_EMBEDDING_MODEL_NAME")
        or os.getenv("EMBED_MODEL")  # fallback if you kept this var around
        or "nomic-embed-text:latest"
    )
    emb = OllamaEmbeddings(
        model=model,
        base_url=base
    )

    #def embed(texts):
        # LangChain returns list of vectors for embed_documents
    #    return emb.embed_documents(texts)
    
    return lambda texts: emb.embed_documents(texts)

'''Chroma vector store interface for RAG.'''

from chromadb import PersistentClient
import logging
log = logging.getLogger("rag.chroma")

class ChromaStore:
    def __init__(self, path="/data/chroma", collection="iirds"):
        '''Initialize ChromaStore with persistent client and collection.
        
        Args:
            path: Filesystem path for persistent Chroma client storage.
            collection: Name of the Chroma collection to use.

        Returns:
            None
        '''
        self.client = PersistentClient(path=path)
        self.col = self.client.get_or_create_collection(collection)

    def upsert(self, payloads, embed_fn):
        '''Upsert payloads into the Chroma collection.
        
        Args:
            payloads: List of payload dictionaries with "id", "text", and "metadata".
            embed_fn: Function to generate embeddings from texts.

        Returns:
            None
        '''
        if not payloads: return
        ids = [p["id"] for p in payloads]
        docs = [p["text"] for p in payloads]
        metas = [p["metadata"] for p in payloads]
        embs = embed_fn(docs)
        self.col.upsert(ids=ids, embeddings=embs, documents=docs, metadatas=metas)

    def search(self, query: str, top_k: int, embed_fn, where: dict | None = None):
        '''Search the Chroma collection for similar documents.

        Args:
            query: Query string to search for.
            top_k: Number of top results to return.
            embed_fn: Function to generate embeddings from texts.
            where: Optional dictionary to filter results.

        Returns:
            List of search hits with "id", "text", "metadata", and "distance".
        '''
        log.debug(f"chroma.search: top_k={top_k} where={where}")
        qvec = embed_fn([query])[0]
        kwargs = {"query_embeddings": [qvec], "n_results": top_k}
        if where:  # only include if non-empty / not None
            kwargs["where"] = where
        res = self.col.query(**kwargs)
        n = len(res["ids"][0]) if res.get("ids") else 0
        log.info(f"chroma.search: returned {n} hits")        
        hits = []
        distances = res.get("distances", [[None]])[0]
        for i in range(len(res["ids"][0])):
            hits.append({
                "id": res["ids"][0][i],
                "text": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
                "distance": distances[i]
            })
        return hits

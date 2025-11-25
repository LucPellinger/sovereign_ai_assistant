# backend/rag/pipeline.py
from backend.rag.chroma_store import ChromaStore
from backend.rag.neo4j_store import Neo4jStore
from backend.rag.embeddings import get_embedder
from typing import Optional, Dict, Any, Tuple, List
import logging

log = logging.getLogger("rag.pipeline")

class IirdsRagPipeline:
    ARRAY_FIELDS = set() # {"product_variants", "components", "roles", "doc_types", "subjects", "phases"}

    def __init__(self, chroma: ChromaStore, neo4j: Neo4jStore):
        self.chroma = chroma
        self.neo4j = neo4j
        self.embed = get_embedder()

    def _build_where(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Build a Chroma 0.5+ filter:
        - For scalar fields: {"field": {"$eq": value}}
        - For array fields in metadata: {"field": {"$contains": value}}
        - For multiple conditions: {"$and": [ ... ]}
        """
        if not filters:
            return None

        clauses = []
        for key, val in filters.items():
            if val is None or (isinstance(val, str) and not val.strip()):
                continue

            # list/tuple -> ANY of the given values
            if isinstance(val, (list, tuple, set)):
                vals = list(val)
                # for array fields we can also use $in to match any membership
                # (Chroma treats $in as "value in field or equals")
                clauses.append({key: {"$in": vals}})
                continue

            # single value
            if key in self.ARRAY_FIELDS:
                clauses.append({key: {"$contains": val}})
            else:
                clauses.append({key: {"$eq": val}})

        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}
    
    # NEW: split graph filters vs direct Chroma filters
    def _prepare_graph_and_chroma_filters(self, filters: Optional[Dict[str, Any]]):
        if not filters:
            return None, {}

        filters = dict(filters)  # shallow copy

        graph_keys = {"product_variants", "components", "roles", "doc_types", "subjects", "phases"}

        graph_filters = {}
        chroma_filters = {}

        for k, v in filters.items():
            if k in graph_keys:
                graph_filters[k] = v
            else:
                chroma_filters[k] = v

        # Resolve graph filters to parent_iri set via Neo4j
        parent_iris = None
        if graph_filters:
            # normalise scalars vs lists
            def norm(x):
                if isinstance(x, (list, tuple, set)):
                    return list(x)
                return [x]
            parent_iris = self.neo4j.find_parents(
                product_variants=norm(graph_filters["product_variants"]) if "product_variants" in graph_filters else None,
                components=norm(graph_filters["components"]) if "components" in graph_filters else None,
                roles=norm(graph_filters["roles"]) if "roles" in graph_filters else None,
                doc_types=norm(graph_filters["doc_types"]) if "doc_types" in graph_filters else None,
                subjects=norm(graph_filters["subjects"]) if "subjects" in graph_filters else None,
                phases=norm(graph_filters["phases"]) if "phases" in graph_filters else None,
            )

        return parent_iris, chroma_filters


    def semantic_search(self, question: str, filters: Optional[Dict[str, Any]] = None, k: int = 8):
        # 1) Use Neo4j to pre-select parent_iri via graph filters (GraphRAG)
        parent_iris, chroma_filters = self._prepare_graph_and_chroma_filters(filters)

        # 2) Build Chroma where-clause from remaining scalar filters
        where = self._build_where(chroma_filters)

        # 3) If Neo4j returned parent_iris, add that constraint to Chroma
        if parent_iris:
            parent_clause = {"parent_iri": {"$in": parent_iris}}
            if where:
                where = {"$and": [where, parent_clause]}
            else:
                where = parent_clause

        log.info(f"semantic_search: q='{question[:80]}' k={k} where={where}")
        hits = self.chroma.search(question, k, self.embed, where=where)
        log.info(f"semantic_search: hits={len(hits)}")
        return hits


    def answer_context(
        self, question: str, filters: Optional[Dict[str, Any]] = None, k: int = 8, return_hits: bool = False
    ) -> Tuple[str, list, List[dict]]:
        hits = self.semantic_search(question, filters, k)
        ctx = "\n\n---\n\n".join(h["text"] for h in hits)
        log.info(f"answer_context: ctx_chars={len(ctx)} citations={len(hits)}")
        citations = [{"parent_iri": h["metadata"]["parent_iri"], "path": h["metadata"]["path"]} for h in hits]
        return (ctx, citations, hits) if return_hits else (ctx, citations)

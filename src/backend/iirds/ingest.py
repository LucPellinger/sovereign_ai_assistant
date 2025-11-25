import io, zipfile, hashlib
from pathlib import Path
from typing import Dict, List, Optional
from backend.iirds.rdf_extract import parse_metadata_rdf
from backend.iirds.content_extract import extract_text_from_xhtml, extract_text_from_pdf
from backend.rag.chunking import chunk_text
from backend.rag.embeddings import get_embedder
from backend.rag.chroma_store import ChromaStore
from backend.rag.neo4j_store import Neo4jStore

import logging
log = logging.getLogger("iirds.ingest")

SUPPORTED_TEXT = (".xhtml", ".htm", ".html")
SUPPORTED_PDF = (".pdf",)

class IirdsIngestor:
    def __init__(self, chroma: ChromaStore, neo4j: Neo4jStore, base_source="upload"):
        self.chroma = chroma
        self.neo4j = neo4j
        self.embed = get_embedder()
        self.base_source = base_source

    # NEW: ensure metadata is scalar-only for Chroma
    def _scalarize_meta_values(self, attrs: Dict) -> Dict:
        out: Dict = {}
        for k, v in attrs.items():
            if isinstance(v, (list, tuple, set)):
                vals = [str(x) for x in v]
                # join all values; still human-readable, but scalar
                out[k] = ";".join(vals) if vals else None
            else:
                out[k] = v
        return out

    def ingest_zip_bytes(self, blob: bytes, zip_name: str,
                         chunk_tokens: int = 250, overlap_tokens: int = 40,
                         min_chunk_chars: int = 40) -> Dict:
        zf = zipfile.ZipFile(io.BytesIO(blob))

        try:
            rdf_bytes = zf.read("META-INF/metadata.rdf")
        except KeyError as e:
            raise KeyError("META-INF/metadata.rdf not found in package") from e

        graph_data = parse_metadata_rdf(rdf_bytes)
        self.neo4j.upsert_graph(graph_data)

        package_iri = (graph_data.get("package") or {}).get("iri")
        chroma_payloads: List[Dict] = []
        chunk_nodes: List[Dict] = []
        attrs_cache: Dict[str, Dict] = {}

        for rend in graph_data.get("renditions", []):
            raw_src = (rend.get("source_path") or "").lstrip("/")
            parent_iri = rend["parent_iri"]
            fmt = rend.get("format") or ""
            if not raw_src:
                continue

            src = self._resolve_zip_path(zf, raw_src)
            if not src:
                continue

            try:
                content_bytes = zf.read(src)
            except KeyError:
                continue

            ext = Path(src).suffix.lower()
            if ext in SUPPORTED_TEXT:
                text = extract_text_from_xhtml(content_bytes)
            elif ext in SUPPORTED_PDF:
                text = extract_text_from_pdf(content_bytes)
            else:
                continue

            if not text or text.strip() == "":
                continue

            if parent_iri not in attrs_cache:
                attrs_cache[parent_iri] = {
                    "product_variants": self.neo4j.fetch_variants(parent_iri),
                    "components": self.neo4j.fetch_components(parent_iri),
                    "roles": self.neo4j.fetch_roles(parent_iri),
                    "doc_types": self.neo4j.fetch_doc_types(parent_iri),
                }
            cached_attrs = attrs_cache[parent_iri]

            # NEW: convert list-valued attrs to scalar strings for Chroma
            scalar_attrs = self._scalarize_meta_values(cached_attrs)

            for start, end, chunk in chunk_text(text, target_tokens=chunk_tokens, overlap_tokens=overlap_tokens):
                if len(chunk) < min_chunk_chars:
                    continue
                chunk_id = self._chunk_id(zip_name, src, start, end, chunk)
                meta = {
                    "chunk_id": chunk_id,
                    "source_zip": zip_name,
                    "package": package_iri,
                    "path": src,
                    "parent_iri": parent_iri,
                    "format": fmt,
                    "text_len": len(chunk),
                    **scalar_attrs,
                }
                chroma_payloads.append({"id": chunk_id, "text": chunk, "metadata": meta})
                chunk_nodes.append({"chunk_id": chunk_id, "path": src, "start": start, "end": end, "parent_iri": parent_iri})

        if chroma_payloads:
            self.chroma.upsert(chroma_payloads, self.embed)

        if chunk_nodes:
            self.neo4j.link_chunks(chunk_nodes)

        log.info(
            f"ingest_zip_bytes: package={package_iri} "
            f"topics={len(graph_data.get('topics', []))} "
            f"renditions={len(graph_data.get('renditions', []))} "
            f"chunks={len(chroma_payloads)}"
        )

        return {
            "package": package_iri,
            "topics": len(graph_data.get("topics", [])),
            "documents": len(graph_data.get("documents", [])),
            "chunks": len(chroma_payloads),
            "renditions_seen": len(graph_data.get("renditions", [])),
        }

    def _chunk_id(self, zip_name: str, path: str, start: int, end: int, text: str) -> str:
        h = hashlib.sha1(f"{zip_name}|{path}|{start}|{end}|{text[:64]}".encode("utf-8")).hexdigest()
        return f"chk_{h}"

    def _resolve_zip_path(self, zf: zipfile.ZipFile, src: str) -> Optional[str]:
        names = zf.namelist()
        src_norm = src.lstrip("/")

        # 1) exact match
        if src_norm in names:
            return src_norm

        # 2) case-insensitive match
        lowered = {n.lower(): n for n in names}
        if src_norm.lower() in lowered:
            return lowered[src_norm.lower()]

        # 3) basename match
        tail = Path(src_norm).name.lower()
        candidates = [n for n in names if n.lower().endswith("/" + tail) or n.lower() == tail]
        if candidates:
            # prefer content/ paths where present
            for n in candidates:
                if n.lower().startswith("content/"):
                    return n
            return candidates[0]

        return None

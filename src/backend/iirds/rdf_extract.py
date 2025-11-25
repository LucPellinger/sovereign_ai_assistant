from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, DCTERMS, DC
from typing import Dict, Optional, List

IIRDS = Namespace("http://iirds.tekom.de/iirds#")
SUPPORTED_EXT = (".xhtml", ".html", ".htm", ".pdf")

def _one(g: Graph, s, p) -> Optional[str]:
    o = next(g.objects(s, p), None)
    return str(o) if o is not None else None

def _many(g: Graph, s, p) -> List[str]:
    return [str(o) for o in g.objects(s, p)]

def parse_metadata_rdf(rdf_bytes: bytes) -> Dict:
    g = Graph()
    g.parse(data=rdf_bytes, format="xml")

    data = {
        "package": None,
        "documents": [],
        "topics": [],
        "renditions": []
    }

    # Package
    for s in g.subjects(RDF.type, IIRDS.Package):
        data["package"] = {"iri": str(s)}
        break

    # Collect IUs
    for iu in g.subjects(RDF.type, IIRDS.Document):
        data["documents"].append(_extract_iu(g, iu, is_topic=False))
    for iu in g.subjects(RDF.type, IIRDS.Topic):
        data["topics"].append(_extract_iu(g, iu, is_topic=True))

    seen = set()

    # Renditions --------------------------------------------------------------
    def add_rendition(parent_iri: str, src: Optional[str], fmt: Optional[str]):
        if not src:
            return
        s = src.lower()
        if not any(s.endswith(ext) for ext in SUPPORTED_EXT):
            return
        key = (parent_iri, src, fmt)
        if key in seen:
            return        # <--- skip duplicates
        seen.add(key)
        data["renditions"].append({
            "parent_iri": parent_iri,
            "source_path": src,
            "format": fmt
        })

    # helpers for both vocab styles
    P_HAS_RENDITION = [IIRDS["has-rendition"], IIRDS.hasRendition, IIRDS.Rendition]
    P_SOURCE = [IIRDS["source"], IIRDS.Source, DCTERMS.source]
    P_FORMAT = [IIRDS["format"], IIRDS.Format, DCTERMS.format]
    P_CONTENT_REF = [IIRDS["contentReference"], IIRDS.contentReference]

    # 1) Explicit rendition nodes
    for r in g.subjects(RDF.type, IIRDS.Rendition):
        fmt = (_first_of(g, r, P_FORMAT) or None)
        src = (_first_of(g, r, P_CONTENT_REF + P_SOURCE) or None)
        # find parent IU via common preds
        for parent_pred in [IIRDS["has-rendition"], IIRDS.hasRendition, IIRDS.Rendition]:
            for parent in g.subjects(parent_pred, r):
                if (parent, RDF.type, IIRDS.Topic) in g or (parent, RDF.type, IIRDS.Document) in g:
                    add_rendition(str(parent), src, fmt)

    # 2) Property-based rendition on IU + forgiving fallback
    all_ius = [*(d["iri"] for d in data["documents"]), *(t["iri"] for t in data["topics"])]
    for iri in all_ius:
        iu = URIRef(iri)

        # IU → rendition node
        for p in P_HAS_RENDITION:
            for r in g.objects(iu, p):
                fmt = (_first_of(g, r, P_FORMAT) or None)
                src = (_first_of(g, r, P_CONTENT_REF + P_SOURCE) or None)
                add_rendition(iri, src, fmt)

        # IU → direct content path
        for p in (P_CONTENT_REF + P_SOURCE):
            for o in g.objects(iu, p):
                add_rendition(iri, str(o), None)

        # fallback: any predicate value that looks like a file path
        for p, o in g.predicate_objects(iu):
            if isinstance(o, (URIRef, Literal)):
                s = str(o)
                ls = s.lower()
                if any(ls.endswith(ext) for ext in SUPPORTED_EXT):
                    add_rendition(iri, s, None)

    print(f"[rdf_extract] docs={len(data['documents'])} topics={len(data['topics'])} renditions={len(data['renditions'])}")
    return data

def _first_of(g: Graph, s, preds: List) -> Optional[str]:
    for p in preds:
        val = _one(g, s, p)
        if val:
            return val
    return None

def _extract_iu(g: Graph, iu, is_topic: bool) -> Dict:
    # labels/titles/language
    label = (_one(g, iu, RDFS.label) or _one(g, iu, DCTERMS.title) or _one(g, iu, DC.title))
    language = (_one(g, iu, IIRDS["language"]) or _one(g, iu, DCTERMS.language) or _one(g, iu, DC.language))

    # status (optional)
    status_val  = _one(g, iu, IIRDS["has-content-lifecycle-status-value"]) or _one(g, iu, IIRDS.InformationUnitLifecycleStatusValue)
    status_date = _one(g, iu, IIRDS["dateOfStatus"]) or _one(g, iu, IIRDS.InformationUnitLifecycleStatusDate)

    # Attributes via modern, hyphenated predicates (fall back to legacy)
    doc_types  = _many(g, iu, IIRDS["is-applicable-for-document-type"]) or _many(g, iu, IIRDS.DocumentType)
    variants   = _many(g, iu, IIRDS["relates-to-product-variant"])     or _many(g, iu, IIRDS.ProductVariant)
    components = _many(g, iu, IIRDS["relates-to-component"])           or _many(g, iu, IIRDS.Component)
    roles      = _many(g, iu, IIRDS["relates-to-qualification"])       or _many(g, iu, IIRDS.hasRole)
    subjects   = _many(g, iu, IIRDS["has-subject"])                    or _many(g, iu, IIRDS.Subject)
    phases     = _many(g, iu, IIRDS["relates-to-product-lifecycle-phase"]) or _many(g, iu, IIRDS.ProductLifecyclePhase)

    return {
        "iri": str(iu), "label": label, "language": language,
        "doc_types": doc_types, "product_variants": variants, "components": components,
        "roles": roles, "subjects": subjects, "phases": phases,
        "status": {"value": status_val, "date": status_date},
        "kind": "Topic" if is_topic else "Document",
    }

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS, DC
from typing import Dict

IIRDS = Namespace("http://iirds.tekom.de/iirds#")

def _first_str(g, subj, pred):
    for o in g.objects(subj, pred):
        return str(o)
    return None

def _vals_any(g, subj, preds):
    vals = []
    for p in preds:
        vals.extend(str(o) for o in g.objects(subj, p))
    return list(dict.fromkeys(vals))

def parse_metadata_rdf(rdf_bytes: bytes) -> Dict:
    g = Graph()
    g.parse(data=rdf_bytes, format="xml")

    data = {
        "package": None, "documents": [], "topics": [],
        "variants": [], "components": [], "roles": [], "subjects": [],
        "phases": [], "events": [], "renditions": []
    }

    for s in g.subjects(RDF.type, IIRDS.Package):
        data["package"] = {"iri": str(s)}

    for iu in g.subjects(RDF.type, IIRDS.Document):
        data["documents"].append(_extract_information_unit(g, iu, is_topic=False))
    for iu in g.subjects(RDF.type, IIRDS.Topic):
        data["topics"].append(_extract_information_unit(g, iu, is_topic=True))

    def add_rendition(parent_iri, rnode):
        src = _first_str(g, rnode, IIRDS.Source) or _first_str(g, rnode, DCTERMS.source)
        fmt = _first_str(g, rnode, IIRDS.Format)
        if src:
            data["renditions"].append({"parent_iri": str(parent_iri), "source_path": str(src), "format": str(fmt) if fmt else None})

    for iu in [*data["documents"], *data["topics"]]:
        subj = URIRef(iu["iri"])
        for p in (IIRDS.Rendition, IIRDS.hasRendition):
            for r in g.objects(subj, p):
                add_rendition(subj, r)

    for r in g.subjects(RDF.type, IIRDS.Rendition):
        for parent in g.subjects(None, r):
            if (parent, RDF.type, IIRDS.Topic) in g or (parent, RDF.type, IIRDS.Document) in g:
                add_rendition(parent, r)

    return data

def _extract_information_unit(g: Graph, iu, is_topic: bool) -> Dict:
    label = _first_str(g, iu, RDFS.label) or _first_str(g, iu, DCTERMS.title) or _first_str(g, iu, DC.title)
    language = _first_str(g, iu, IIRDS.Language) or _first_str(g, iu, DCTERMS.language) or _first_str(g, iu, DC.language)
    status_val  = _first_str(g, iu, IIRDS.InformationUnitLifecycleStatusValue)
    status_date = _first_str(g, iu, IIRDS.InformationUnitLifecycleStatusDate)

    doc_types  = _vals_any(g, iu, [IIRDS.DocumentType])
    variants   = _vals_any(g, iu, [IIRDS.ProductVariant])
    components = _vals_any(g, iu, [IIRDS.Component])
    roles      = _vals_any(g, iu, [IIRDS.Role, IIRDS.hasRole])
    subjects   = _vals_any(g, iu, [IIRDS.Subject, IIRDS.hasSubject])
    phases     = _vals_any(g, iu, [IIRDS.ProductLifecyclePhase])

    return {
        "iri": str(iu), "label": label, "language": language,
        "doc_types": doc_types, "product_variants": variants, "components": components,
        "roles": roles, "subjects": subjects, "phases": phases,
        "status": {"value": status_val, "date": status_date},
        "kind": "Topic" if is_topic else "Document",
    }

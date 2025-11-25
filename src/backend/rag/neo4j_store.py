# neo4j_store.py
import time
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

class Neo4jStore:
    def __init__(self, uri="bolt://neo4j:7687", user="neo4j", password="password"):
        # retry connect (e.g., 30s)
        deadline = time.time() + 30
        last_err = None
        while time.time() < deadline:
            try:
                self.driver = GraphDatabase.driver(uri, auth=(user, password))
                # simple ping
                with self.driver.session() as s:
                    s.run("RETURN 1").consume()
                break
            except ServiceUnavailable as e:
                last_err = e
                time.sleep(1)
        if not hasattr(self, "driver"):
            raise last_err or RuntimeError("Could not connect to Neo4j")

    def ensure_constraints(self):
        stmts = [
            "CREATE CONSTRAINT pkg_iri   IF NOT EXISTS FOR (p:Package)   REQUIRE p.iri IS UNIQUE",
            "CREATE CONSTRAINT doc_iri   IF NOT EXISTS FOR (n:Document)  REQUIRE n.iri IS UNIQUE",
            "CREATE CONSTRAINT topic_iri IF NOT EXISTS FOR (n:Topic)     REQUIRE n.iri IS UNIQUE",
            "CREATE CONSTRAINT rend_src  IF NOT EXISTS FOR (r:Rendition) REQUIRE r.source_path IS UNIQUE",
            "CREATE CONSTRAINT chunk_id  IF NOT EXISTS FOR (c:Chunk)     REQUIRE c.chunk_id IS UNIQUE",
        ]
        with self.driver.session() as s:
            for q in stmts:
                s.run(q)

    def upsert_graph(self, data):
        with self.driver.session() as s:
            if data.get("package"):
                s.run("MERGE (p:Package {iri:$iri})", iri=data["package"]["iri"])

            for node in data.get("documents", []) + data.get("topics", []):
                s.run(f"""
                    MERGE (n:{node["kind"]} {{iri:$iri}})
                    SET n.label=$label, n.language=$language, n.status_value=$status_value, n.status_date=$status_date
                """, iri=node["iri"], label=node.get("label"), language=node.get("language"),
                     status_value=(node.get("status") or {}).get("value"),
                     status_date=(node.get("status") or {}).get("date"))

                if data.get("package"):
                    s.run("""
                        MATCH (n {iri:$iri}), (p:Package {iri:$piri})
                        MERGE (n)-[:PART_OF_PACKAGE]->(p)
                    """, iri=node["iri"], piri=data["package"]["iri"])

                self._attach_array(s, node["iri"], node.get("doc_types", []), "DocType", "APPLIES_TO_DOCUMENT_TYPE")
                self._attach_array(s, node["iri"], node.get("product_variants", []), "ProductVariant", "RELATES_TO_PRODUCT_VARIANT")
                self._attach_array(s, node["iri"], node.get("components", []), "Component", "RELATES_TO_COMPONENT")
                self._attach_array(s, node["iri"], node.get("roles", []), "Role", "HAS_ROLE")
                self._attach_array(s, node["iri"], node.get("subjects", []), "Subject", "HAS_SUBJECT")
                self._attach_array(s, node["iri"], node.get("phases", []), "LifecyclePhase", "HAS_LIFECYCLE_PHASE")

            for r in data.get("renditions", []):
                s.run("""
                    MERGE (x {iri:$parent})
                    MERGE (r:Rendition {source_path:$src})
                    SET r.format=$fmt
                    MERGE (x)-[:HAS_RENDITION]->(r)
                """, parent=r["parent_iri"], src=r["source_path"], fmt=r.get("format"))

    def _attach_array(self, s, iri, values, label, rel):
        for val in values:
            s.run(f"""
                MATCH (n {{iri:$iri}})
                MERGE (m:{label} {{iri:$val}})
                MERGE (n)-[:{rel}]->(m)
            """, iri=iri, val=val)

    def link_chunks(self, chunks):
        with self.driver.session() as s:
            for c in chunks:
                s.run("""
                    MERGE (ch:Chunk {chunk_id:$cid})
                    SET ch.path=$path, ch.start_char=$start, ch.end_char=$end
                    WITH ch
                    MATCH (n {iri:$parent})
                    MERGE (ch)-[:DERIVED_FROM]->(n)
                """, cid=c["chunk_id"], path=c["path"], start=c["start"], end=c["end"], parent=c["parent_iri"])

    # Convenience collection helpers
    def _collect(self, s, iri, rel):
        rec = s.run(f"""
            MATCH (n {{iri:$iri}})-[:{rel}]->(m)
            RETURN collect(distinct m.iri) AS items
        """, iri=iri).single()
        return rec["items"] if rec else []

    def fetch_variants(self, iri):
        with self.driver.session() as s:
            return self._collect(s, iri, "RELATES_TO_PRODUCT_VARIANT")
    def fetch_components(self, iri):
        with self.driver.session() as s:
            return self._collect(s, iri, "RELATES_TO_COMPONENT")
    def fetch_roles(self, iri):
        with self.driver.session() as s:
            return self._collect(s, iri, "HAS_ROLE")
    def fetch_doc_types(self, iri):
        with self.driver.session() as s:
            return self._collect(s, iri, "APPLIES_TO_DOCUMENT_TYPE")

    # NEW: GraphRAG helper – find IU IRIs matching high-level filters
    def find_parents(
        self,
        product_variants=None,
        components=None,
        roles=None,
        doc_types=None,
        subjects=None,
        phases=None,
    ):
        product_variants = list(product_variants or [])
        components       = list(components or [])
        roles            = list(roles or [])
        doc_types        = list(doc_types or [])
        subjects         = list(subjects or [])
        phases           = list(phases or [])

        with self.driver.session() as s:
            q = "MATCH (n) "
            where_clauses = []
            params = {}

            if product_variants:
                q += "MATCH (n)-[:RELATES_TO_PRODUCT_VARIANT]->(pv:ProductVariant) "
                where_clauses.append("pv.iri IN $product_variants")
                params["product_variants"] = product_variants

            if components:
                q += "MATCH (n)-[:RELATES_TO_COMPONENT]->(c:Component) "
                where_clauses.append("c.iri IN $components")
                params["components"] = components

            if roles:
                q += "MATCH (n)-[:HAS_ROLE]->(r:Role) "
                where_clauses.append("r.iri IN $roles")
                params["roles"] = roles

            if doc_types:
                q += "MATCH (n)-[:APPLIES_TO_DOCUMENT_TYPE]->(d:DocType) "
                where_clauses.append("d.iri IN $doc_types")
                params["doc_types"] = doc_types

            if subjects:
                q += "MATCH (n)-[:HAS_SUBJECT]->(s:Subject) "
                where_clauses.append("s.iri IN $subjects")
                params["subjects"] = subjects

            if phases:
                q += "MATCH (n)-[:HAS_LIFECYCLE_PHASE]->(ph:LifecyclePhase) "
                where_clauses.append("ph.iri IN $phases")
                params["phases"] = phases

            if where_clauses:
                q += "WHERE " + " AND ".join(where_clauses) + " "

            q += "RETURN collect(distinct n.iri) AS iris"

            rec = s.run(q, **params).single()
            return rec["iris"] if rec and rec["iris"] is not None else []

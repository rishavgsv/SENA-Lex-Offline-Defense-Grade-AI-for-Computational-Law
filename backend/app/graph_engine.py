import networkx as nx
import spacy
import logging
from typing import List, Dict, Any

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logging.warning("spacy model 'en_core_web_sm' not found in graph_engine. Proceeding without entity extraction.")
    nlp = None

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build_from_chunks(self, chunks: List[Dict[str, Any]]):
        """Construct a knowledge graph mapping documents to clauses and entities."""
        for chunk in chunks:
            doc_id = chunk.get("document", "Unknown_Doc")
            clause_id = chunk.get("clause_id", "General")
            text = chunk.get("text", "")
            
            # Map Document -> Clause
            clause_node = f"{doc_id}::{clause_id}"
            
            self.graph.add_node(doc_id, type="Document")
            self.graph.add_node(clause_node, type="Clause", text=text, title=chunk.get("clause_title", ""))
            self.graph.add_edge(doc_id, clause_node, relation="CONTAINS")
            
            # Use spaCy to extract entities (Parties, Dates, Locations)
            if nlp:
                doc = nlp(text)
                for ent in doc.ents:
                    # Filter for relevant legal entities
                    if ent.label_ in ["ORG", "PERSON", "GPE", "DATE", "MONEY"]:
                        ent_node = f"{ent.label_}::{ent.text}"
                        self.graph.add_node(ent_node, type="Entity", label=ent.label_, name=ent.text)
                        # Link Clause -> Entity
                        self.graph.add_edge(clause_node, ent_node, relation="MENTIONS")

    def get_related_entities(self, clause_id: str, doc_id: str) -> List[str]:
        """Fetch entities involved in a specific clause."""
        clause_node = f"{doc_id}::{clause_id}"
        if clause_node in self.graph:
            return [v for u, v, d in self.graph.edges(clause_node, data=True) if d.get("relation") == "MENTIONS"]
        return []

    def get_clause_context(self, entity_name: str) -> List[str]:
        """Find which clauses mention a specific entity to aid multi-hop logic."""
        clauses = []
        for n, data in self.graph.nodes(data=True):
            if data.get("type") == "Entity" and data.get("name") == entity_name:
                for u, v, rel in self.graph.in_edges(n, data=True):
                    if rel.get("relation") == "MENTIONS":
                        clauses.append(u)
        return list(set(clauses))

graph_engine = KnowledgeGraph()

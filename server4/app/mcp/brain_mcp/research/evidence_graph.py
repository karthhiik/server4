"""
Evidence Graph — Per-deck entity-relation graph with source lineage.

Each deck run builds a dynamic knowledge graph:
- Nodes: entities (companies, markets, metrics, technologies, personas)
- Edges: relationships (supports, contradicts, compares_to, depends_on, etc.)
- Every node/edge stores source lineage traceable to FactPackets
"""

import logging
import re
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.mcp.brain_mcp.research.models import FactPacket, SlideKind

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    COMPANY = "company"
    MARKET = "market"
    METRIC = "metric"
    TECHNOLOGY = "technology"
    PERSONA = "persona"
    PRODUCT = "product"
    TREND = "trend"
    REGULATION = "regulation"


class RelationType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    COMPARES_TO = "compares_to"
    DEPENDS_ON = "depends_on"
    GREW_FROM = "grew_from"
    COMPETES_WITH = "competes_with"
    ACQUIRED_BY = "acquired_by"
    MENTIONED_BY = "mentioned_by"
    PART_OF = "part_of"


# ── Regex patterns for entity extraction ──────────────────────────

_COMPANY_SUFFIXES = r"(?:Inc\.?|Corp\.?|Ltd\.?|LLC|Co\.?|PLC|GmbH|S\.A\.?|AG)"
_COMPANY_PAT = re.compile(
    rf"\b([A-Z][a-zA-Z0-9&'-]+(?:\s+[A-Z][a-zA-Z0-9&'-]+)*\s*{_COMPANY_SUFFIXES})\b"
)
_STANDALONE_COMPANY_PAT = re.compile(
    r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){0,3})\b"
)
_MARKET_PAT = re.compile(
    r"\b([A-Za-z\s\-]+?)\s+(?:market|industry|sector|space|landscape)\b",
    re.IGNORECASE,
)
_MONEY_PAT = re.compile(
    r"\$\s*([\d,.]+)\s*(billion|trillion|million|B|T|M|bn|mn|k|K)?\b",
    re.IGNORECASE,
)
_PERCENT_PAT = re.compile(r"([\d,.]+)\s*%")
_USER_PAT = re.compile(
    r"([\d,.]+)\s*(million|billion|M|B|mn|bn|k|K)?\s+"
    r"(?:users|customers|subscribers|downloads|installations|accounts|merchants|DAU|MAU)",
    re.IGNORECASE,
)
_REVENUE_PAT = re.compile(
    r"(?:\$\s*)([\d,.]+)\s*(billion|trillion|million|B|T|M|bn|mn)?\s+"
    r"(?:revenue|ARR|MRR|GMV|ACV|run.rate)",
    re.IGNORECASE,
)

_TECH_TERMS = {
    "AI", "ML", "NLP", "LLM", "GPT", "blockchain", "SaaS", "PaaS", "IaaS",
    "IoT", "API", "SDK", "cloud", "edge computing", "quantum", "5G", "AR", "VR",
    "XR", "deep learning", "reinforcement learning", "computer vision",
    "autonomous", "robotics", "fintech", "biotech", "healthtech", "edtech",
    "regtech", "proptech", "agritech", "cybersecurity", "zero trust",
    "microservices", "kubernetes", "serverless", "web3", "DeFi", "NFT",
    "metaverse", "generative AI", "RAG", "vector database", "transformer",
}
_TECH_PAT = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _TECH_TERMS) + r")\b",
    re.IGNORECASE,
)

# Words to skip when extracting standalone company names
_STOP_WORDS = {
    "The", "This", "That", "These", "Those", "With", "From", "About",
    "Over", "Under", "Into", "Through", "Between", "During", "Before",
    "After", "Above", "Below", "Each", "Every", "Both", "Many", "Some",
    "Most", "Other", "More", "Less", "Very", "Also", "Just", "Only",
    "However", "Therefore", "Moreover", "Furthermore", "Additionally",
    "According", "Based", "Due", "Given", "While", "Although", "Since",
    "Because", "Although", "Despite", "Instead", "Meanwhile", "Total",
    "Annual", "Monthly", "Weekly", "Daily", "Average", "Growth", "Rate",
    "Year", "Quarter", "Report", "Source", "Data", "Figure", "Table",
    "Market", "Industry", "Sector", "Company", "Revenue", "Profit",
    "Global", "North", "South", "East", "West", "United", "States",
    "Europe", "Asia", "World",
}


@dataclass
class GraphNode:
    id: str
    name: str
    entity_type: EntityType
    attributes: dict[str, Any] = field(default_factory=dict)
    fact_packet_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    slide_relevance: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "attributes": dict(self.attributes),
            "fact_packet_ids": list(self.fact_packet_ids),
            "confidence": self.confidence,
            "slide_relevance": dict(self.slide_relevance),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphNode":
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=EntityType(data["entity_type"]),
            attributes=data.get("attributes", {}),
            fact_packet_ids=data.get("fact_packet_ids", []),
            confidence=data.get("confidence", 0.0),
            slide_relevance=data.get("slide_relevance", {}),
        )


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relation: RelationType
    strength: float = 0.5
    source_fact_ids: list[str] = field(default_factory=list)
    bidirectional: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation.value,
            "strength": self.strength,
            "source_fact_ids": list(self.source_fact_ids),
            "bidirectional": self.bidirectional,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphEdge":
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation=RelationType(data["relation"]),
            strength=data.get("strength", 0.5),
            source_fact_ids=data.get("source_fact_ids", []),
            bidirectional=data.get("bidirectional", False),
        )


class EvidenceGraph:
    """In-session evidence graph built from FactPackets."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._fact_index: dict[str, list[str]] = {}  # fact_id -> node_ids
        self._name_to_id: dict[str, str] = {}  # normalized_name -> node_id

    # ── Public API ────────────────────────────────────────────

    def add_fact_packet(self, packet: FactPacket) -> list[str]:
        """
        Extract entities from a FactPacket and add nodes/edges.

        1. Extract entity names from the claim text
        2. Create or update nodes
        3. Create edges between co-mentioned entities
        4. Track which FactPackets contribute to which nodes

        Returns list of node IDs created/updated.
        """
        text = packet.claim
        if packet.raw_snippet:
            text = f"{text} {packet.raw_snippet}"

        entities = self._extract_entities(text)
        if not entities:
            return []

        node_ids: list[str] = []
        for name, etype in entities:
            node_id = self._upsert_node(name, etype, packet)
            node_ids.append(node_id)

        # Track fact->nodes index
        self._fact_index[packet.id] = node_ids

        # Create edges between co-mentioned entities in same fact
        relation = self._infer_relation(packet)
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                self._add_edge(
                    node_ids[i], node_ids[j], relation, packet.id, packet.confidence
                )

        logger.debug(
            "evidence_graph_updated",
            fact_id=packet.id,
            nodes_affected=len(node_ids),
            total_nodes=len(self._nodes),
            total_edges=len(self._edges),
        )
        return node_ids

    def get_slide_context(
        self, slide_kind: SlideKind, topic: str, max_nodes: int = 20
    ) -> dict[str, Any]:
        """
        Get the most relevant subgraph for a specific slide.

        Returns: {
            "entities": [...],
            "relationships": [...],
            "summary": "one-paragraph context",
            "key_metrics": {...}
        }
        """
        slide_key = slide_kind.value

        # Score nodes by slide relevance + topic match
        scored: list[tuple[float, GraphNode]] = []
        topic_lower = topic.lower()
        for node in self._nodes.values():
            relevance = node.slide_relevance.get(slide_key, 0.0)
            # Boost if node name appears in topic
            name_match = 0.3 if node.name.lower() in topic_lower else 0.0
            # Boost by confidence
            conf_boost = node.confidence * 0.2
            total = relevance + name_match + conf_boost
            if total > 0:
                scored.append((total, node))

        # Sort descending, take top max_nodes
        scored.sort(key=lambda x: x[0], reverse=True)
        top_nodes = scored[:max_nodes]
        top_ids = {n.id for _, n in top_nodes}

        # Find edges between top nodes
        relevant_edges = [
            e for e in self._edges
            if e.source_id in top_ids and e.target_id in top_ids
        ]

        # Extract key metrics from metric nodes
        key_metrics: dict[str, Any] = {}
        for _, node in top_nodes:
            if node.entity_type == EntityType.METRIC and node.attributes:
                key_metrics[node.name] = node.attributes

        # Build summary
        entity_names = [n.name for _, n in top_nodes[:10]]
        summary = (
            f"For the {slide_kind.value} slide about '{topic}', "
            f"key entities include: {', '.join(entity_names)}. "
            f"The evidence graph contains {len(top_nodes)} relevant entities "
            f"connected by {len(relevant_edges)} relationships."
        )

        return {
            "entities": [n.to_dict() for _, n in top_nodes],
            "relationships": [e.to_dict() for e in relevant_edges],
            "summary": summary,
            "key_metrics": key_metrics,
        }

    def get_global_summary(self) -> dict[str, Any]:
        """
        Get deck-level summary from the full graph.
        Returns entities, key themes, metric clusters, narrative threads.
        """
        # Group nodes by type
        by_type: dict[str, list[GraphNode]] = {}
        for node in self._nodes.values():
            by_type.setdefault(node.entity_type.value, []).append(node)

        # Find most connected nodes (narrative hubs)
        connection_counts: dict[str, int] = {}
        for edge in self._edges:
            connection_counts[edge.source_id] = connection_counts.get(edge.source_id, 0) + 1
            connection_counts[edge.target_id] = connection_counts.get(edge.target_id, 0) + 1

        hub_nodes = sorted(
            self._nodes.values(),
            key=lambda n: connection_counts.get(n.id, 0),
            reverse=True,
        )[:10]

        # Extract metrics
        metrics: dict[str, Any] = {}
        for node in self._nodes.values():
            if node.entity_type == EntityType.METRIC and node.attributes:
                metrics[node.name] = node.attributes

        # Identify themes from entity clusters
        themes: list[str] = []
        if by_type.get(EntityType.MARKET.value):
            themes.append("market_opportunity")
        if by_type.get(EntityType.COMPANY.value, []):
            comp_count = len(by_type[EntityType.COMPANY.value])
            if comp_count > 2:
                themes.append("competitive_landscape")
        if by_type.get(EntityType.TECHNOLOGY.value):
            themes.append("technology_moat")
        if by_type.get(EntityType.METRIC.value):
            themes.append("quantitative_evidence")
        if by_type.get(EntityType.TREND.value):
            themes.append("market_trends")

        return {
            "total_entities": len(self._nodes),
            "total_edges": len(self._edges),
            "entities_by_type": {k: len(v) for k, v in by_type.items()},
            "hub_entities": [n.to_dict() for n in hub_nodes],
            "key_metrics": metrics,
            "themes": themes,
            "narrative_threads": [n.name for n in hub_nodes[:5]],
        }

    def find_contradictions(self) -> list[dict[str, Any]]:
        """Find entities with CONTRADICTS edges — flag for debate."""
        contradictions: list[dict[str, Any]] = []
        for edge in self._edges:
            if edge.relation == RelationType.CONTRADICTS:
                source = self._nodes.get(edge.source_id)
                target = self._nodes.get(edge.target_id)
                if source and target:
                    contradictions.append({
                        "entity_a": source.to_dict(),
                        "entity_b": target.to_dict(),
                        "edge": edge.to_dict(),
                        "fact_ids": edge.source_fact_ids,
                    })
        return contradictions

    def get_related_entities(
        self, entity_id: str, max_depth: int = 2
    ) -> list[GraphNode]:
        """BFS traversal to find related entities."""
        if entity_id not in self._nodes:
            return []

        visited: set[str] = {entity_id}
        queue: deque[tuple[str, int]] = deque([(entity_id, 0)])
        result: list[GraphNode] = []

        # Build adjacency
        adjacency: dict[str, set[str]] = {}
        for edge in self._edges:
            adjacency.setdefault(edge.source_id, set()).add(edge.target_id)
            if edge.bidirectional:
                adjacency.setdefault(edge.target_id, set()).add(edge.source_id)
            else:
                adjacency.setdefault(edge.target_id, set()).add(edge.source_id)

        while queue:
            current_id, depth = queue.popleft()
            if depth > 0:
                node = self._nodes.get(current_id)
                if node:
                    result.append(node)
            if depth < max_depth:
                for neighbor_id in adjacency.get(current_id, set()):
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        queue.append((neighbor_id, depth + 1))

        return result

    def merge_nodes(self, node_id_a: str, node_id_b: str) -> None:
        """Merge duplicate entities (same company/metric different names)."""
        node_a = self._nodes.get(node_id_a)
        node_b = self._nodes.get(node_id_b)
        if not node_a or not node_b:
            logger.warning(
                "merge_nodes_failed",
                reason="node not found",
                a=node_id_a,
                b=node_id_b,
            )
            return

        # Merge fact_packet_ids
        merged_facts = list(set(node_a.fact_packet_ids + node_b.fact_packet_ids))
        node_a.fact_packet_ids = merged_facts

        # Merge attributes
        node_a.attributes.update(node_b.attributes)

        # Merge slide_relevance (take max per slide)
        for slide, score in node_b.slide_relevance.items():
            node_a.slide_relevance[slide] = max(
                node_a.slide_relevance.get(slide, 0.0), score
            )

        # Merge confidence (take max)
        node_a.confidence = max(node_a.confidence, node_b.confidence)

        # Redirect edges from node_b to node_a
        for edge in self._edges:
            if edge.source_id == node_id_b:
                edge.source_id = node_id_a
            if edge.target_id == node_id_b:
                edge.target_id = node_id_a

        # Remove self-loops created by merge
        self._edges = [
            e for e in self._edges if e.source_id != e.target_id
        ]

        # Update name index
        normalized_b = self._normalize_entity_name(node_b.name)
        if normalized_b in self._name_to_id:
            self._name_to_id[normalized_b] = node_id_a

        # Update fact index
        for fact_id, nids in self._fact_index.items():
            self._fact_index[fact_id] = [
                node_id_a if nid == node_id_b else nid for nid in nids
            ]

        # Remove node_b
        del self._nodes[node_id_b]
        logger.info(
            "nodes_merged",
            kept=node_a.name,
            removed=node_b.name,
            merged_id=node_id_a,
        )

    # ── Serialization ─────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph for MongoDB storage."""
        return {
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "edges": [e.to_dict() for e in self._edges],
            "fact_index": {k: list(v) for k, v in self._fact_index.items()},
            "name_to_id": dict(self._name_to_id),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceGraph":
        """Deserialize from MongoDB."""
        graph = cls()
        for nid, ndata in data.get("nodes", {}).items():
            graph._nodes[nid] = GraphNode.from_dict(ndata)
        for edata in data.get("edges", []):
            graph._edges.append(GraphEdge.from_dict(edata))
        graph._fact_index = {
            k: list(v) for k, v in data.get("fact_index", {}).items()
        }
        graph._name_to_id = dict(data.get("name_to_id", {}))
        return graph

    # ── Internal helpers ──────────────────────────────────────

    def _extract_entities(self, text: str) -> list[tuple[str, EntityType]]:
        """
        Extract entity names and types from text using regex patterns.
        """
        entities: list[tuple[str, EntityType]] = []
        seen_normalized: set[str] = set()

        def _add(name: str, etype: EntityType) -> None:
            norm = self._normalize_entity_name(name)
            if norm and norm not in seen_normalized and len(norm) > 1:
                seen_normalized.add(norm)
                entities.append((name.strip(), etype))

        # Companies with suffixes (Inc, Corp, Ltd)
        for m in _COMPANY_PAT.finditer(text):
            _add(m.group(1), EntityType.COMPANY)

        # Standalone capitalized names (likely companies/products) —
        # only if 2+ words to reduce noise
        for m in _STANDALONE_COMPANY_PAT.finditer(text):
            name = m.group(1)
            words = name.split()
            if len(words) >= 2 and words[0] not in _STOP_WORDS:
                _add(name, EntityType.COMPANY)

        # Markets / Industries
        for m in _MARKET_PAT.finditer(text):
            market_name = m.group(1).strip()
            if len(market_name) > 3 and market_name.split()[0] not in _STOP_WORDS:
                _add(f"{market_name} market", EntityType.MARKET)

        # Money metrics ($X billion)
        for m in _MONEY_PAT.finditer(text):
            value = m.group(1)
            unit = m.group(2) or ""
            label = f"${value}{unit}"
            _add(label, EntityType.METRIC)

        # Percentage metrics
        for m in _PERCENT_PAT.finditer(text):
            pct_val = m.group(1)
            # Grab surrounding context for label
            start = max(0, m.start() - 30)
            context = text[start:m.end()].strip()
            _add(f"{pct_val}% ({context})", EntityType.METRIC)

        # User/customer counts
        for m in _USER_PAT.finditer(text):
            _add(m.group(0).strip(), EntityType.METRIC)

        # Revenue metrics
        for m in _REVENUE_PAT.finditer(text):
            _add(m.group(0).strip(), EntityType.METRIC)

        # Technology terms
        for m in _TECH_PAT.finditer(text):
            _add(m.group(1), EntityType.TECHNOLOGY)

        return entities

    def _normalize_entity_name(self, name: str) -> str:
        """Normalize entity name for deduplication."""
        normalized = name.strip().lower()
        # Remove common suffixes
        for suffix in ("inc.", "inc", "corp.", "corp", "ltd.", "ltd", "llc", "co."):
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()
        # Collapse whitespace
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _upsert_node(
        self, name: str, entity_type: EntityType, packet: FactPacket
    ) -> str:
        """Create or update a graph node for an entity."""
        normalized = self._normalize_entity_name(name)
        existing_id = self._name_to_id.get(normalized)

        if existing_id and existing_id in self._nodes:
            node = self._nodes[existing_id]
            if packet.id not in node.fact_packet_ids:
                node.fact_packet_ids.append(packet.id)
            # Update confidence as running max
            node.confidence = max(node.confidence, packet.confidence)
            # Merge slide relevance
            for slide, score in packet.slide_relevance.items():
                node.slide_relevance[slide] = max(
                    node.slide_relevance.get(slide, 0.0), score
                )
            # Update attributes from numeric facts
            if packet.numeric_value is not None:
                node.attributes[packet.numeric_unit or "value"] = packet.numeric_value
            return existing_id

        # Create new node
        node_id = f"ent_{uuid.uuid4().hex[:10]}"
        attrs: dict[str, Any] = {}
        if packet.numeric_value is not None:
            attrs[packet.numeric_unit or "value"] = packet.numeric_value

        node = GraphNode(
            id=node_id,
            name=name,
            entity_type=entity_type,
            attributes=attrs,
            fact_packet_ids=[packet.id],
            confidence=packet.confidence,
            slide_relevance=dict(packet.slide_relevance),
        )
        self._nodes[node_id] = node
        self._name_to_id[normalized] = node_id
        return node_id

    def _infer_relation(self, packet: FactPacket) -> RelationType:
        """Infer the most likely relation type from the FactPacket."""
        claim_lower = packet.claim.lower()

        # Check for contradiction signals
        if any(w in claim_lower for w in (
            "however", "but", "contrary", "despite", "contradicts",
            "disagrees", "unlike", "versus", "vs", "decline",
        )):
            return RelationType.CONTRADICTS

        # Check for comparison signals
        if any(w in claim_lower for w in (
            "compared to", "versus", "vs", "outperforms", "lags behind",
            "relative to", "in contrast",
        )):
            return RelationType.COMPARES_TO

        # Check for competitive signals
        if any(w in claim_lower for w in (
            "competitor", "competes", "rival", "alternative",
            "competing", "market share",
        )):
            return RelationType.COMPETES_WITH

        # Check for dependency
        if any(w in claim_lower for w in (
            "depends on", "relies on", "requires", "built on", "powered by",
        )):
            return RelationType.DEPENDS_ON

        # Check for acquisition
        if any(w in claim_lower for w in (
            "acquired", "acquisition", "merged", "bought",
        )):
            return RelationType.ACQUIRED_BY

        # Check for growth
        if any(w in claim_lower for w in (
            "grew", "growth", "increased", "risen", "expanded", "surged",
        )):
            return RelationType.GREW_FROM

        # Check for part-of
        if any(w in claim_lower for w in (
            "part of", "subsidiary", "division", "segment", "within",
        )):
            return RelationType.PART_OF

        # Default
        return RelationType.SUPPORTS

    def _add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: RelationType,
        fact_id: str,
        confidence: float,
    ) -> None:
        """Add or strengthen an edge between two nodes."""
        # Check for existing edge
        for edge in self._edges:
            if (
                (edge.source_id == source_id and edge.target_id == target_id)
                or (edge.source_id == target_id and edge.target_id == source_id)
            ):
                if fact_id not in edge.source_fact_ids:
                    edge.source_fact_ids.append(fact_id)
                # Strengthen the edge
                edge.strength = min(1.0, edge.strength + confidence * 0.1)
                return

        self._edges.append(
            GraphEdge(
                source_id=source_id,
                target_id=target_id,
                relation=relation,
                strength=confidence * 0.5,
                source_fact_ids=[fact_id],
                bidirectional=relation
                in (RelationType.COMPARES_TO, RelationType.COMPETES_WITH),
            )
        )

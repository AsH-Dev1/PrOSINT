"""Entity Graph Engine v4 - graph data model, SQLite persistence, relationship tracking."""
import json, sqlite3, uuid, os
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "prosint_graph.db"

ENTITY_TYPES = ["Person","Email","Phone","Domain","IP","Username","SocialProfile",
                "Breach","Location","Wallet","Company","Document","Image","Discord"]
RELATIONSHIPS = ["OWNS","LINKED_TO","MENTIONED_IN","BREACHED_IN","RESOLVES_TO",
                 "LOCATED_AT","WORKS_AT","SAME_AS","FOUND_ON","MATCHES","BELONGS_TO"]


def _get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_schema(conn)
    return conn


def _init_schema(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY, type TEXT NOT NULL, value TEXT NOT NULL,
            properties TEXT DEFAULT '{}', confidence REAL DEFAULT 1.0,
            created_at TEXT, updated_at TEXT, investigation_id TEXT
        );
        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY, source_id TEXT NOT NULL, target_id TEXT NOT NULL,
            relationship TEXT NOT NULL, confidence REAL DEFAULT 0.5,
            evidence TEXT DEFAULT '', created_at TEXT,
            FOREIGN KEY(source_id) REFERENCES entities(id),
            FOREIGN KEY(target_id) REFERENCES entities(id)
        );
        CREATE TABLE IF NOT EXISTS investigations (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, target TEXT NOT NULL,
            description TEXT DEFAULT '', status TEXT DEFAULT 'active',
            created_at TEXT, updated_at TEXT, entity_count INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
        CREATE INDEX IF NOT EXISTS idx_entities_value ON entities(value);
        CREATE INDEX IF NOT EXISTS idx_entities_inv ON entities(investigation_id);
        CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
        CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
    """)


class Entity:
    def __init__(self, entity_type: str, value: str, properties: dict = None,
                 confidence: float = 1.0, entity_id: str = None):
        self.id = entity_id or str(uuid.uuid4())[:8]
        self.type = entity_type
        self.value = value
        self.properties = properties or {}
        self.confidence = confidence
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

    def to_dict(self):
        return {"id": self.id, "type": self.type, "value": self.value,
                "properties": self.properties, "confidence": self.confidence,
                "created_at": self.created_at}

    @classmethod
    def from_row(cls, row):
        props = row["properties"] if isinstance(row, dict) else row[3]
        conf = row["confidence"] if isinstance(row, dict) else row[4]
        eid = row["id"] if isinstance(row, dict) else row[0]
        etype = row["type"] if isinstance(row, dict) else row[1]
        val = row["value"] if isinstance(row, dict) else row[2]
        try: props_dict = json.loads(str(props)) if isinstance(props, str) else (props if isinstance(props, dict) else {})
        except: props_dict = {}
        return cls(etype, val, props_dict, conf or 1.0, eid)

    @classmethod
    def canonical_value(cls, entity_type: str, value: str) -> str:
        v = value.lower().strip()
        if entity_type == "Email": return v
        if entity_type == "Domain": return v.replace("www.", "").rstrip("/")
        if entity_type == "Username": return v.lstrip("@")
        if entity_type == "Phone":
            import re; cleaned = re.sub(r'[\s\-\(\)]', '', v)
            return cleaned if cleaned.startswith('+') else '+' + cleaned
        return v


class GraphEngine:
    def __init__(self, investigation_id: str = None):
        self.investigation_id = investigation_id or str(uuid.uuid4())[:8]
        self.db = _get_db()

    def create_investigation(self, name: str, target: str, description: str = ""):
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO investigations(id,name,target,description,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            (self.investigation_id, name, target, description, now, now))
        self.db.commit()
        return self.investigation_id

    def add_entity(self, entity_type: str, value: str, properties: dict = None,
                   confidence: float = 1.0) -> str:
        value = Entity.canonical_value(entity_type, value)
        existing = self.db.execute(
            "SELECT * FROM entities WHERE type=? AND value=? AND investigation_id=?",
            (entity_type, value, self.investigation_id)).fetchone()
        if existing:
            e = Entity.from_row(existing)
            if properties:
                e.properties.update(properties)
                e.updated_at = datetime.now(timezone.utc).isoformat()
                self.db.execute("UPDATE entities SET properties=?, updated_at=? WHERE id=?",
                               (json.dumps(e.properties, default=str), e.updated_at, e.id))
                self.db.commit()
            return e.id

        e = Entity(entity_type, value, properties, confidence)
        self.db.execute(
            "INSERT INTO entities(id,type,value,properties,confidence,created_at,updated_at,investigation_id) VALUES(?,?,?,?,?,?,?,?)",
            (e.id, e.type, e.value, json.dumps(e.properties, default=str),
             e.confidence, e.created_at, e.updated_at, self.investigation_id))
        self.db.execute("UPDATE investigations SET entity_count=entity_count+1, updated_at=? WHERE id=?",
                       (e.updated_at, self.investigation_id))
        self.db.commit()
        return e.id

    def add_edge(self, source_id: str, target_id: str, relationship: str,
                 confidence: float = 0.5, evidence: str = ""):
        edge_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        existing = self.db.execute(
            "SELECT id FROM edges WHERE source_id=? AND target_id=? AND relationship=?",
            (source_id, target_id, relationship)).fetchone()
        if existing:
            self.db.execute("UPDATE edges SET confidence=MAX(confidence,?), evidence=?, created_at=? WHERE id=?",
                           (confidence, evidence, now, existing["id"]))
        else:
            self.db.execute(
                "INSERT INTO edges(id,source_id,target_id,relationship,confidence,evidence,created_at) VALUES(?,?,?,?,?,?,?)",
                (edge_id, source_id, target_id, relationship, confidence, evidence, now))
        self.db.commit()
        return edge_id

    def find_neighbors(self, entity_id: str = None, depth: int = 1) -> dict:
        """Find neighbors. If entity_id is None or an investigation ID, use the first entity.
           Accepts investigation_id as entity_id parameter - finds root entity automatically."""
        # Check if entity_id is actually an investigation ID (from cases list)
        if entity_id:
            inv = self.db.execute("SELECT id FROM investigations WHERE id=?", (entity_id,)).fetchone()
            if inv:
                root = self.db.execute(
                    "SELECT * FROM entities WHERE investigation_id=? ORDER BY created_at ASC LIMIT 1",
                    (entity_id,)).fetchone()
                if root:
                    entity_id = root["id"] if isinstance(root, dict) else root[0]
                else:
                    return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

        if not entity_id:
            return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

        visited = set()
        nodes = {}
        edges_list = []
        queue = [(entity_id, 0)]

        while queue:
            current_id, current_depth = queue.pop(0)
            if current_id in visited or current_depth > depth:
                continue
            visited.add(current_id)
            row = self.db.execute("SELECT * FROM entities WHERE id=?", (current_id,)).fetchone()
            if not row: continue
            nodes[current_id] = Entity.from_row(row).to_dict()

            if current_depth < depth:
                for direction in ["source_id", "target_id"]:
                    other = "target_id" if direction == "source_id" else "source_id"
                    for edge_row in self.db.execute(
                        f"SELECT * FROM edges WHERE {direction}=?", (current_id,)):
                        neighbor = edge_row[other]
                        edges_list.append({
                            "id": edge_row["id"], "source": edge_row["source_id"],
                            "target": edge_row["target_id"],
                            "relationship": edge_row["relationship"],
                            "confidence": edge_row["confidence"],
                        })
                        if neighbor not in visited:
                            queue.append((neighbor, current_depth + 1))

        return {"nodes": list(nodes.values()), "edges": edges_list,
                "total_nodes": len(nodes), "total_edges": len(edges_list)}

    def search_entities(self, query: str = "", entity_type: str = "") -> list[dict]:
        sql = "SELECT * FROM entities WHERE investigation_id=?"
        params = [self.investigation_id]
        if entity_type:
            sql += " AND type=?"
            params.append(entity_type)
        sql += " ORDER BY created_at DESC LIMIT 100"
        rows = self.db.execute(sql, params).fetchall()
        results = [Entity.from_row(r).to_dict() for r in rows]
        if query:
            q = query.lower()
            results = [r for r in results if q in r["value"].lower() or
                      q in str(r.get("properties", {})).lower()]
        return results

    def list_investigations(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM investigations ORDER BY updated_at DESC LIMIT 50").fetchall()
        return [{"id": r[0], "name": r[1], "target": r[2], "description": r[3],
                 "status": r[4], "created_at": r[5], "updated_at": r[6],
                 "entity_count": r[7]} for r in rows]

    def close(self):
        self.db.close()

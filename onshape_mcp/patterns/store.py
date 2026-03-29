"""Assembly pattern library — stores and retrieves successful assembly patterns."""

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


DEFAULT_DB_PATH = os.path.expanduser("~/.onshape-mcp/patterns.db")


@dataclass
class PatternPart:
    """A part role within an assembly pattern."""

    role: str  # e.g., "back_panel", "drawer_front"
    width: float  # inches
    depth: float  # inches
    height: float  # inches
    ps_layout: Optional[Dict[str, Any]] = None  # PS offset info


@dataclass
class PatternMate:
    """A mate connection within an assembly pattern."""

    role_first: str
    role_second: str
    mate_type: str  # "FASTENED", "SLIDER", "REVOLUTE", "CYLINDRICAL"
    first_face_label: str  # e.g., "+Y", "-X"
    second_face_label: str
    direction: str  # "same" or "anti"
    first_offsets: Optional[Dict[str, float]] = None
    second_offsets: Optional[Dict[str, float]] = None
    notes: str = ""


@dataclass
class PatternPosition:
    """A part position within an assembly pattern (relative to reference part)."""

    role: str
    instance_number: int  # 1-based (e.g., drawer 1, drawer 2)
    relative_x: float  # inches, relative to reference part
    relative_y: float
    relative_z: float
    world_bounds: Optional[Dict[str, float]] = None  # low_x, high_x, etc.


@dataclass
class AssemblyPattern:
    """A complete assembly pattern that can be stored and retrieved."""

    name: str
    description: str
    part_count: int
    mate_count: int
    parts: List[PatternPart] = field(default_factory=list)
    mates: List[PatternMate] = field(default_factory=list)
    positions: List[PatternPosition] = field(default_factory=list)
    created_at: str = ""
    pattern_id: Optional[int] = None


class PatternStore:
    """SQLite-backed assembly pattern library with FTS5 search."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS assembly_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    part_count INTEGER NOT NULL DEFAULT 0,
                    mate_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS pattern_parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id INTEGER NOT NULL
                        REFERENCES assembly_patterns(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    width REAL NOT NULL,
                    depth REAL NOT NULL,
                    height REAL NOT NULL,
                    ps_layout_json TEXT
                );

                CREATE TABLE IF NOT EXISTS pattern_mates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id INTEGER NOT NULL
                        REFERENCES assembly_patterns(id) ON DELETE CASCADE,
                    role_first TEXT NOT NULL,
                    role_second TEXT NOT NULL,
                    mate_type TEXT NOT NULL DEFAULT 'FASTENED',
                    first_face_label TEXT NOT NULL,
                    second_face_label TEXT NOT NULL,
                    direction TEXT NOT NULL DEFAULT 'same',
                    first_offsets_json TEXT,
                    second_offsets_json TEXT,
                    notes TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS pattern_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id INTEGER NOT NULL
                        REFERENCES assembly_patterns(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    instance_number INTEGER NOT NULL DEFAULT 1,
                    relative_x REAL NOT NULL DEFAULT 0,
                    relative_y REAL NOT NULL DEFAULT 0,
                    relative_z REAL NOT NULL DEFAULT 0,
                    world_bounds_json TEXT
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS patterns_fts USING fts5(
                    name, description,
                    content='assembly_patterns', content_rowid='id'
                );

                -- Triggers to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS patterns_ai
                    AFTER INSERT ON assembly_patterns
                BEGIN
                    INSERT INTO patterns_fts(rowid, name, description)
                        VALUES (new.id, new.name, new.description);
                END;

                CREATE TRIGGER IF NOT EXISTS patterns_ad
                    AFTER DELETE ON assembly_patterns
                BEGIN
                    INSERT INTO patterns_fts(patterns_fts, rowid, name, description)
                        VALUES ('delete', old.id, old.name, old.description);
                END;

                CREATE TRIGGER IF NOT EXISTS patterns_au
                    AFTER UPDATE ON assembly_patterns
                BEGIN
                    INSERT INTO patterns_fts(patterns_fts, rowid, name, description)
                        VALUES ('delete', old.id, old.name, old.description);
                    INSERT INTO patterns_fts(rowid, name, description)
                        VALUES (new.id, new.name, new.description);
                END;
            """)
            conn.commit()
        finally:
            conn.close()

    def store_pattern(self, pattern: AssemblyPattern) -> int:
        """Store a complete assembly pattern. Returns the new pattern ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO assembly_patterns "
                "(name, description, part_count, mate_count) VALUES (?, ?, ?, ?)",
                (
                    pattern.name,
                    pattern.description,
                    pattern.part_count,
                    pattern.mate_count,
                ),
            )
            pattern_id = cursor.lastrowid

            for part in pattern.parts:
                conn.execute(
                    "INSERT INTO pattern_parts "
                    "(pattern_id, role, width, depth, height, ps_layout_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        pattern_id,
                        part.role,
                        part.width,
                        part.depth,
                        part.height,
                        json.dumps(part.ps_layout) if part.ps_layout else None,
                    ),
                )

            for mate in pattern.mates:
                conn.execute(
                    "INSERT INTO pattern_mates "
                    "(pattern_id, role_first, role_second, mate_type, "
                    "first_face_label, second_face_label, direction, "
                    "first_offsets_json, second_offsets_json, notes) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        pattern_id,
                        mate.role_first,
                        mate.role_second,
                        mate.mate_type,
                        mate.first_face_label,
                        mate.second_face_label,
                        mate.direction,
                        json.dumps(mate.first_offsets) if mate.first_offsets else None,
                        json.dumps(mate.second_offsets)
                        if mate.second_offsets
                        else None,
                        mate.notes,
                    ),
                )

            for pos in pattern.positions:
                conn.execute(
                    "INSERT INTO pattern_positions "
                    "(pattern_id, role, instance_number, "
                    "relative_x, relative_y, relative_z, world_bounds_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        pattern_id,
                        pos.role,
                        pos.instance_number,
                        pos.relative_x,
                        pos.relative_y,
                        pos.relative_z,
                        json.dumps(pos.world_bounds) if pos.world_bounds else None,
                    ),
                )

            conn.commit()
            logger.info(
                f"Stored pattern '{pattern.name}' "
                f"(id={pattern_id}, {pattern.part_count} parts, "
                f"{pattern.mate_count} mates)"
            )
            return pattern_id
        finally:
            conn.close()

    def search_patterns(
        self, query: str, limit: int = 10
    ) -> List[AssemblyPattern]:
        """Search patterns by name/description using FTS5."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT ap.* FROM assembly_patterns ap
                   JOIN patterns_fts ON ap.id = patterns_fts.rowid
                   WHERE patterns_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit),
            ).fetchall()
            return [self._row_to_pattern(conn, row) for row in rows]
        finally:
            conn.close()

    def get_pattern(self, pattern_id: int) -> Optional[AssemblyPattern]:
        """Retrieve a single pattern by ID with all details."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM assembly_patterns WHERE id = ?", (pattern_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_pattern(conn, row)
        finally:
            conn.close()

    def list_patterns(self, limit: int = 50) -> List[AssemblyPattern]:
        """List all patterns (summary only, no child details)."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM assembly_patterns ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                self._row_to_pattern(conn, row, include_details=False)
                for row in rows
            ]
        finally:
            conn.close()

    def delete_pattern(self, pattern_id: int) -> bool:
        """Delete a pattern and all its child records. Returns True if deleted."""
        conn = self._get_conn()
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.execute(
                "DELETE FROM assembly_patterns WHERE id = ?", (pattern_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def _row_to_pattern(
        self,
        conn: sqlite3.Connection,
        row: sqlite3.Row,
        include_details: bool = True,
    ) -> AssemblyPattern:
        """Convert a database row into an AssemblyPattern dataclass."""
        pattern = AssemblyPattern(
            pattern_id=row["id"],
            name=row["name"],
            description=row["description"],
            part_count=row["part_count"],
            mate_count=row["mate_count"],
            created_at=row["created_at"],
        )

        if include_details:
            # Load parts
            part_rows = conn.execute(
                "SELECT * FROM pattern_parts WHERE pattern_id = ?",
                (row["id"],),
            ).fetchall()
            pattern.parts = [
                PatternPart(
                    role=pr["role"],
                    width=pr["width"],
                    depth=pr["depth"],
                    height=pr["height"],
                    ps_layout=json.loads(pr["ps_layout_json"])
                    if pr["ps_layout_json"]
                    else None,
                )
                for pr in part_rows
            ]

            # Load mates
            mate_rows = conn.execute(
                "SELECT * FROM pattern_mates WHERE pattern_id = ?",
                (row["id"],),
            ).fetchall()
            pattern.mates = [
                PatternMate(
                    role_first=mr["role_first"],
                    role_second=mr["role_second"],
                    mate_type=mr["mate_type"],
                    first_face_label=mr["first_face_label"],
                    second_face_label=mr["second_face_label"],
                    direction=mr["direction"],
                    first_offsets=json.loads(mr["first_offsets_json"])
                    if mr["first_offsets_json"]
                    else None,
                    second_offsets=json.loads(mr["second_offsets_json"])
                    if mr["second_offsets_json"]
                    else None,
                    notes=mr["notes"],
                )
                for mr in mate_rows
            ]

            # Load positions
            pos_rows = conn.execute(
                "SELECT * FROM pattern_positions WHERE pattern_id = ?",
                (row["id"],),
            ).fetchall()
            pattern.positions = [
                PatternPosition(
                    role=pr["role"],
                    instance_number=pr["instance_number"],
                    relative_x=pr["relative_x"],
                    relative_y=pr["relative_y"],
                    relative_z=pr["relative_z"],
                    world_bounds=json.loads(pr["world_bounds_json"])
                    if pr["world_bounds_json"]
                    else None,
                )
                for pr in pos_rows
            ]

        return pattern

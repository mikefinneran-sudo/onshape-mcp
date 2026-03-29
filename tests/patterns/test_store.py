"""Unit tests for the assembly pattern store (SQLite-backed)."""

import os
import sqlite3

import pytest

from onshape_mcp.patterns.store import (
    AssemblyPattern,
    PatternMate,
    PatternPart,
    PatternPosition,
    PatternStore,
)


@pytest.fixture
def store(tmp_path):
    """Provide a PatternStore backed by a temporary database."""
    db_path = str(tmp_path / "test_patterns.db")
    return PatternStore(db_path=db_path)


@pytest.fixture
def sample_pattern():
    """Provide a fully populated AssemblyPattern for testing."""
    return AssemblyPattern(
        name="3-Drawer Dresser",
        description="Three-drawer dresser with back panel and side panels",
        part_count=7,
        mate_count=12,
        parts=[
            PatternPart(
                role="back_panel", width=24.0, depth=0.75, height=30.0
            ),
            PatternPart(
                role="side_left",
                width=0.75,
                depth=18.0,
                height=30.0,
                ps_layout={"offset_x": 2.0},
            ),
        ],
        mates=[
            PatternMate(
                role_first="back_panel",
                role_second="side_left",
                mate_type="FASTENED",
                first_face_label="-X",
                second_face_label="+Y",
                direction="same",
                first_offsets={"offsetZ": 0.375},
                notes="Left side flush with back panel edge",
            ),
        ],
        positions=[
            PatternPosition(
                role="drawer",
                instance_number=1,
                relative_x=0.75,
                relative_y=0.0,
                relative_z=2.0,
                world_bounds={"low_x": 0.75, "high_x": 23.25},
            ),
            PatternPosition(
                role="drawer",
                instance_number=2,
                relative_x=0.75,
                relative_y=0.0,
                relative_z=12.0,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# PatternStore.__init__
# ---------------------------------------------------------------------------


class TestPatternStoreInit:
    """Test database initialization."""

    def test_creates_db_file(self, tmp_path):
        db_path = str(tmp_path / "subdir" / "patterns.db")
        PatternStore(db_path=db_path)
        assert os.path.exists(db_path)

    def test_creates_required_tables(self, store):
        conn = sqlite3.connect(store.db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()
        table_names = {t[0] for t in tables}
        assert "assembly_patterns" in table_names
        assert "pattern_parts" in table_names
        assert "pattern_mates" in table_names
        assert "pattern_positions" in table_names

    def test_creates_fts_table(self, store):
        conn = sqlite3.connect(store.db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()
        table_names = {t[0] for t in tables}
        assert "patterns_fts" in table_names

    def test_idempotent_init(self, tmp_path):
        """Calling __init__ twice on the same DB doesn't error."""
        db_path = str(tmp_path / "patterns.db")
        PatternStore(db_path=db_path)
        PatternStore(db_path=db_path)  # Should not raise


# ---------------------------------------------------------------------------
# store_pattern
# ---------------------------------------------------------------------------


class TestStorePattern:
    """Test storing assembly patterns."""

    def test_returns_integer_id(self, store, sample_pattern):
        pattern_id = store.store_pattern(sample_pattern)
        assert isinstance(pattern_id, int)
        assert pattern_id >= 1

    def test_stores_parts(self, store, sample_pattern):
        pattern_id = store.store_pattern(sample_pattern)
        conn = sqlite3.connect(store.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM pattern_parts WHERE pattern_id = ?", (pattern_id,)
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        roles = {r["role"] for r in rows}
        assert roles == {"back_panel", "side_left"}

    def test_stores_mates(self, store, sample_pattern):
        pattern_id = store.store_pattern(sample_pattern)
        conn = sqlite3.connect(store.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM pattern_mates WHERE pattern_id = ?", (pattern_id,)
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0]["mate_type"] == "FASTENED"
        assert rows[0]["notes"] == "Left side flush with back panel edge"

    def test_stores_positions(self, store, sample_pattern):
        pattern_id = store.store_pattern(sample_pattern)
        conn = sqlite3.connect(store.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM pattern_positions WHERE pattern_id = ?",
            (pattern_id,),
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        instances = sorted([r["instance_number"] for r in rows])
        assert instances == [1, 2]

    def test_sequential_ids(self, store):
        p1 = AssemblyPattern(name="First", description="", part_count=1, mate_count=0)
        p2 = AssemblyPattern(name="Second", description="", part_count=1, mate_count=0)
        id1 = store.store_pattern(p1)
        id2 = store.store_pattern(p2)
        assert id2 == id1 + 1


# ---------------------------------------------------------------------------
# get_pattern
# ---------------------------------------------------------------------------


class TestGetPattern:
    """Test retrieving a single pattern by ID."""

    def test_retrieves_full_pattern(self, store, sample_pattern):
        pattern_id = store.store_pattern(sample_pattern)
        retrieved = store.get_pattern(pattern_id)

        assert retrieved is not None
        assert retrieved.pattern_id == pattern_id
        assert retrieved.name == "3-Drawer Dresser"
        assert retrieved.description == "Three-drawer dresser with back panel and side panels"
        assert retrieved.part_count == 7
        assert retrieved.mate_count == 12

    def test_retrieves_parts_with_details(self, store, sample_pattern):
        pattern_id = store.store_pattern(sample_pattern)
        retrieved = store.get_pattern(pattern_id)

        assert len(retrieved.parts) == 2
        back_panel = next(p for p in retrieved.parts if p.role == "back_panel")
        assert back_panel.width == 24.0
        assert back_panel.depth == 0.75
        assert back_panel.height == 30.0
        assert back_panel.ps_layout is None

        side_left = next(p for p in retrieved.parts if p.role == "side_left")
        assert side_left.ps_layout == {"offset_x": 2.0}

    def test_retrieves_mates_with_offsets(self, store, sample_pattern):
        pattern_id = store.store_pattern(sample_pattern)
        retrieved = store.get_pattern(pattern_id)

        assert len(retrieved.mates) == 1
        mate = retrieved.mates[0]
        assert mate.role_first == "back_panel"
        assert mate.role_second == "side_left"
        assert mate.mate_type == "FASTENED"
        assert mate.direction == "same"
        assert mate.first_offsets == {"offsetZ": 0.375}
        assert mate.second_offsets is None

    def test_retrieves_positions_with_world_bounds(self, store, sample_pattern):
        pattern_id = store.store_pattern(sample_pattern)
        retrieved = store.get_pattern(pattern_id)

        assert len(retrieved.positions) == 2
        pos1 = next(p for p in retrieved.positions if p.instance_number == 1)
        assert pos1.relative_z == 2.0
        assert pos1.world_bounds == {"low_x": 0.75, "high_x": 23.25}

        pos2 = next(p for p in retrieved.positions if p.instance_number == 2)
        assert pos2.world_bounds is None

    def test_nonexistent_id_returns_none(self, store):
        result = store.get_pattern(9999)
        assert result is None

    def test_has_created_at_timestamp(self, store, sample_pattern):
        pattern_id = store.store_pattern(sample_pattern)
        retrieved = store.get_pattern(pattern_id)
        assert retrieved.created_at != ""
        assert retrieved.created_at is not None


# ---------------------------------------------------------------------------
# search_patterns
# ---------------------------------------------------------------------------


class TestSearchPatterns:
    """Test FTS5 search across patterns."""

    def test_finds_by_name_keyword(self, store):
        store.store_pattern(AssemblyPattern(
            name="Bookshelf Assembly",
            description="Simple 5-shelf bookshelf",
            part_count=7, mate_count=6,
        ))
        store.store_pattern(AssemblyPattern(
            name="Kitchen Cabinet",
            description="Upper cabinet with door",
            part_count=5, mate_count=8,
        ))

        results = store.search_patterns("Bookshelf")
        assert len(results) == 1
        assert results[0].name == "Bookshelf Assembly"

    def test_finds_by_description_keyword(self, store):
        store.store_pattern(AssemblyPattern(
            name="Storage Unit",
            description="6-drawer dresser with dovetail joints",
            part_count=10, mate_count=15,
        ))
        results = store.search_patterns("dovetail")
        assert len(results) == 1
        assert results[0].name == "Storage Unit"

    def test_no_results_returns_empty(self, store):
        store.store_pattern(AssemblyPattern(
            name="Desk", description="Simple desk", part_count=4, mate_count=3,
        ))
        results = store.search_patterns("helicopter")
        assert results == []

    def test_respects_limit(self, store):
        for i in range(5):
            store.store_pattern(AssemblyPattern(
                name=f"Shelf variant {i}",
                description="A shelf design",
                part_count=3, mate_count=2,
            ))
        results = store.search_patterns("shelf", limit=2)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# list_patterns
# ---------------------------------------------------------------------------


class TestListPatterns:
    """Test listing all patterns."""

    def test_returns_patterns_sorted_by_date_desc(self, store):
        """Patterns with distinct timestamps sort newest-first."""
        # Insert with explicit timestamps to avoid sub-second collisions
        conn = sqlite3.connect(store.db_path)
        conn.execute(
            "INSERT INTO assembly_patterns (name, description, part_count, mate_count, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("Old", "", 1, 0, "2026-01-01 00:00:00"),
        )
        conn.execute(
            "INSERT INTO assembly_patterns (name, description, part_count, mate_count, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("Middle", "", 1, 0, "2026-02-01 00:00:00"),
        )
        conn.execute(
            "INSERT INTO assembly_patterns (name, description, part_count, mate_count, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("Recent", "", 1, 0, "2026-03-01 00:00:00"),
        )
        conn.commit()
        conn.close()

        results = store.list_patterns()
        assert len(results) == 3
        assert results[0].name == "Recent"
        assert results[1].name == "Middle"
        assert results[2].name == "Old"

    def test_respects_limit(self, store):
        for i in range(5):
            store.store_pattern(AssemblyPattern(
                name=f"Pattern {i}", description="", part_count=1, mate_count=0,
            ))
        results = store.list_patterns(limit=3)
        assert len(results) == 3

    def test_empty_store_returns_empty(self, store):
        results = store.list_patterns()
        assert results == []

    def test_list_does_not_include_child_details(self, store, sample_pattern):
        """list_patterns calls _row_to_pattern with include_details=False."""
        store.store_pattern(sample_pattern)
        results = store.list_patterns()
        assert len(results) == 1
        # include_details=False means parts/mates/positions are empty
        assert results[0].parts == []
        assert results[0].mates == []
        assert results[0].positions == []


# ---------------------------------------------------------------------------
# delete_pattern
# ---------------------------------------------------------------------------


class TestDeletePattern:
    """Test pattern deletion with cascade."""

    def test_deletes_pattern(self, store, sample_pattern):
        pattern_id = store.store_pattern(sample_pattern)
        deleted = store.delete_pattern(pattern_id)
        assert deleted is True
        assert store.get_pattern(pattern_id) is None

    def test_cascades_to_child_tables(self, store, sample_pattern):
        pattern_id = store.store_pattern(sample_pattern)
        store.delete_pattern(pattern_id)

        conn = sqlite3.connect(store.db_path)
        parts = conn.execute(
            "SELECT COUNT(*) FROM pattern_parts WHERE pattern_id = ?",
            (pattern_id,),
        ).fetchone()[0]
        mates = conn.execute(
            "SELECT COUNT(*) FROM pattern_mates WHERE pattern_id = ?",
            (pattern_id,),
        ).fetchone()[0]
        positions = conn.execute(
            "SELECT COUNT(*) FROM pattern_positions WHERE pattern_id = ?",
            (pattern_id,),
        ).fetchone()[0]
        conn.close()

        assert parts == 0
        assert mates == 0
        assert positions == 0

    def test_nonexistent_id_returns_false(self, store):
        deleted = store.delete_pattern(9999)
        assert deleted is False

    def test_other_patterns_unaffected(self, store):
        p1 = AssemblyPattern(
            name="Keep Me", description="", part_count=1, mate_count=0,
        )
        p2 = AssemblyPattern(
            name="Delete Me", description="", part_count=1, mate_count=0,
        )
        id1 = store.store_pattern(p1)
        id2 = store.store_pattern(p2)

        store.delete_pattern(id2)

        assert store.get_pattern(id1) is not None
        assert store.get_pattern(id2) is None

"""Unit tests for assembly operation guards."""

import pytest

from onshape_mcp.analysis.guards import (
    GuardResult,
    check_ps_part_count,
    extract_occurrence_fixed_state,
    get_face_normal_from_body_details,
    validate_face_pair,
    validate_part_face_mapping,
    verify_positions_stable,
)


# ---------------------------------------------------------------------------
# GuardResult
# ---------------------------------------------------------------------------


class TestGuardResult:
    """Test the GuardResult dataclass and its helpers."""

    def test_format_warnings_empty(self):
        result = GuardResult(passed=True, warnings=[])
        assert result.format_warnings() == ""

    def test_format_warnings_single(self):
        result = GuardResult(passed=False, warnings=["Something went wrong"])
        formatted = result.format_warnings()
        assert "[GUARD WARNING] Something went wrong" in formatted
        assert formatted.endswith("\n\n")

    def test_format_warnings_multiple(self):
        result = GuardResult(
            passed=False, warnings=["First warning", "Second warning"]
        )
        formatted = result.format_warnings()
        lines = formatted.strip().split("\n")
        assert len(lines) == 2
        assert "[GUARD WARNING] First warning" == lines[0]
        assert "[GUARD WARNING] Second warning" == lines[1]


# ---------------------------------------------------------------------------
# extract_occurrence_fixed_state
# ---------------------------------------------------------------------------


class TestExtractOccurrenceFixedState:
    """Test extraction of instance fixed/grounded state from assembly data."""

    def test_fixed_and_unfixed_occurrences(self):
        assembly_data = {
            "rootAssembly": {
                "occurrences": [
                    {"path": ["inst_back_panel"], "fixed": True},
                    {"path": ["inst_side_left"], "fixed": False},
                    {"path": ["inst_door"], "fixed": True},
                ]
            }
        }
        states = extract_occurrence_fixed_state(assembly_data)
        assert states == {
            "inst_back_panel": True,
            "inst_side_left": False,
            "inst_door": True,
        }

    def test_skips_deep_paths(self):
        """Only top-level instances (path length 1) are tracked."""
        assembly_data = {
            "rootAssembly": {
                "occurrences": [
                    {"path": ["inst_a"], "fixed": True},
                    {"path": ["inst_a", "inst_nested"], "fixed": False},
                ]
            }
        }
        states = extract_occurrence_fixed_state(assembly_data)
        assert states == {"inst_a": True}

    def test_missing_fixed_defaults_to_false(self):
        assembly_data = {
            "rootAssembly": {
                "occurrences": [
                    {"path": ["inst_no_fixed_key"]},
                ]
            }
        }
        states = extract_occurrence_fixed_state(assembly_data)
        assert states["inst_no_fixed_key"] is False

    def test_empty_occurrences(self):
        assembly_data = {"rootAssembly": {"occurrences": []}}
        states = extract_occurrence_fixed_state(assembly_data)
        assert states == {}

    def test_missing_root_assembly(self):
        assembly_data = {}
        states = extract_occurrence_fixed_state(assembly_data)
        assert states == {}


# ---------------------------------------------------------------------------
# validate_face_pair
# ---------------------------------------------------------------------------


class TestValidateFacePair:
    """Test face-pair direction validation."""

    def test_same_direction_passes_no_warnings(self):
        # Two faces pointing the same way (dot product ~1.0)
        result = validate_face_pair(
            face1_normal=(0.0, 0.0, 1.0),
            face2_normal=(0.0, 0.0, 1.0),
        )
        assert result.passed is True
        assert result.warnings == []

    def test_anti_parallel_one_grounded_passes_with_warning(self):
        # Opposing normals, but one instance is grounded
        result = validate_face_pair(
            face1_normal=(0.0, 0.0, 1.0),
            face2_normal=(0.0, 0.0, -1.0),
            instance1_fixed=True,
            instance2_fixed=False,
        )
        assert result.passed is True
        assert len(result.warnings) == 1
        assert "Anti-parallel" in result.warnings[0]
        assert "grounded" in result.warnings[0]

    def test_anti_parallel_neither_grounded_fails(self):
        result = validate_face_pair(
            face1_normal=(0.0, 0.0, 1.0),
            face2_normal=(0.0, 0.0, -1.0),
            instance1_fixed=False,
            instance2_fixed=False,
        )
        assert result.passed is False
        assert len(result.warnings) == 1
        assert "WILL cause a 180-degree flip" in result.warnings[0]

    def test_anti_parallel_both_grounded_passes_with_warning(self):
        result = validate_face_pair(
            face1_normal=(1.0, 0.0, 0.0),
            face2_normal=(-1.0, 0.0, 0.0),
            instance1_fixed=True,
            instance2_fixed=True,
        )
        assert result.passed is True
        assert len(result.warnings) == 1

    def test_perpendicular_faces_pass(self):
        # Dot product ~0, not anti-parallel
        result = validate_face_pair(
            face1_normal=(1.0, 0.0, 0.0),
            face2_normal=(0.0, 1.0, 0.0),
        )
        assert result.passed is True
        assert result.warnings == []

    def test_nearly_anti_parallel_triggers(self):
        # Dot product just below -0.9
        result = validate_face_pair(
            face1_normal=(0.0, 0.0, 1.0),
            face2_normal=(0.0, 0.1, -0.995),
        )
        dot = 0.0 * 0.0 + 0.0 * 0.1 + 1.0 * -0.995
        assert dot < -0.9  # Confirm test data is valid
        assert result.passed is False
        assert len(result.warnings) == 1


# ---------------------------------------------------------------------------
# validate_part_face_mapping
# ---------------------------------------------------------------------------


class TestValidatePartFaceMapping:
    """Test that face IDs are validated against the correct part."""

    def _make_assembly(self, instances):
        return {"rootAssembly": {"instances": instances}}

    def test_face_found_on_correct_part(self):
        assembly = self._make_assembly([
            {"id": "inst_1", "name": "Back Panel", "partId": "part_abc"},
        ])
        bodies = [
            {
                "id": "part_abc",
                "faces": [
                    {"id": "face_top"},
                    {"id": "face_bottom"},
                ],
            }
        ]
        result = validate_part_face_mapping(assembly, "inst_1", "face_top", bodies)
        assert result.passed is True
        assert result.warnings == []

    def test_face_not_found_on_part(self):
        assembly = self._make_assembly([
            {"id": "inst_1", "name": "Back Panel", "partId": "part_abc"},
        ])
        bodies = [
            {
                "id": "part_abc",
                "faces": [{"id": "face_top"}, {"id": "face_bottom"}],
            }
        ]
        result = validate_part_face_mapping(assembly, "inst_1", "face_wrong", bodies)
        assert result.passed is False
        assert len(result.warnings) == 1
        assert "NOT FOUND" in result.warnings[0]
        assert "face_top" in result.warnings[0]  # Available faces listed

    def test_instance_with_empty_part_id(self):
        assembly = self._make_assembly([
            {"id": "inst_phantom", "name": "Ghost", "partId": ""},
        ])
        result = validate_part_face_mapping(assembly, "inst_phantom", "face_x", [])
        assert result.passed is False
        assert "no Part ID" in result.warnings[0]

    def test_instance_not_found_in_assembly(self):
        assembly = self._make_assembly([])
        result = validate_part_face_mapping(assembly, "missing_inst", "face_x", [])
        assert result.passed is False
        assert "no Part ID" in result.warnings[0]

    def test_part_id_not_found_in_body_details(self):
        assembly = self._make_assembly([
            {"id": "inst_1", "name": "Shelf", "partId": "part_xyz"},
        ])
        bodies = [{"id": "part_other", "faces": []}]
        result = validate_part_face_mapping(assembly, "inst_1", "face_a", bodies)
        assert result.passed is False
        assert "not found in body details" in result.warnings[0]


# ---------------------------------------------------------------------------
# verify_positions_stable
# ---------------------------------------------------------------------------


class TestVerifyPositionsStable:
    """Test position drift detection after mate creation."""

    def test_no_drift_passes(self):
        before = {
            "inst_a": (0.0, 0.0, 0.0),
            "inst_b": (5.0, 0.0, 0.0),
            "inst_c": (10.0, 0.0, 0.0),
        }
        after = {
            "inst_a": (0.0, 0.0, 0.0),
            "inst_b": (5.0, 0.0, 0.0),
            "inst_c": (10.0, 0.0, 0.0),
        }
        result = verify_positions_stable(before, after, ("inst_a", "inst_b"))
        assert result.passed is True
        assert result.warnings == []

    def test_drift_on_uninvolved_instance_warns(self):
        before = {
            "inst_a": (0.0, 0.0, 0.0),
            "inst_b": (5.0, 0.0, 0.0),
            "inst_c": (10.0, 0.0, 0.0),
        }
        after = {
            "inst_a": (0.0, 0.0, 0.0),
            "inst_b": (5.0, 0.0, 0.0),
            "inst_c": (10.5, 0.0, 0.0),  # drifted 0.5"
        }
        result = verify_positions_stable(before, after, ("inst_a", "inst_b"))
        assert result.passed is False
        assert len(result.warnings) == 1
        assert "inst_c" in result.warnings[0]
        assert "drifted" in result.warnings[0]

    def test_mated_instances_are_skipped(self):
        before = {"inst_a": (0.0, 0.0, 0.0), "inst_b": (5.0, 0.0, 0.0)}
        after = {"inst_a": (1.0, 2.0, 3.0), "inst_b": (6.0, 2.0, 3.0)}
        result = verify_positions_stable(before, after, ("inst_a", "inst_b"))
        assert result.passed is True
        assert result.warnings == []

    def test_within_tolerance_passes(self):
        before = {"inst_c": (10.0, 0.0, 0.0)}
        after = {"inst_c": (10.05, 0.0, 0.0)}  # 0.05" drift, under 0.1 default
        result = verify_positions_stable(before, after, ("inst_a", "inst_b"))
        assert result.passed is True

    def test_custom_tolerance(self):
        before = {"inst_c": (10.0, 0.0, 0.0)}
        after = {"inst_c": (10.05, 0.0, 0.0)}
        # With a tighter tolerance, this should warn
        result = verify_positions_stable(
            before, after, ("inst_a", "inst_b"), tolerance_inches=0.01
        )
        assert result.passed is False
        assert len(result.warnings) == 1

    def test_instance_missing_from_after_is_ignored(self):
        before = {"inst_a": (0.0, 0.0, 0.0), "inst_c": (10.0, 0.0, 0.0)}
        after = {"inst_a": (0.0, 0.0, 0.0)}  # inst_c gone from after
        result = verify_positions_stable(before, after, ("inst_a", "inst_b"))
        assert result.passed is True


# ---------------------------------------------------------------------------
# check_ps_part_count
# ---------------------------------------------------------------------------


class TestCheckPSPartCount:
    """Test Part Studio part count guard."""

    def test_matching_count_passes(self):
        result = check_ps_part_count(expected_count=5, actual_count=5)
        assert result.passed is True
        assert result.warnings == []

    def test_more_parts_than_expected_passes(self):
        result = check_ps_part_count(expected_count=5, actual_count=7)
        assert result.passed is True

    def test_fewer_parts_fails_with_warning(self):
        result = check_ps_part_count(
            expected_count=5,
            actual_count=3,
            part_studio_name="Cabinet Parts",
        )
        assert result.passed is False
        assert len(result.warnings) == 1
        assert "Cabinet Parts" in result.warnings[0]
        assert "3 parts" in result.warnings[0]
        assert "expected 5" in result.warnings[0]
        assert "merged" in result.warnings[0]


# ---------------------------------------------------------------------------
# get_face_normal_from_body_details
# ---------------------------------------------------------------------------


class TestGetFaceNormalFromBodyDetails:
    """Test face normal vector extraction from body details."""

    def _make_bodies(self, part_id, faces):
        return [{"id": part_id, "faces": faces}]

    def test_face_found_returns_normal_tuple(self):
        bodies = self._make_bodies("part_1", [
            {
                "id": "face_top",
                "surface": {
                    "type": "plane",
                    "normal": {"x": 0.0, "y": 1.0, "z": 0.0},
                },
            },
        ])
        normal = get_face_normal_from_body_details(bodies, "part_1", "face_top")
        assert normal == (0.0, 1.0, 0.0)

    def test_face_not_found_returns_none(self):
        bodies = self._make_bodies("part_1", [
            {
                "id": "face_top",
                "surface": {
                    "type": "plane",
                    "normal": {"x": 0.0, "y": 1.0, "z": 0.0},
                },
            },
        ])
        normal = get_face_normal_from_body_details(bodies, "part_1", "face_missing")
        assert normal is None

    def test_part_not_found_returns_none(self):
        bodies = self._make_bodies("part_1", [])
        normal = get_face_normal_from_body_details(bodies, "part_other", "face_x")
        assert normal is None

    def test_non_planar_face_returns_none(self):
        bodies = self._make_bodies("part_1", [
            {
                "id": "face_cyl",
                "surface": {"type": "cylinder", "origin": {}, "axis": {}},
            },
        ])
        normal = get_face_normal_from_body_details(bodies, "part_1", "face_cyl")
        assert normal is None

    def test_multiple_parts_finds_correct_one(self):
        bodies = [
            {
                "id": "part_a",
                "faces": [
                    {
                        "id": "face_1",
                        "surface": {
                            "type": "plane",
                            "normal": {"x": 1.0, "y": 0.0, "z": 0.0},
                        },
                    },
                ],
            },
            {
                "id": "part_b",
                "faces": [
                    {
                        "id": "face_1",
                        "surface": {
                            "type": "plane",
                            "normal": {"x": 0.0, "y": 0.0, "z": -1.0},
                        },
                    },
                ],
            },
        ]
        normal = get_face_normal_from_body_details(bodies, "part_b", "face_1")
        assert normal == (0.0, 0.0, -1.0)

    def test_missing_normal_keys_default_to_zero(self):
        bodies = self._make_bodies("part_1", [
            {
                "id": "face_sparse",
                "surface": {"type": "plane", "normal": {"z": 1.0}},
            },
        ])
        normal = get_face_normal_from_body_details(bodies, "part_1", "face_sparse")
        assert normal == (0.0, 0.0, 1.0)

    def test_empty_bodies_returns_none(self):
        normal = get_face_normal_from_body_details([], "part_1", "face_1")
        assert normal is None

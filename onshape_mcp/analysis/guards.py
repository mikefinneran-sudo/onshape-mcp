"""Assembly operation guards — anti-fragile validation for mate creation and positioning."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class GuardResult:
    """Result of a guard check."""

    passed: bool
    warnings: List[str]

    def format_warnings(self) -> str:
        if not self.warnings:
            return ""
        return "\n".join(f"[GUARD WARNING] {w}" for w in self.warnings) + "\n\n"


def extract_occurrence_fixed_state(
    assembly_data: Dict[str, Any],
) -> Dict[str, bool]:
    """Extract instance_id -> fixed/grounded state from assembly data."""
    fixed_states: Dict[str, bool] = {}
    root = assembly_data.get("rootAssembly", {})
    for occ in root.get("occurrences", []):
        path = occ.get("path", [])
        if len(path) == 1:
            fixed_states[path[0]] = occ.get("fixed", False)
    return fixed_states


def validate_face_pair(
    face1_normal: Tuple[float, float, float],
    face2_normal: Tuple[float, float, float],
    instance1_fixed: bool = False,
    instance2_fixed: bool = False,
) -> GuardResult:
    """Check if two face normals are anti-parallel (opposing directions).

    Anti-parallel faces cause 180-degree flips on free-floating parts.
    Safe ONLY if at least one instance is grounded — but even then, still risky.
    Same-direction faces are always recommended.
    """
    # Compute dot product
    dot = sum(a * b for a, b in zip(face1_normal, face2_normal))

    warnings = []
    if dot < -0.9:  # Anti-parallel (normals oppose)
        either_fixed = instance1_fixed or instance2_fixed
        if either_fixed:
            warnings.append(
                f"Anti-parallel faces detected (dot={dot:.2f}). One instance is grounded, "
                f"but anti-parallel mates have been observed to flip parts even with grounding. "
                f"Recommend using same-direction coplanar faces instead."
            )
        else:
            warnings.append(
                f"Anti-parallel faces detected (dot={dot:.2f}) with NO grounded instance. "
                f"This WILL cause a 180-degree flip. Use same-direction faces with offsetZ to bridge the gap."
            )
        return GuardResult(passed=either_fixed, warnings=warnings)

    return GuardResult(passed=True, warnings=[])


def validate_part_face_mapping(
    assembly_data: Dict[str, Any],
    instance_id: str,
    face_id: str,
    body_details_bodies: List[Dict[str, Any]],
) -> GuardResult:
    """Verify that a face ID belongs to the Part ID that an instance references.

    Catches the common error of using face IDs from a different part
    (e.g., using door face IDs on the back panel when both are 24x0.75x30).
    """
    # Find the instance's Part ID from assembly data
    root = assembly_data.get("rootAssembly", {})
    instances = root.get("instances", [])

    instance_part_id = None
    instance_name = "unknown"
    for inst in instances:
        if inst.get("id") == instance_id:
            instance_part_id = inst.get("partId", "")
            instance_name = inst.get("name", "unknown")
            break

    if not instance_part_id:
        return GuardResult(
            passed=False,
            warnings=[
                f"Instance {instance_id} ({instance_name}) has no Part ID "
                f"— may be a phantom instance."
            ],
        )

    # Check if face_id exists in the body matching instance_part_id
    for body in body_details_bodies:
        if body.get("id") == instance_part_id:
            face_ids = [f.get("id", "") for f in body.get("faces", [])]
            if face_id in face_ids:
                return GuardResult(passed=True, warnings=[])
            else:
                available = ", ".join(face_ids[:6])
                return GuardResult(
                    passed=False,
                    warnings=[
                        f"Face '{face_id}' NOT FOUND on Part {instance_part_id} "
                        f"(instance {instance_name}). Available faces: {available}. "
                        f"Check get_assembly for correct Part ID → face mapping."
                    ],
                )

    return GuardResult(
        passed=False,
        warnings=[
            f"Part ID {instance_part_id} not found in body details. Wrong Part Studio?"
        ],
    )


def verify_positions_stable(
    positions_before: Dict[str, Tuple[float, float, float]],
    positions_after: Dict[str, Tuple[float, float, float]],
    mated_instance_ids: Tuple[str, str],
    tolerance_inches: float = 0.1,
) -> GuardResult:
    """Detect unexpected position drift after mate creation.

    Compares positions of all instances EXCEPT the two being mated.
    If any uninvolved instance moved more than tolerance, warns about solver cascade.
    """
    warnings = []

    for inst_id, pos_before in positions_before.items():
        if inst_id in mated_instance_ids:
            continue  # Skip the mated parts — they're expected to move

        pos_after = positions_after.get(inst_id)
        if pos_after is None:
            continue

        dx = abs(pos_after[0] - pos_before[0])
        dy = abs(pos_after[1] - pos_before[1])
        dz = abs(pos_after[2] - pos_before[2])
        max_drift = max(dx, dy, dz)

        if max_drift > tolerance_inches:
            warnings.append(
                f"Instance {inst_id} drifted {max_drift:.3f}\" after mate creation "
                f"(was not involved in this mate). Solver cascade detected. "
                f"Consider deleting mates before repositioning."
            )

    return GuardResult(passed=len(warnings) == 0, warnings=warnings)


def check_ps_part_count(
    expected_count: int,
    actual_count: int,
    part_studio_name: str = "",
) -> GuardResult:
    """Warn if Part Studio has fewer parts than expected (geometry merge detection)."""
    if actual_count < expected_count:
        return GuardResult(
            passed=False,
            warnings=[
                f"Part Studio '{part_studio_name}' has {actual_count} parts but "
                f"expected {expected_count}. Parts may have merged due to overlapping "
                f"geometry. Use separate Part Studios for same-dimension parts."
            ],
        )
    return GuardResult(passed=True, warnings=[])


def get_face_normal_from_body_details(
    body_details_bodies: List[Dict[str, Any]],
    part_id: str,
    face_id: str,
) -> Optional[Tuple[float, float, float]]:
    """Extract the outward normal vector for a face from body details data.

    Returns None if the face or part is not found.
    """
    for body in body_details_bodies:
        if body.get("id") != part_id:
            continue
        for face in body.get("faces", []):
            if face.get("id") != face_id:
                continue
            surface = face.get("surface", {})
            if surface.get("type") != "plane":
                return None  # Can't determine normal for non-planar faces
            normal = surface.get("normal", {})
            return (
                normal.get("x", 0.0),
                normal.get("y", 0.0),
                normal.get("z", 0.0),
            )
    return None

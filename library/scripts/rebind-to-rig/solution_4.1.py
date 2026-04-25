import bpy
from mathutils import Matrix

# ── Parameters ────────────────────────────────────────────────────────────────
SOURCE_ARMATURE_NAME = ""    # Auto-detect if empty (armature that is not meta/rig, has mesh children)
META_ARMATURE_NAME   = ""    # Auto-detect if empty
RIG_ARMATURE_NAME    = ""    # Auto-detect if empty
DRY_RUN              = False # If True: print what would happen but make no changes
POSITION_THRESHOLD   = 0.15  # Max bone distance for position-based mapping (Blender units)
EYES_VG_NAME         = "Eyes"
EYEBROW_VG_L         = "Eyebrow_L"
EYEBROW_VG_R         = "Eyebrow_R"
EYEBROW_VG_COMBINED  = "Eyebrows"

# USAGE:
# SOURCE_ARMATURE_NAME - original Synty armature; leave empty to auto-detect
# META_ARMATURE_NAME   - Rigify metarig; leave empty to auto-detect
# RIG_ARMATURE_NAME    - generated Rigify rig; leave empty to auto-detect
# DRY_RUN              - set True first to verify the bone mapping before committing
# POSITION_THRESHOLD   - increase if auto-mapping misses bones on unusual character scales
# EYES_VG_NAME / EYEBROW_VG_* - Synty vertex group names; change only if your model differs

# ── Constants ──────────────────────────────────────────────────────────────────
DEF_PREFIX = "DEF-"

# Rigify renames these spine bones post-generation — resolve them here
BONE_NAME_OVERRIDES = {
    "DEF-spine.006": "DEF-head",
    "DEF-spine.004": "DEF-neck",
}

FACE_DEF_TO_ORG = [
    ("DEF-Eye_L",      "ORG-Eye_L"),
    ("DEF-Eye_R",      "ORG-Eye_R"),
    ("DEF-Eyebrow_L",  "ORG-Eyebrow_L"),
    ("DEF-Eyebrow_R",  "ORG-Eyebrow_R"),
]


# ── Pure logic helpers ─────────────────────────────────────────────────────────

def resolve_rig_bone(rig_arm, meta_bone_name):
    """Resolve META bone name to DEF bone name in the generated rig."""
    def_name = DEF_PREFIX + meta_bone_name
    def_name = BONE_NAME_OVERRIDES.get(def_name, def_name)
    if rig_arm.pose.bones.get(def_name):
        return def_name
    return None


def _coerce_armature_object(candidate):
    if not candidate:
        return None
    if isinstance(candidate, str):
        candidate = _get_object_by_name(candidate)
    if candidate and hasattr(candidate, "type") and candidate.type == 'ARMATURE':
        return candidate
    return None


def _looks_like_generated_rig(arm_obj):
    """Heuristic: generated Rigify rig has both DEF- and ORG- spine pose bones."""
    if not arm_obj or not getattr(arm_obj, "pose", None):
        return False
    pose_bones = arm_obj.pose.bones
    has_def = any(pose_bones.get(n) for n in ("DEF-spine", "DEF-spine.001", "DEF-head", "DEF-neck"))
    has_org = any(pose_bones.get(n) for n in ("ORG-spine", "ORG-spine.001", "ORG-head", "ORG-neck"))
    return has_def and has_org


def _iter_scene_objects():
    objects = bpy.data.objects
    if hasattr(objects, "values"):
        return objects.values()
    return objects


def _get_object_by_name(name):
    objects = bpy.data.objects
    if hasattr(objects, "get"):
        return objects.get(name)
    for obj in _iter_scene_objects():
        if getattr(obj, "name", None) == name:
            return obj
    return None


def get_rig_from_meta(meta_arm_obj):
    """Find generated RIG from metarig via rigify_target_rig property, then name fallbacks."""
    if not meta_arm_obj or getattr(meta_arm_obj, "data", None) is None:
        return None
    arm_data = meta_arm_obj.data

    # Try direct Rigify property first
    for ref in [
        getattr(arm_data, "rigify_target_rig", None),
        arm_data.get("rigify_target_rig") if hasattr(arm_data, "get") else None,
    ]:
        rig = _coerce_armature_object(ref)
        if rig and rig != meta_arm_obj:
            return rig

    # Name-based fallbacks
    base = getattr(meta_arm_obj, "name", "")
    for name in [
        base.replace("META-", "RIG-", 1),
        base.replace("metarig", "rig", 1),
        f"RIG-{base}",
    ]:
        rig = _coerce_armature_object(_get_object_by_name(name))
        if rig and rig != meta_arm_obj:
            return rig

    # Last resort: find any rig-looking armature
    candidates = [
        obj for obj in _iter_scene_objects()
        if obj.type == 'ARMATURE' and obj != meta_arm_obj and _looks_like_generated_rig(obj)
    ]
    if len(candidates) == 1:
        return candidates[0]
    preferred = next((o for o in candidates if o.name.startswith("RIG-")), None)
    return preferred


def build_bone_mapping(source_arm_obj, meta_arm_obj, threshold=0.15):
    """Map source bone names to META bone names by world-space head position proximity."""
    mapping = {}
    src_mat  = source_arm_obj.matrix_world
    meta_mat = meta_arm_obj.matrix_world

    meta_positions = [
        (bone.name, meta_mat @ bone.head_local)
        for bone in meta_arm_obj.data.bones
    ]

    for src_bone in source_arm_obj.data.bones:
        src_head_world = src_mat @ src_bone.head_local
        best_name = None
        best_dist = threshold
        for meta_name, meta_head_world in meta_positions:
            dist = (src_head_world - meta_head_world).length
            if dist < best_dist:
                best_dist = dist
                best_name = meta_name
        if best_name:
            mapping[src_bone.name] = best_name
    return mapping


def get_meshes_of_armature(source_arm_obj):
    return [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.parent == source_arm_obj]


def split_by_symmetry(mesh_obj, old_vg_name, new_vg_l, new_vg_r, dry_run=False):
    """Split a shared vertex group into L/R halves by X-axis position (X>=0 → L)."""
    vg = mesh_obj.vertex_groups.get(old_vg_name)
    if vg is None:
        return 0, 0
    vg_idx = vg.index
    weights = {}
    for vert in mesh_obj.data.vertices:
        for g in vert.groups:
            if g.group == vg_idx:
                weights[vert.index] = (vert.co.x, g.weight)
                break
    if not weights:
        return 0, 0
    if dry_run:
        count_l = sum(1 for x, _ in weights.values() if x >= 0)
        return count_l, len(weights) - count_l
    vg_l = mesh_obj.vertex_groups.get(new_vg_l) or mesh_obj.vertex_groups.new(name=new_vg_l)
    vg_r = mesh_obj.vertex_groups.get(new_vg_r) or mesh_obj.vertex_groups.new(name=new_vg_r)
    count_l, count_r = 0, 0
    for vert_idx, (x, weight) in weights.items():
        if x >= 0:
            vg_l.add([vert_idx], weight, 'REPLACE'); count_l += 1
        else:
            vg_r.add([vert_idx], weight, 'REPLACE'); count_r += 1
    mesh_obj.vertex_groups.remove(vg)
    return count_l, count_r


def rename_vertex_groups_with_mapping(mesh_obj, bone_mapping, rig_arm_obj, dry_run=False):
    """Rename vertex groups from source names to DEF bone names via the bone mapping."""
    renames = []
    for vg in list(mesh_obj.vertex_groups):
        meta_bone_name = bone_mapping.get(vg.name)
        if meta_bone_name is None:
            continue
        new_name = resolve_rig_bone(rig_arm_obj, meta_bone_name)
        if new_name and new_name != vg.name:
            renames.append((vg.name, new_name))
            if not dry_run:
                vg.name = new_name
    return renames


def rebind_armature_modifier(mesh_obj, source_arm_obj, rig_arm_obj, dry_run=False):
    """Replace armature modifier pointing to source with one pointing to rig."""
    old_mods = [mod.name for mod in mesh_obj.modifiers
                if mod.type == 'ARMATURE' and mod.object == source_arm_obj]
    if not old_mods:
        return False
    if not dry_run:
        for mod_name in old_mods:
            mesh_obj.modifiers.remove(mesh_obj.modifiers[mod_name])
        new_mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
        new_mod.object = rig_arm_obj
    return True


def reparent_to_rig(mesh_obj, rig_arm_obj, dry_run=False):
    """Reparent mesh to rig, preserving world matrix."""
    if mesh_obj.parent == rig_arm_obj:
        return
    if not dry_run:
        world_mat = mesh_obj.matrix_world.copy()
        mesh_obj.parent = rig_arm_obj
        mesh_obj.parent_type = 'OBJECT'
        mesh_obj.matrix_world = world_mat


def set_def_org_constraints(rig_arm_obj, dry_run=False):
    """Add COPY_TRANSFORMS on DEF face bones → ORG face bones."""
    result = []
    for def_name, org_name in FACE_DEF_TO_ORG:
        def_pb = rig_arm_obj.pose.bones.get(def_name)
        org_pb = rig_arm_obj.pose.bones.get(org_name)
        if not def_pb or not org_pb:
            continue
        result.append(def_name)
        if dry_run:
            continue
        existing = next(
            (c for c in def_pb.constraints
             if c.type == 'COPY_TRANSFORMS' and c.target == rig_arm_obj and c.subtarget == org_name),
            None,
        )
        if existing:
            continue
        ct = def_pb.constraints.new('COPY_TRANSFORMS')
        ct.target = rig_arm_obj; ct.subtarget = org_name
    return result


# ── Entry point ────────────────────────────────────────────────────────────────

def run():
    dry_run = DRY_RUN
    prefix = "[DRY RUN] " if dry_run else ""

    # Resolve source armature
    if SOURCE_ARMATURE_NAME:
        source_arm = _coerce_armature_object(SOURCE_ARMATURE_NAME)
        if source_arm is None:
            print(f"ERROR: Source armature '{SOURCE_ARMATURE_NAME}' not found.")
            return
    else:
        candidates = [
            obj for obj in _iter_scene_objects()
            if obj.type == 'ARMATURE' and not _looks_like_generated_rig(obj)
            and get_meshes_of_armature(obj)
        ]
        if not candidates:
            print("ERROR: No source armature found (no armature with mesh children).")
            return
        if len(candidates) > 1:
            print(f"ERROR: Multiple candidates: {[o.name for o in candidates]}. Set SOURCE_ARMATURE_NAME.")
            return
        source_arm = candidates[0]

    # Resolve metarig
    if META_ARMATURE_NAME:
        meta_arm = _coerce_armature_object(META_ARMATURE_NAME)
        if meta_arm is None:
            print(f"ERROR: Meta armature '{META_ARMATURE_NAME}' not found.")
            return
    else:
        candidates = [
            obj for obj in _iter_scene_objects()
            if obj.type == 'ARMATURE' and obj != source_arm and not _looks_like_generated_rig(obj)
            and "meta" in obj.name.lower()
        ]
        if not candidates:
            candidates = [
                obj for obj in _iter_scene_objects()
                if obj.type == 'ARMATURE' and obj != source_arm and not _looks_like_generated_rig(obj)
            ]
        if not candidates:
            print("ERROR: Could not auto-detect metarig. Set META_ARMATURE_NAME.")
            return
        if len(candidates) > 1:
            print(f"ERROR: Multiple metarig candidates: {[o.name for o in candidates]}. Set META_ARMATURE_NAME.")
            return
        meta_arm = candidates[0]

    # Resolve rig
    if RIG_ARMATURE_NAME:
        rig_arm = _coerce_armature_object(RIG_ARMATURE_NAME)
        if rig_arm is None:
            print(f"ERROR: Rig armature '{RIG_ARMATURE_NAME}' not found.")
            return
    else:
        rig_arm = get_rig_from_meta(meta_arm)
        if rig_arm is None:
            print(f"ERROR: Could not find generated rig for '{meta_arm.name}'. Run rigify-generate-and-fix first.")
            return

    print(f"{prefix}Rebind: '{source_arm.name}' → META='{meta_arm.name}' → RIG='{rig_arm.name}'")

    meshes = get_meshes_of_armature(source_arm)
    if not meshes:
        print(f"  No meshes parented to '{source_arm.name}'.")
    else:
        print(f"  {len(meshes)} mesh(es).")

    bone_mapping = build_bone_mapping(source_arm, meta_arm, threshold=POSITION_THRESHOLD)
    print(f"  {len(bone_mapping)} bones mapped (threshold={POSITION_THRESHOLD}).")

    for mesh_obj in meshes:
        print(f"  Processing: {mesh_obj.name}")

        if mesh_obj.vertex_groups.get(EYES_VG_NAME):
            count_l, count_r = split_by_symmetry(mesh_obj, EYES_VG_NAME, "DEF-Eye_L", "DEF-Eye_R", dry_run)
            print(f"    Eyes split: {count_l} L / {count_r} R vertices")

        if mesh_obj.vertex_groups.get(EYEBROW_VG_COMBINED):
            count_l, count_r = split_by_symmetry(mesh_obj, EYEBROW_VG_COMBINED, "DEF-Eyebrow_L", "DEF-Eyebrow_R", dry_run)
            print(f"    Eyebrows split: {count_l} L / {count_r} R vertices")

        renames = rename_vertex_groups_with_mapping(mesh_obj, bone_mapping, rig_arm, dry_run)
        for old, new in renames:
            print(f"    VG: '{old}' → '{new}'")

        found_mod = rebind_armature_modifier(mesh_obj, source_arm, rig_arm, dry_run)
        if not found_mod:
            print(f"    WARNING: No armature modifier pointing to '{source_arm.name}' in '{mesh_obj.name}'")

        reparent_to_rig(mesh_obj, rig_arm, dry_run)

    constrained = set_def_org_constraints(rig_arm, dry_run)
    if constrained:
        print(f"  DEF→ORG constraints: {', '.join(constrained)}")

    print(f"{prefix}rebind-to-rig complete ({len(meshes)} mesh(es)).")


run()

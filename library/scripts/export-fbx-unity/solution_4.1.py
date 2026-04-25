"""
Seredos Export Characters
=========================
Exports the selected RIG + all child meshes as FBX for Unity.
Each action is exported separately as a humanoid animation FBX
(visual baking via nla.bake so constraint-driven bones land correctly).

FACE- animations (e.g. "FACE-TestAnimation") are exported as blend-shape
animations because Unity's Humanoid Animator freezes unmapped bones (DEF-Eyebrow
etc.). Shape keys are created once via setup_face_shape_keys() (NO drivers --
drivers would activate shape keys simultaneously with bones causing double
deformation). The bone->shape-key mapping is encoded in the shape key name
(FACE_{bone}_{axis}_{dir}) and the extreme value stored as a custom property
on the mesh object.

Paths (relative to blend file):
  Model:       ../Assets/Seredos/Character/Models/Characters/characters.fbx
  Animations:  ../Assets/Seredos/Character/Animations/<Action>.fbx
  Face Anim.:  ../Assets/Seredos/Character/Animations/Face/<Action>.fbx
  Items:       ../Assets/Seredos/Character/Models/Items/<ItemName>.fbx

FBX settings:
  -Y Forward, Z Up, Apply Transform ON, Only Deform Bones ON, No Leaf Bones
"""

import os
import bpy

# ── Parameters ────────────────────────────────────────────────────────────────
RIG_NAME          = ""   # Auto-detect if empty (active armature or first armature with DEF/ORG bones)
BLEND_FILE_PATH   = bpy.data.filepath

EXPORT_SUBPATH    = os.path.join("..", "Assets", "Seredos", "Character", "Models", "Characters")
ANIM_SUBPATH      = os.path.join("..", "Assets", "Seredos", "Character", "Animations")
FACE_ANIM_SUBPATH = os.path.join("..", "Assets", "Seredos", "Character", "Animations", "Face")
ITEMS_SUBPATH     = os.path.join("..", "Assets", "Seredos", "Character", "Models", "Items")
EXPORT_FILE       = "characters.fbx"

SLOT_PREFIX              = "SLOT-"
FACE_PREFIX              = "FACE-"
ANIM_BLACKLIST_PREFIXES  = {"Armature|Take 001|BaseLayer"}

FBX_SETTINGS = dict(
    axis_forward             = '-Y',
    axis_up                  = 'Z',
    apply_scale_options      = 'FBX_SCALE_UNITS',
    apply_unit_scale         = True,
    bake_space_transform     = True,
    add_leaf_bones           = False,
    primary_bone_axis        = 'Y',
    secondary_bone_axis      = 'X',
    use_armature_deform_only = True,
    mesh_smooth_type         = 'FACE',
    use_mesh_modifiers       = True,
    path_mode                = 'RELATIVE',
)

# Internal constants (not user-configurable)
TRANSFORMS_EMPTY_NAME = "transforms"
_INVALID_FILENAME_CHARS = r'\/:*?"<>|'
_CONSTRAINT_TYPES_WITH_TARGET = {
    'COPY_TRANSFORMS', 'COPY_LOCATION', 'COPY_ROTATION',
    'COPY_SCALE', 'DAMPED_TRACK', 'LOCKED_TRACK', 'STRETCH_TO',
    'TRACK_TO', 'CLAMP_TO',
}
_AXIS_LABELS = {
    'location':            ['loc_x', 'loc_y', 'loc_z'],
    'rotation_euler':      ['eul_x', 'eul_y', 'eul_z'],
    'rotation_quaternion': ['qut_w', 'qut_x', 'qut_y', 'qut_z'],
    'scale':               ['sca_x', 'sca_y', 'sca_z'],
}
_AXIS_LABEL_TO_SUFFIX_IDX = {
    label: (suffix, idx)
    for suffix, labels in _AXIS_LABELS.items()
    for idx, label in enumerate(labels)
}
_MESH_PROP_PREFIX = 'FACESK_'

# ---------------------------------------------------------------------------
# Pure logic (testable without bpy)
# ---------------------------------------------------------------------------

def get_export_paths(blend_filepath: str) -> tuple[str, str, str, str]:
    """Returns (model_dir, anim_dir, face_anim_dir, fbx_path).
    blend_filepath must be an absolute path (bpy.data.filepath).
    """
    blend_dir     = os.path.dirname(os.path.abspath(blend_filepath))
    model_dir     = os.path.normpath(os.path.join(blend_dir, EXPORT_SUBPATH))
    anim_dir      = os.path.normpath(os.path.join(blend_dir, ANIM_SUBPATH))
    face_anim_dir = os.path.normpath(os.path.join(blend_dir, FACE_ANIM_SUBPATH))
    fbx_path      = os.path.join(model_dir, EXPORT_FILE)
    return model_dir, anim_dir, face_anim_dir, fbx_path


def get_item_export_path(blend_filepath: str) -> str:
    """Returns the absolute items export path.
    blend_filepath must be an absolute path (bpy.data.filepath).
    """
    blend_dir = os.path.dirname(os.path.abspath(blend_filepath))
    return os.path.normpath(os.path.join(blend_dir, ITEMS_SUBPATH))


def find_exportable_items(rig) -> list:
    """Finds all items in the rig: MESH objects that are direct children of a SLOT-* object.

    Membership in a slot (not a 'transforms' child) defines an item.
    An optional 'transforms' child empty encodes per-slot anchor points -- if absent,
    the object origin is used as anchor.

    Returns a list of bpy.types.Object (no duplicates).
    Pure logic -- testable with mock objects without running bpy.
    """
    items = []
    seen  = set()
    for obj in rig.children_recursive:
        if not obj.name.startswith(SLOT_PREFIX):
            continue
        for child in obj.children:
            if child.type == 'MESH' and id(child) not in seen:
                items.append(child)
                seen.add(id(child))
    return items


def collect_character_objects(rig, items: list) -> list:
    """Returns all objects for the character FBX, excluding items and their children.

    items: pre-computed list from find_exportable_items(rig) --
           passed externally so it isn't computed twice in execute().

    Pure function -- testable without bpy.
    """
    item_ids = {id(obj) for item in items for obj in collect_hierarchy(item)}
    return [obj for obj in collect_hierarchy(rig) if id(obj) not in item_ids]


def sanitize_filename(name: str) -> str:
    """Replaces Windows-invalid filename characters with '_'."""
    for ch in _INVALID_FILENAME_CHARS:
        name = name.replace(ch, '_')
    return name


def should_export_action(
    action_name: str,
    blacklist_prefixes: set[str] = ANIM_BLACKLIST_PREFIXES,
) -> bool:
    """True if the action should be exported.

    An action is skipped if its name starts with one of the blacklist prefixes.
    Covers both 'Armature|Take 001|BaseLayer' and numbered variants '.001', '.002' etc.
    """
    for prefix in blacklist_prefixes:
        if action_name == prefix or action_name.startswith(prefix + "."):
            return False
    return True


# ---------------------------------------------------------------------------
# bpy-dependent helper functions
# ---------------------------------------------------------------------------

def collect_hierarchy(root_obj) -> list:
    """Returns root_obj and all its descendants (children, grandchildren, ...)."""
    result = [root_obj]

    def _recurse(obj):
        for child in obj.children:
            result.append(child)
            _recurse(child)

    _recurse(root_obj)
    return result


def switch_to_object_mode() -> str:
    """Switches to Object Mode, returns the previous mode."""
    prev = bpy.context.mode
    if prev != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    return prev


def restore_mode(prev_mode: str) -> None:
    """Restores the previous mode."""
    if prev_mode == 'OBJECT':
        return
    # POSE is not a valid mode for mode_set; use posemode_toggle instead
    if prev_mode == 'POSE':
        try:
            bpy.ops.object.posemode_toggle()
        except Exception:
            pass
        return
    mode = prev_mode.replace('EDIT_ARMATURE', 'EDIT')
    bpy.ops.object.mode_set(mode=mode)


def export_model(fbx_path: str, objects: list) -> None:
    """Exports the given objects as a static FBX (no animations)."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]

    bpy.ops.export_scene.fbx(
        filepath      = fbx_path,
        use_selection = True,
        bake_anim     = False,
        **FBX_SETTINGS,
    )
    print(f"[seredos_export] Model -> {fbx_path}")


def export_single_item(items_dir: str, item_obj) -> None:
    """Exports a single item as its own FBX file.

    Workflow:
    1. Save parent state (parent, parent_type, parent_bone, matrices)
    2. Temporarily unparent the item and move to origin (0,0,0)
    3. Export item + children as FBX
    4. Fully restore parent state

    IMPORTANT: Do not touch children's transforms. The local offsets to the item
    are the actual anchor data and must remain unchanged for the export.
    """
    saved_parent      = item_obj.parent
    saved_parent_type = item_obj.parent_type
    saved_parent_bone = item_obj.parent_bone
    saved_mpi         = item_obj.matrix_parent_inverse.copy()
    saved_local       = item_obj.matrix_local.copy()

    # Unparent: Blender maintains world matrix when parent=None is set
    item_obj.parent = None
    # Move to origin
    item_obj.location            = (0, 0, 0)
    item_obj.rotation_euler      = (0, 0, 0)
    item_obj.rotation_quaternion = (1, 0, 0, 0)
    item_obj.scale               = (1, 1, 1)
    bpy.context.view_layer.update()

    fbx_path = os.path.join(items_dir, sanitize_filename(item_obj.name) + ".fbx")
    export_model(fbx_path, collect_hierarchy(item_obj))

    # Restore parent state
    item_obj.parent               = saved_parent
    item_obj.parent_type          = saved_parent_type
    item_obj.parent_bone          = saved_parent_bone
    item_obj.matrix_parent_inverse = saved_mpi
    item_obj.matrix_local         = saved_local
    bpy.context.view_layer.update()
    print(f"[seredos_export] Item -> {fbx_path}")


def export_items(items_dir: str, items: list) -> int:
    """Exports all items as separate FBX files to items_dir.

    Returns the number of exported items.
    """
    os.makedirs(items_dir, exist_ok=True)
    for item_obj in items:
        export_single_item(items_dir, item_obj)
    return len(items)


def bake_action(rig, action):
    """Bakes an action onto all bones with visual_keying (constraint-driven).

    Sets action as the active action, bakes all bones via nla.bake,
    and returns the new (baked) action.
    The baked action must be manually removed after export.
    """
    rig.animation_data.action = action
    frame_start = int(action.frame_range[0])
    frame_end   = int(action.frame_range[1])

    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(
        frame_start        = frame_start,
        frame_end          = frame_end,
        step               = 1,
        only_selected      = False,
        visual_keying      = True,
        clear_constraints  = False,
        clear_parents      = False,
        use_current_action = False,
        clean_curves       = False,
        bake_types         = {'POSE'},
    )
    return rig.animation_data.action


def export_animations(anim_dir: str, face_anim_dir: str, rig) -> tuple[int, int]:
    """Exports all exportable actions.

    Normal actions are baked as humanoid FBX.
    FACE- actions are exported as blend-shape FBX (Animations/Face/).
    Returns (body_count, face_count).
    """
    os.makedirs(anim_dir, exist_ok=True)

    actions = [a for a in bpy.data.actions if should_export_action(a.name)]

    if not actions:
        print("[seredos_export] No animations found to export.")
        return 0, 0

    prev_action = rig.animation_data.action if rig.animation_data else None

    body_count = 0
    face_count = 0

    # --- Body animations (Humanoid) ---
    body_actions = [a for a in actions if not a.name.startswith(FACE_PREFIX)]
    face_actions = [a for a in actions if a.name.startswith(FACE_PREFIX)]

    if body_actions:
        bpy.ops.object.select_all(action='DESELECT')
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')

        for action in body_actions:
            fbx_path = os.path.join(anim_dir, sanitize_filename(action.name) + ".fbx")
            print(f"[seredos_export] Baking '{action.name}' ...")
            baked = bake_action(rig, action)

            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.export_scene.fbx(
                filepath                        = fbx_path,
                use_selection                   = True,
                bake_anim                       = True,
                bake_anim_use_all_actions       = False,
                bake_anim_step                  = 1.0,
                bake_anim_simplify_factor       = 0.0,
                bake_anim_use_nla_strips        = False,
                bake_anim_force_startend_keying = True,
                **FBX_SETTINGS,
            )
            print(f"[seredos_export] Animation -> {fbx_path}")
            bpy.data.actions.remove(baked)
            body_count += 1
            bpy.ops.object.mode_set(mode='POSE')

        bpy.ops.object.mode_set(mode='OBJECT')

    # --- Face animations (Blend Shapes) ---
    for action in face_actions:
        face_meshes = get_face_meshes_for_action(rig, action)
        if not face_meshes:
            print(f"[seredos_export] '{action.name}': No face meshes found -- skipped.")
            continue
        export_face_animation(face_anim_dir, rig, face_meshes, action)
        face_count += 1

    if rig.animation_data:
        rig.animation_data.action = prev_action

    return body_count, face_count


# ---------------------------------------------------------------------------
# Face shape key helper functions (testable without bpy side effects)
# ---------------------------------------------------------------------------

def get_ctrl_bones_from_action(action) -> set:
    """Returns all bone names animated in an action."""
    bones = set()
    for fc in action.fcurves:
        if fc.data_path.startswith('pose.bones["'):
            bones.add(fc.data_path.split('"')[1])
    return bones


def find_def_bones_for_ctrl(rig, ctrl_bone_name: str) -> set:
    """Traverses constraints recursively: finds all DEF-bones that depend
    (directly or indirectly) on ctrl_bone_name and have vertex groups."""
    result = set()
    visited = set()

    def _recurse(bone_name):
        if bone_name in visited:
            return
        visited.add(bone_name)
        for pbone in rig.pose.bones:
            for c in pbone.constraints:
                if c.type in _CONSTRAINT_TYPES_WITH_TARGET:
                    if getattr(c, 'subtarget', '') == bone_name:
                        _recurse(pbone.name)
                        if pbone.name.startswith('DEF-'):
                            result.add(pbone.name)

    _recurse(ctrl_bone_name)
    return result


def get_face_meshes_for_action(rig, action) -> list:
    """Returns all mesh children of the rig whose vertex groups are influenced
    by the ctrl-bones animated in the action (via constraint chain)."""
    ctrl_bones = get_ctrl_bones_from_action(action)
    def_bones = set()
    for ctrl in ctrl_bones:
        def_bones |= find_def_bones_for_ctrl(rig, ctrl)

    face_meshes = []
    for obj in rig.children_recursive:
        if obj.type != 'MESH':
            continue
        vg_names = {vg.name for vg in obj.vertex_groups}
        if def_bones & vg_names:
            face_meshes.append(obj)
    return face_meshes


def _get_fcurve_range(action, bone_name: str, data_path_suffix: str, array_index: int):
    """Returns (min_val, max_val) of all keyframes for an FCurve, or None."""
    dp = f'pose.bones["{bone_name}"].{data_path_suffix}'
    for fc in action.fcurves:
        if fc.data_path == dp and fc.array_index == array_index:
            vals = [kp.co.y for kp in fc.keyframe_points]
            if vals:
                return min(vals), max(vals)
    return None


def _remove_driver_from_shape_key(mesh_obj, sk_name: str) -> None:
    """Removes an existing driver from the shape key (cleanup of older setups)."""
    mesh = mesh_obj.data
    if mesh.shape_keys is None:
        return
    sk = mesh.shape_keys.key_blocks.get(sk_name)
    if sk is None:
        return
    # driver_remove() is idempotent -- no error if no driver present
    try:
        sk.driver_remove('value')
    except Exception:
        pass
    anim_data = mesh.shape_keys.animation_data
    if anim_data:
        dp = f'key_blocks["{sk_name}"].value'
        for d in list(anim_data.drivers):
            if d.data_path == dp:
                anim_data.drivers.remove(d)


def _create_or_update_shape_key(mesh_obj, sk_name: str, rig, depsgraph,
                                 extreme_val: float) -> object:
    """Creates or overwrites a shape key with the current evaluated mesh.

    Stores the extreme value as a custom property on the mesh object (ID type).
    The bone mapping is encoded in the shape key name (parsed by _parse_face_sk_name
    during export). No driver -- shape key stays at value 0 in Blender.
    """
    mesh = mesh_obj.data

    # Ensure basis key exists
    if mesh.shape_keys is None:
        mesh_obj.shape_key_add(name='Basis', from_mix=False)

    sk_blocks = mesh.shape_keys.key_blocks

    # Remove existing driver (idempotency on repeat)
    _remove_driver_from_shape_key(mesh_obj, sk_name)

    # Get evaluated mesh
    eval_obj  = mesh_obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()

    if sk_name in sk_blocks:
        sk = sk_blocks[sk_name]
        for i, v in enumerate(eval_mesh.vertices):
            sk.data[i].co = v.co.copy()
    else:
        sk = mesh_obj.shape_key_add(name=sk_name, from_mix=True)
        sk.interpolation = 'KEY_LINEAR'
        for i, v in enumerate(eval_mesh.vertices):
            sk.data[i].co = v.co.copy()

    eval_obj.to_mesh_clear()

    # Store extreme value on mesh object (mesh is ID type -> custom props ok)
    mesh_obj.data[f'{_MESH_PROP_PREFIX}{sk_name}'] = float(extreme_val)

    # Explicitly set to 0 -- no visual influence in Blender
    sk.value = 0.0
    return sk


def _get_bone_attr_val(pbone, suffix: str, array_index: int) -> float:
    """Reads a bone attribute value (location, rotation_euler, etc.)."""
    if suffix == 'location':
        return pbone.location[array_index]
    if suffix == 'rotation_euler':
        return pbone.rotation_euler[array_index]
    if suffix == 'rotation_quaternion':
        return pbone.rotation_quaternion[array_index]
    if suffix == 'scale':
        return pbone.scale[array_index]
    return 0.0


def setup_face_shape_keys(rig) -> int:
    """Creates or updates shape keys for all FACE- actions.

    For each animated ctrl-bone FCurve, shape keys for extreme values
    (min and max of the keyframe range) are created. The bone->shape-key mapping
    is encoded in the shape key name (FACE_{bone}_{axis}_{dir}), the extreme value
    stored as a custom property on the mesh object. No drivers -- shape keys always
    stay at value 0 in Blender and don't affect normal preview. Existing shape keys
    are overwritten (idempotent). Existing drivers from older setups are removed.

    Returns the total number of shape keys created/updated.
    """
    face_actions = [a for a in bpy.data.actions if a.name.startswith(FACE_PREFIX)]
    if not face_actions:
        print("[seredos_export] No FACE- actions found.")
        return 0

    # Collect all ctrl-bones + FCurves from all FACE- actions
    # {(bone_name, data_path_suffix, array_index): (global_min, global_max)}
    fcurve_ranges: dict = {}
    for action in face_actions:
        ctrl_bones = get_ctrl_bones_from_action(action)
        for bone_name in ctrl_bones:
            for fc in action.fcurves:
                if not fc.data_path.startswith(f'pose.bones["{bone_name}"]'):
                    continue
                # Extract suffix: pose.bones["name"].location -> location
                suffix = fc.data_path[len(f'pose.bones["{bone_name}"].') :]
                key = (bone_name, suffix, fc.array_index)
                vals = [kp.co.y for kp in fc.keyframe_points]
                if not vals:
                    continue
                lo, hi = min(vals), max(vals)
                if key in fcurve_ranges:
                    prev_lo, prev_hi = fcurve_ranges[key]
                    fcurve_ranges[key] = (min(lo, prev_lo), max(hi, prev_hi))
                else:
                    fcurve_ranges[key] = (lo, hi)

    if not fcurve_ranges:
        print("[seredos_export] No animated FCurves in FACE- actions.")
        return 0

    # Find meshes influenced by these ctrl-bones
    all_ctrl_bones = {k[0] for k in fcurve_ranges}
    def_bones = set()
    for ctrl in all_ctrl_bones:
        def_bones |= find_def_bones_for_ctrl(rig, ctrl)

    face_meshes = [
        obj for obj in rig.children_recursive
        if obj.type == 'MESH'
        and def_bones & {vg.name for vg in obj.vertex_groups}
    ]

    if not face_meshes:
        print("[seredos_export] No face meshes with matching vertex groups found.")
        return 0

    # Bring rig to rest pose and save current state
    prev_action = rig.animation_data.action if rig.animation_data else None
    if rig.animation_data:
        rig.animation_data.action = None
    prev_pose_positions = {}
    for pbone in rig.pose.bones:
        prev_pose_positions[pbone.name] = (
            pbone.location.copy(),
            pbone.rotation_quaternion.copy(),
            pbone.rotation_euler.copy(),
            pbone.scale.copy(),
        )
        pbone.location = (0, 0, 0)
        pbone.rotation_quaternion = (1, 0, 0, 0)
        pbone.rotation_euler = (0, 0, 0)
        pbone.scale = (1, 1, 1)

    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()

    # Ensure all meshes have a basis key
    for mesh_obj in face_meshes:
        if mesh_obj.data.shape_keys is None:
            mesh_obj.shape_key_add(name='Basis', from_mix=False)

    total_keys = 0

    for (bone_name, suffix, array_index), (val_min, val_max) in fcurve_ranges.items():
        # Only axes with actual movement (range > epsilon)
        if abs(val_max - val_min) < 1e-5:
            continue

        labels_for_suffix = _AXIS_LABELS.get(suffix)
        axis_label = labels_for_suffix[array_index] if labels_for_suffix else f'ch{array_index}'

        for extreme_val, direction in ((val_min, 'neg'), (val_max, 'pos')):
            # Only side with deflection (magnitude > epsilon relative to rest = 0)
            if abs(extreme_val) < 1e-5:
                continue

            sk_name = f'FACE_{bone_name}_{axis_label}_{direction}'

            # Move bone to extreme position
            pbone = rig.pose.bones.get(bone_name)
            if pbone is None:
                continue
            if suffix == 'location':
                loc = [0.0, 0.0, 0.0]
                loc[array_index] = extreme_val
                pbone.location = loc
            elif suffix == 'rotation_euler':
                rot = [0.0, 0.0, 0.0]
                rot[array_index] = extreme_val
                pbone.rotation_euler = rot
            elif suffix == 'rotation_quaternion':
                quat = [1.0, 0.0, 0.0, 0.0]
                quat[array_index] = extreme_val
                pbone.rotation_quaternion = quat
            elif suffix == 'scale':
                sca = [1.0, 1.0, 1.0]
                sca[array_index] = extreme_val
                pbone.scale = sca

            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()

            for mesh_obj in face_meshes:
                _create_or_update_shape_key(
                    mesh_obj, sk_name, rig, depsgraph, extreme_val,
                )
                total_keys += 1

            # Reset bone
            pbone.location = (0, 0, 0)
            pbone.rotation_quaternion = (1, 0, 0, 0)
            pbone.rotation_euler = (0, 0, 0)
            pbone.scale = (1, 1, 1)

    # Restore rig state
    for pbone in rig.pose.bones:
        if pbone.name in prev_pose_positions:
            loc, quat, eul, sca = prev_pose_positions[pbone.name]
            pbone.location           = loc
            pbone.rotation_quaternion = quat
            pbone.rotation_euler     = eul
            pbone.scale              = sca
    if rig.animation_data:
        rig.animation_data.action = prev_action
    bpy.context.view_layer.update()

    print(f"[seredos_export] {total_keys} shape key(s) created/updated on {len(face_meshes)} mesh(es).")
    return total_keys


# ---------------------------------------------------------------------------
# Face animation export helpers
# ---------------------------------------------------------------------------

def _parse_face_sk_name(sk_name: str):
    """Parses a FACE_ shape key name back to (bone_name, suffix, idx, direction).

    Format: FACE_{bone_name}_{axis_label}_{direction}
    Example: 'FACE_eyebrow_ctrl_center_loc_y_pos' ->
             ('eyebrow_ctrl_center', 'location', 1, 'pos')
    Returns None if the name does not match.
    """
    if not sk_name.startswith('FACE_'):
        return None
    rest = sk_name[5:]
    for direction in ('pos', 'neg'):
        dir_suffix = f'_{direction}'
        if not rest.endswith(dir_suffix):
            continue
        rest_no_dir = rest[: -len(dir_suffix)]
        for axis_label, (suffix, idx) in _AXIS_LABEL_TO_SUFFIX_IDX.items():
            tail = f'_{axis_label}'
            if rest_no_dir.endswith(tail):
                bone_name = rest_no_dir[: -len(tail)]
                return bone_name, suffix, idx, direction
    return None


def bake_shape_key_animation(face_meshes, action, rig) -> dict:
    """Bakes shape key values per frame from bone positions as keyframes.

    Reads the animated ctrl-bone positions from the evaluated rig per frame
    and calculates shape key values via shape key name parsing and mesh custom
    properties. No driver needed.

    Returns a dict {mesh_name: {sk_name: [frame_numbers]}} so that
    cleanup_shape_key_keyframes can remove the keyframes again.
    """
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action

    frame_start = int(action.frame_range[0])
    frame_end   = int(action.frame_range[1])

    baked: dict = {}

    for frame in range(frame_start, frame_end + 1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_rig  = rig.evaluated_get(depsgraph)

        for mesh_obj in face_meshes:
            if mesh_obj.data.shape_keys is None:
                continue
            sk_blocks = mesh_obj.data.shape_keys.key_blocks
            if len(sk_blocks) <= 1:
                continue  # only basis

            obj_entry = baked.setdefault(mesh_obj.name, {})
            for sk in sk_blocks:
                if sk.name == 'Basis' or not sk.name.startswith('FACE_'):
                    continue

                parsed = _parse_face_sk_name(sk.name)
                if parsed is None:
                    continue
                bone_name, suffix, idx, _direction = parsed
                extreme = float(mesh_obj.data.get(f'{_MESH_PROP_PREFIX}{sk.name}', 0.0))

                eval_pbone = eval_rig.pose.bones.get(bone_name)
                if eval_pbone is None or abs(extreme) < 1e-6:
                    sk.value = 0.0
                else:
                    val = _get_bone_attr_val(eval_pbone, suffix, idx)
                    sk.value = max(0.0, min(1.0, val / extreme))

                sk.keyframe_insert(data_path='value', frame=frame)
                obj_entry.setdefault(sk.name, []).append(frame)

    return baked


def cleanup_shape_key_keyframes(face_meshes, baked: dict) -> None:
    """Removes all temporarily set shape key keyframes and resets values to 0.

    Also fully removes the action object from bpy.data.actions so that
    'Key.001Action' etc. are not misinterpreted as body animations and exported
    as FBX on the next run.
    """
    for mesh_obj in face_meshes:
        if mesh_obj.data.shape_keys is None:
            continue
        obj_entry  = baked.get(mesh_obj.name, {})
        sk_blocks  = mesh_obj.data.shape_keys.key_blocks
        anim_data  = mesh_obj.data.shape_keys.animation_data
        if anim_data is None or anim_data.action is None:
            continue
        for sk_name in obj_entry:
            # Reset value -- no visual influence after export
            if sk_name in sk_blocks:
                sk_blocks[sk_name].value = 0.0

        # Fully remove action object (prevents junk exports on next run)
        action_to_remove = anim_data.action
        anim_data.action = None
        bpy.data.actions.remove(action_to_remove)


def export_face_animation(face_anim_dir: str, rig, face_meshes, action) -> None:
    """Exports a FACE- action as a blend-shape FBX.

    Temporarily bakes shape key values as keyframes, exports rig + meshes,
    then removes all temporary keyframes.
    """
    os.makedirs(face_anim_dir, exist_ok=True)
    fbx_path = os.path.join(face_anim_dir, sanitize_filename(action.name) + ".fbx")

    print(f"[seredos_export] Baking shape keys for '{action.name}' ...")
    baked = bake_shape_key_animation(face_meshes, action, rig)

    # Select only meshes -- NOT the rig.
    # With rig, bone curves for DEF-Eyebrow etc. would be baked and played in Unity
    # in addition to blend shape deformation -> double deflection.
    # Blend shape keyframes live on mesh.shape_keys.animation_data (independent of
    # the rig) and export correctly without the rig selected.
    bpy.ops.object.select_all(action='DESELECT')
    for mesh_obj in face_meshes:
        mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = face_meshes[0]

    bpy.ops.export_scene.fbx(
        filepath                        = fbx_path,
        use_selection                   = True,
        bake_anim                       = True,
        bake_anim_use_all_actions       = False,
        bake_anim_step                  = 1.0,
        bake_anim_simplify_factor       = 0.0,
        bake_anim_use_nla_strips        = False,
        bake_anim_force_startend_keying = True,
        **FBX_SETTINGS,
    )
    print(f"[seredos_export] Face animation -> {fbx_path}")

    cleanup_shape_key_keyframes(face_meshes, baked)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    blend_filepath = BLEND_FILE_PATH or bpy.data.filepath
    if not blend_filepath:
        print("ERROR: Blend file must be saved before exporting.")
        return

    # Find rig
    rig = None
    if RIG_NAME:
        rig = bpy.data.objects.get(RIG_NAME)
        if not rig:
            print(f"ERROR: Rig '{RIG_NAME}' not found.")
            return
    else:
        active = bpy.context.active_object
        if active and active.type == 'ARMATURE':
            rig = active
        else:
            for obj in bpy.data.objects:
                if obj.type != 'ARMATURE' or not obj.pose:
                    continue
                bones = obj.pose.bones
                if any(b.name.startswith('DEF-') for b in bones) and any(b.name.startswith('ORG-') for b in bones):
                    rig = obj
                    break
        if not rig:
            print("ERROR: No rig found. Set RIG_NAME or make an armature active.")
            return

    print(f"[seredos_export] Rig: {rig.name}")

    model_dir, anim_dir, face_anim_dir, fbx_path = get_export_paths(blend_filepath)
    items_dir = get_item_export_path(blend_filepath)
    os.makedirs(model_dir, exist_ok=True)

    items   = find_exportable_items(rig)
    objects = collect_character_objects(rig, items)

    # Temporarily unhide objects (FBX exporter ignores hidden objects)
    was_hidden = {}
    for obj in objects:
        was_hidden[obj.name] = obj.hide_get()
        if obj.hide_get():
            obj.hide_set(False)

    prev_mode = switch_to_object_mode()
    try:
        export_model(fbx_path, objects)
        print(f"[seredos_export] Model exported: {fbx_path}")

        item_count = export_items(items_dir, items)
        if item_count:
            print(f"[seredos_export] {item_count} item(s) exported -> {items_dir}")

        body_count, face_count = export_animations(anim_dir, face_anim_dir, rig)
        print(f"[seredos_export] {body_count} body animation(s) -> {anim_dir}")
        if face_count:
            print(f"[seredos_export] {face_count} face animation(s) -> {face_anim_dir}")

    except Exception as e:
        import traceback
        print(f"[seredos_export] Export failed: {e}")
        traceback.print_exc()
    finally:
        restore_mode(prev_mode)
        for obj in objects:
            if was_hidden.get(obj.name):
                obj.hide_set(True)

    print("[seredos_export] Export complete.")


run()

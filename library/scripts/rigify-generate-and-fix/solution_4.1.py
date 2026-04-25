import bpy
import math
import mathutils
from mathutils import Vector

# ── Parameters ────────────────────────────────────────────────────────────────
METARIG_NAME     = "metarig"       # Name of metarig object in scene
RIG_NAME         = "RIG-Character" # Expected generated rig name (fallback if not linked)
ELBOW_DISTANCE   = 0.5             # IK pole offset for arms (Blender units)
KNEE_DISTANCE    = 0.5             # IK pole offset for legs (Blender units)
EYE_FORWARD_DIST = 0.35            # Eye control forward offset from eye bone head

BROW_OUTER_R  = Vector((-0.0606, -0.0149, 1.6516))
BROW_INNER_R  = Vector((-0.0281, -0.0149, 1.6671))
BROW_INNER_L  = Vector(( 0.0281, -0.0149, 1.6671))
BROW_OUTER_L  = Vector(( 0.0606, -0.0149, 1.6516))
BROW_CENTER   = Vector(( 0.0,    -0.0149, 1.6637))

# USAGE:
# METARIG_NAME  - exact name of the metarig object (default "metarig" matches Rigify default)
# RIG_NAME      - used as fallback if no new armature is detected after generate
# ELBOW/KNEE_DISTANCE - Blender unit offset for IK pole targets; adjust for character scale
# EYE_FORWARD_DIST    - how far forward (Y axis) eye ctrl bones are placed from eye bone head
# BROW_*              - world-space positions for eyebrow control bones; adjust per character


def natural_pole_dir(eb, first_n, tip_n):
    b0 = eb.get(first_n); b2 = eb.get(tip_n)
    if not (b0 and b2): return None
    arm_vec   = (b2.head - b0.head).normalized()
    joint_vec = b0.tail - b0.head
    perp      = joint_vec - arm_vec * joint_vec.dot(arm_vec)
    limb_len  = (b2.head - b0.head).length
    if perp.length < 0.02 * limb_len: return None
    return perp.normalized()


def _copy_rna_params(src, dst, attrs):
    if not (src and dst):
        return
    for attr in attrs:
        if hasattr(src, attr) and hasattr(dst, attr):
            try:
                setattr(dst, attr, getattr(src, attr))
            except Exception:
                pass


def configure_hand_finger_rigify(metarig_obj):
    if not metarig_obj or metarig_obj.type != "ARMATURE" or not metarig_obj.pose:
        return []

    changed = []
    for side in ("L", "R"):
        src = metarig_obj.pose.bones.get(f"IndexFinger_01_{side}")
        if not src:
            continue
        for target_name in (f"MiddleFinger_01_{side}", f"PinkyFinger_01_{side}"):
            target = metarig_obj.pose.bones.get(target_name)
            if not target:
                continue
            if target.rigify_type != "limbs.super_finger":
                target.rigify_type = "limbs.super_finger"
                changed.append(target_name)
            _copy_rna_params(
                getattr(src, "rigify_parameters", None),
                getattr(target, "rigify_parameters", None),
                ("primary_rotation_axis", "bbones", "make_extra_ik_control"),
            )
    return changed


def run():
    metarig = bpy.data.objects.get(METARIG_NAME)
    if metarig is None:
        print(f"ERROR: Metarig '{METARIG_NAME}' not found in scene.")
        return

    bpy.context.view_layer.objects.active = metarig

    # Must be in POSE mode to configure finger rigify_type and to call rigify_generate
    bpy.ops.object.mode_set(mode='POSE')

    changed_finger_roots = configure_hand_finger_rigify(metarig)

    # Snapshot all armatures before generate so we can identify the new one
    existing_armatures = {obj.name for obj in bpy.data.objects if obj.type == 'ARMATURE'}

    bpy.ops.pose.rigify_generate()

    # Find newly created armature object
    new_armatures = [
        obj for obj in bpy.data.objects
        if obj.type == 'ARMATURE' and obj.name not in existing_armatures
    ]
    if new_armatures:
        rig = new_armatures[0]
    else:
        # No new object: Rigify updated an existing rig
        rig = bpy.data.objects.get(RIG_NAME)

    if rig is None:
        print("ERROR: No generated rig found after rigify_generate().")
        return

    print(f"Rig found: '{rig.name}'")
    bpy.context.view_layer.objects.active = rig

    # ── EDIT MODE ─────────────────────────────────────────────────────────────
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones

    # Remove unwanted ORG bones
    for unwanted in ("ORG-Eyebrows", "ORG-Eyes", "ORG-eyebrow_anchor.R"):
        if unwanted in eb: eb.remove(eb[unwanted])

    # Arms
    for org_n, tip_n, ctrl_n, mch_n in [
        ("ORG-upper_arm.L","ORG-hand.L","upper_arm_ik_target.L","MCH-upper_arm_ik_target.parent.L"),
        ("ORG-upper_arm.R","ORG-hand.R","upper_arm_ik_target.R","MCH-upper_arm_ik_target.parent.R"),
    ]:
        d = natural_pole_dir(eb, org_n, tip_n) or mathutils.Vector((0, 1, 0))
        org = eb.get(org_n); ctrl = eb.get(ctrl_n); mch = eb.get(mch_n)
        if not (org and ctrl and mch): continue
        h = org.tail + d * ELBOW_DISTANCE; t = h + d * 0.05
        for b in (ctrl, mch): b.head = h.copy(); b.tail = t.copy(); b.roll = 0

    # Legs
    for org_n, ctrl_n, mch_n in [
        ("ORG-thigh.L","thigh_ik_target.L","MCH-thigh_ik_target.parent.L"),
        ("ORG-thigh.R","thigh_ik_target.R","MCH-thigh_ik_target.parent.R"),
    ]:
        d = mathutils.Vector((0, -1, 0))
        org = eb.get(org_n); ctrl = eb.get(ctrl_n); mch = eb.get(mch_n)
        if not (org and ctrl and mch): continue
        h = org.tail + d * KNEE_DISTANCE; t = h + d * 0.05
        for b in (ctrl, mch): b.head = h.copy(); b.tail = t.copy(); b.roll = 0

    # Eye Target Bones
    bL = eb.get("Eye_L"); bR = eb.get("Eye_R")
    if bL and bR:
        mw  = rig.matrix_world; fwd = mathutils.Vector((0, -EYE_FORWARD_DIST, 0))
        tL  = mw @ bL.head.copy() + fwd; tR = mw @ bR.head.copy() + fwd; tM = (tL + tR) / 2
        for n in ["eye_ctrl.L", "eye_ctrl.R", "eyes_ctrl"]:
            if n in eb: eb.remove(eb[n])
        def mb(name, head, td):
            b = eb.new(name); b.head = head.copy()
            b.tail = head + mathutils.Vector(td) * 0.03
            b.roll = 0; b.use_deform = False; return b
        bEL = mb("eye_ctrl.L", tL, (0, 0, -1))
        bER = mb("eye_ctrl.R", tR, (0, 0, -1))
        bEM = mb("eyes_ctrl",  tM, (0, 0,  1))
        bEL.parent = bEM; bEL.use_connect = False
        bER.parent = bEM; bER.use_connect = False
        bHead = eb.get("head")
        if bHead: bEM.parent = bHead; bEM.use_connect = False

    # ── Eyebrow Ctrl Bones (3-point) ──────────────────────────────────────────
    bHeadBone = eb.get("head")
    up = mathutils.Vector((0, 0, 1))
    for old_n in ("eyebrow_ctrl.L","eyebrow_ctrl.R"):
        if old_n in eb: eb.remove(eb[old_n])

    for ctrl_n, pos in [
        ("eyebrow_ctrl.R",      BROW_OUTER_R),
        ("eyebrow_ctrl_center", BROW_CENTER),
        ("eyebrow_ctrl.L",      BROW_OUTER_L),
    ]:
        if ctrl_n in eb: eb.remove(eb[ctrl_n])
        cb = eb.new(ctrl_n)
        cb.head = pos.copy(); cb.tail = pos + up * 0.012
        cb.roll = 0; cb.use_deform = False
        if bHeadBone: cb.parent = bHeadBone; cb.use_connect = False

    # ── Jaw DEF Bone ─────────────────────────────────────────────────────────
    org_jaw = eb.get("ORG-jaw")
    if org_jaw:
        if "DEF-jaw" in eb: eb.remove(eb["DEF-jaw"])
        dj = eb.new("DEF-jaw")
        dj.head = org_jaw.head.copy(); dj.tail = org_jaw.tail.copy()
        dj.roll = org_jaw.roll; dj.use_deform = True
        dj.parent = org_jaw; dj.use_connect = False

    # ── Eyebrow DEF Bones ─────────────────────────────────────────────────────
    for org_n, def_n, dh, dt in [
        ("ORG-Eyebrow_R", "DEF-Eyebrow_R", BROW_CENTER, BROW_OUTER_R),
        ("ORG-Eyebrow_L", "DEF-Eyebrow_L", BROW_CENTER, BROW_OUTER_L),
    ]:
        org = eb.get(org_n)
        if not org: continue
        if def_n in eb: eb.remove(eb[def_n])
        db = eb.new(def_n)
        db.head = dh.copy(); db.tail = dt.copy()
        db.roll = 0; db.use_deform = True
        db.parent = org; db.use_connect = False

    # ── DEF Hierarchy ─────────────────────────────────────────────────────────
    DEF_PARENTS = {
        "DEF-thigh.L":           "DEF-spine",
        "DEF-thigh.R":           "DEF-spine",
        "DEF-shoulder.L":        "DEF-spine.003",
        "DEF-shoulder.R":        "DEF-spine.003",
        "DEF-upper_arm.L":       "DEF-shoulder.L",
        "DEF-upper_arm.R":       "DEF-shoulder.R",
        "DEF-RingFinger_01_L":   "DEF-hand.L",
        "DEF-IndexFinger_01_L":  "DEF-hand.L",
        "DEF-MiddleFinger_01_L": "DEF-hand.L",
        "DEF-PinkyFinger_01_L":  "DEF-hand.L",
        "DEF-Thumb_01_L":        "DEF-hand.L",
        "DEF-RingFinger_01_R":   "DEF-hand.R",
        "DEF-IndexFinger_01_R":  "DEF-hand.R",
        "DEF-MiddleFinger_01_R": "DEF-hand.R",
        "DEF-PinkyFinger_01_R":  "DEF-hand.R",
        "DEF-Thumb_01_R":        "DEF-hand.R",
        "DEF-jaw":               "DEF-spine.006",
        "DEF-Eye_L":             "DEF-spine.006",
        "DEF-Eye_R":             "DEF-spine.006",
        "DEF-Eyebrow_L":         "DEF-spine.006",
        "DEF-Eyebrow_R":         "DEF-spine.006",
    }
    for bone_n, parent_n in DEF_PARENTS.items():
        bone = eb.get(bone_n); parent = eb.get(parent_n)
        if bone and parent:
            bone.parent = parent; bone.use_connect = False

    # ── Disable split DEF bones ───────────────────────────────────────────────
    for bn in ["DEF-upper_arm.L.001","DEF-upper_arm.R.001",
               "DEF-forearm.L.001",  "DEF-forearm.R.001",
               "DEF-thigh.L.001",    "DEF-thigh.R.001",
               "DEF-shin.L.001",     "DEF-shin.R.001"]:
        b = eb.get(bn)
        if b: b.use_deform = False

    # ── Rename spine bones ────────────────────────────────────────────────────
    for old_n, new_n in {"DEF-spine.004": "DEF-neck", "DEF-spine.006": "DEF-head"}.items():
        if old_n in eb: eb[old_n].name = new_n

    # ── POSE MODE ─────────────────────────────────────────────────────────────
    bpy.ops.object.mode_set(mode="POSE")

    for bn in ["upper_arm_parent.L","upper_arm_parent.R","thigh_parent.L","thigh_parent.R"]:
        pb = rig.pose.bones.get(bn)
        if pb and "pole_vector" in pb: pb["pole_vector"] = True

    # ── Knee IK pole angle ────────────────────────────────────────────────────
    def find_best_pole_angle(side):
        shin_ik  = rig.pose.bones.get(f"MCH-shin_ik.{side}")
        def_shin = rig.pose.bones.get(f"DEF-shin.{side}")
        if not shin_ik or not def_shin:
            return None
        pole_con = next((c for c in shin_ik.constraints if c.type == "IK" and c.pole_subtarget), None)
        if not pole_con:
            return None
        rest_q = (rig.matrix_world @ def_shin.bone.matrix_local).to_quaternion()
        def measure(deg):
            pole_con.pole_angle = math.radians(deg)
            bpy.context.view_layer.update()
            posed_q = (rig.matrix_world @ def_shin.matrix).to_quaternion()
            return math.degrees((posed_q @ rest_q.inverted()).angle)
        best_deg, best_diff = -90.0, 999.0
        for deg in range(-180, 181, 20):
            d = measure(deg)
            if d < best_diff:
                best_diff, best_deg = d, float(deg)
        for delta in [x * 2 for x in range(-10, 11)]:
            d = measure(best_deg + delta)
            if d < best_diff:
                best_diff, best_deg = d, best_deg + delta
        for delta in [x * 0.2 for x in range(-10, 11)]:
            d = measure(best_deg + delta)
            if d < best_diff:
                best_diff, best_deg = d, best_deg + delta
        pole_con.pole_angle = math.radians(best_deg)
        bpy.context.view_layer.update()
        return best_deg, best_diff

    for side in ("L", "R"):
        result = find_best_pole_angle(side)
        if result:
            print(f"  Knee pole angle {side}: {result[0]:.1f}° (rest_diff={result[1]:.3f}°)")

    for cn, tn in [("Eye_L","eye_ctrl.L"),("Eye_R","eye_ctrl.R")]:
        pb = rig.pose.bones.get(cn)
        if not pb: continue
        for c in list(pb.constraints):
            if c.type == "DAMPED_TRACK": pb.constraints.remove(c)
        con = pb.constraints.new("DAMPED_TRACK")
        con.target = rig; con.subtarget = tn; con.track_axis = "TRACK_Y"

    def _make_wgt(name, verts, edges):
        old = bpy.data.objects.get(name)
        if old: bpy.data.objects.remove(old, do_unlink=True)
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        col = next((c for c in bpy.data.collections if "WGTS" in c.name), None)
        if col: col.objects.link(obj)
        else: bpy.context.scene.collection.objects.link(obj)
        return obj

    _EYE_VERTS = [
        (0.0,0.5,0.0),(-0.1294,0.483,0.0),(-0.25,0.433,0.0),(-0.3536,0.3536,0.0),
        (-0.433,0.25,0.0),(-0.483,0.1294,0.0),(-0.5,0.0,0.0),(-0.483,-0.1294,0.0),
        (-0.433,-0.25,0.0),(-0.3536,-0.3536,0.0),(-0.25,-0.433,0.0),(-0.1294,-0.483,0.0),
        (-0.0,-0.5,0.0),(0.1294,-0.483,0.0),(0.25,-0.433,0.0),(0.3536,-0.3536,0.0),
        (0.433,-0.25,0.0),(0.483,-0.1294,0.0),(0.5,-0.0,0.0),(0.483,0.1294,0.0),
        (0.433,0.25,0.0),(0.3536,0.3536,0.0),(0.25,0.433,0.0),(0.1294,0.483,0.0),
    ]
    _EYE_EDGES = [(i, (i+1) % 24) for i in range(24)]

    wgt_eye_l = _make_wgt(f"WGT-{rig.name}_eye_ctrl.L", _EYE_VERTS, _EYE_EDGES)
    wgt_eye_r = _make_wgt(f"WGT-{rig.name}_eye_ctrl.R", _EYE_VERTS, _EYE_EDGES)

    for bn, wgt in (("eye_ctrl.L", wgt_eye_l), ("eye_ctrl.R", wgt_eye_r)):
        pb = rig.pose.bones.get(bn)
        if pb: pb.custom_shape = wgt

    for bn in ["Eye_L","Eye_R"]:
        pb = rig.pose.bones.get(bn)
        if pb: pb.bone.hide = True

    # ── Eyebrow Constraints ───────────────────────────────────────────────────
    for ctrl_n in ("eyebrow_ctrl.R", "eyebrow_ctrl_center", "eyebrow_ctrl.L"):
        pb = rig.pose.bones.get(ctrl_n)
        if not pb: continue
        pb.lock_location = (True, False, True)

    for org_n, loc_n, track_n in [
        ("ORG-Eyebrow_R", "eyebrow_ctrl_center", "eyebrow_ctrl.R"),
        ("ORG-Eyebrow_L", "eyebrow_ctrl_center", "eyebrow_ctrl.L"),
    ]:
        org_pb = rig.pose.bones.get(org_n)
        if not org_pb: continue
        for c in list(org_pb.constraints):
            if c.type in ("COPY_TRANSFORMS","COPY_LOCATION","DAMPED_TRACK"):
                org_pb.constraints.remove(c)
        cl = org_pb.constraints.new("COPY_LOCATION")
        cl.target = rig; cl.subtarget = loc_n
        dt = org_pb.constraints.new("DAMPED_TRACK")
        dt.target = rig; dt.subtarget = track_n; dt.track_axis = "TRACK_Y"

    # ── DEF → ORG COPY_TRANSFORMS ─────────────────────────────────────────────
    for side in ("L", "R"):
        for def_n, org_n in [
            (f"DEF-Eye_{side}",     f"ORG-Eye_{side}"),
            (f"DEF-Eyebrow_{side}", f"ORG-Eyebrow_{side}"),
        ]:
            def_pb = rig.pose.bones.get(def_n)
            if not def_pb or not rig.pose.bones.get(org_n): continue
            for c in list(def_pb.constraints):
                if c.type == "COPY_TRANSFORMS": def_pb.constraints.remove(c)
            ct = def_pb.constraints.new("COPY_TRANSFORMS")
            ct.target = rig; ct.subtarget = org_n; ct.influence = 1.0

    bpy.context.view_layer.update()

    if changed_finger_roots:
        print(f"Finger Rigify setup applied: {', '.join(changed_finger_roots)}")
    print(f"rigify-generate-and-fix complete: '{rig.name}'")


run()

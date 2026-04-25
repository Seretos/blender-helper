import bpy

# ── Parameters ────────────────────────────────────────────────────────────────
METARIG_NAME = ""   # Auto-detect if empty (armature with rigify_target_rig property, META-* name, or "metarig")
RIG_NAME     = ""   # Auto-detect if empty (armature with both DEF- and ORG- spine pose bones)

# USAGE:
# METARIG_NAME - exact name of the metarig object; leave empty to auto-detect
# RIG_NAME     - exact name of the generated rig; leave empty to auto-detect

# ── Hardcoded reference data (from rigify_fix.py) ─────────────────────────────
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

SPLIT_DEF_TO_DISABLE = [
    "DEF-upper_arm.L.001", "DEF-upper_arm.R.001",
    "DEF-forearm.L.001",   "DEF-forearm.R.001",
    "DEF-thigh.L.001",     "DEF-thigh.R.001",
    "DEF-shin.L.001",      "DEF-shin.R.001",
]

FACE_DEF_TO_ORG = [
    ("DEF-Eye_L",     "ORG-Eye_L"),
    ("DEF-Eye_R",     "ORG-Eye_R"),
    ("DEF-Eyebrow_L", "ORG-Eyebrow_L"),
    ("DEF-Eyebrow_R", "ORG-Eyebrow_R"),
]


# ── Detection helpers ──────────────────────────────────────────────────────────

def find_metarig():
    for obj in bpy.data.objects:
        if obj.type != 'ARMATURE': continue
        if obj.data.get("rigify_target_rig") is not None: return obj
        if obj.name.startswith("META-") or obj.name.lower() == "metarig": return obj
    return None


def find_rig():
    for obj in bpy.data.objects:
        if obj.type != 'ARMATURE' or not obj.pose: continue
        bones = obj.pose.bones
        has_def = any(b.name in ("DEF-spine", "DEF-neck", "DEF-head") for b in bones)
        has_org = any(b.name in ("ORG-spine", "ORG-neck", "ORG-head") for b in bones)
        if has_def and has_org: return obj
    return None


# ── Check helpers ──────────────────────────────────────────────────────────────

def has_constraint(rig, bone_name, con_type, subtarget=None):
    pb = rig.pose.bones.get(bone_name)
    if not pb: return False
    for c in pb.constraints:
        if c.type != con_type: continue
        if subtarget and c.subtarget != subtarget: continue
        return True
    return False


def bone_parent_name(rig, bone_name):
    b = rig.data.bones.get(bone_name)
    if not b or not b.parent: return None
    return b.parent.name


def run():
    metarig = bpy.data.objects.get(METARIG_NAME) if METARIG_NAME else find_metarig()
    rig     = bpy.data.objects.get(RIG_NAME)     if RIG_NAME     else find_rig()

    meta_name = metarig.name if metarig else "not found"
    rig_name  = rig.name     if rig     else "not found"

    sep = "═" * 53
    print(f"\n{sep}")
    print(f"  RIGIFY SETUP ANALYSIS")
    print(f"  Metarig: {meta_name} | Rig: {rig_name}")
    print(f"{sep}\n")

    # ── Pre-generation checks ──────────────────────────────────────────────────
    print("PRE-GENERATION (metarig)")
    print("─────────────────────────")
    if metarig:
        print(f"  Metarig present         : ✓ {metarig.name}")
        for side in ("L", "R"):
            for finger in ("MiddleFinger_01", "PinkyFinger_01"):
                bn = f"{finger}_{side}"
                pb = metarig.pose.bones.get(bn) if metarig.pose else None
                rt = pb.rigify_type if pb else "N/A"
                ok = rt == "limbs.super_finger"
                print(f"  Finger {bn:<22}: {'✓' if ok else '✗'} {rt}")
    else:
        print("  Metarig present         : ✗ not found")
    print()

    print("POST-GENERATION (rig)")
    print("──────────────────────")
    print(f"  Generated rig present   : {'✓ ' + rig.name if rig else '✗ not found'}")
    print()

    if not rig:
        print("  (Cannot check fix steps — no rig found)")
        return

    bones = rig.data.bones
    applied_count = 0
    results = []

    def check(n, label, ok, detail=""):
        nonlocal applied_count
        if ok: applied_count += 1
        results.append((n, label, ok, detail))

    # Check 1 — Unwanted bones removed
    unwanted = [b for b in ("ORG-Eyebrows","ORG-Eyes","ORG-eyebrow_anchor.R") if b in bones]
    check(1, "Unwanted bones removed", not unwanted,
          f"still present: {', '.join(unwanted)}" if unwanted else "")

    # Check 2 — IK pole targets repositioned
    pole_bones = ["upper_arm_ik_target.L","upper_arm_ik_target.R","thigh_ik_target.L","thigh_ik_target.R"]
    at_origin = [bn for bn in pole_bones if bn in bones and
                 (rig.matrix_world @ bones[bn].head_local).length < 0.001]
    check(2, "IK pole targets repositioned", not at_origin,
          f"still at origin: {', '.join(at_origin)}" if at_origin else "")

    # Check 3 — Eye control bones created
    eye_ctrl_bones = ["eye_ctrl.L","eye_ctrl.R","eyes_ctrl"]
    missing_eye = [b for b in eye_ctrl_bones if b not in bones]
    check(3, "Eye control bones created", not missing_eye,
          f"missing: {', '.join(missing_eye)}" if missing_eye else "")

    # Check 4 — Eye control parent hierarchy
    hier_ok = (
        bone_parent_name(rig, "eye_ctrl.L") == "eyes_ctrl" and
        bone_parent_name(rig, "eye_ctrl.R") == "eyes_ctrl" and
        bone_parent_name(rig, "eyes_ctrl")  == "head"
    )
    check(4, "Eye control parent hierarchy", hier_ok)

    # Check 5 — Eye DAMPED_TRACK constraints
    eye_dt_ok = (
        has_constraint(rig, "Eye_L", "DAMPED_TRACK", "eye_ctrl.L") and
        has_constraint(rig, "Eye_R", "DAMPED_TRACK", "eye_ctrl.R")
    )
    check(5, "Eye DAMPED_TRACK constraints", eye_dt_ok)

    # Check 6 — Eye control custom shapes
    shapes_ok = all(
        rig.pose.bones.get(b) and rig.pose.bones[b].custom_shape is not None
        for b in ["eye_ctrl.L","eye_ctrl.R","eyes_ctrl"]
        if b in bones
    )
    check(6, "Eye control custom shapes", shapes_ok)

    # Check 7 — Eyebrow control bones
    brow_bones = ["eyebrow_ctrl.R","eyebrow_ctrl_center","eyebrow_ctrl.L"]
    missing_brow = [b for b in brow_bones if b not in bones]
    check(7, "Eyebrow control bones created", not missing_brow,
          f"missing: {', '.join(missing_brow)}" if missing_brow else "")

    # Check 8 — Eyebrow parent + axis lock
    brow_ok = True
    brow_detail = []
    for bn in ["eyebrow_ctrl.R","eyebrow_ctrl_center","eyebrow_ctrl.L"]:
        pb = rig.pose.bones.get(bn)
        if not pb: brow_ok = False; continue
        if bone_parent_name(rig, bn) != "head":
            brow_ok = False; brow_detail.append(f"{bn}: parent={bone_parent_name(rig, bn)}")
        if tuple(pb.lock_location) != (True, False, True):
            brow_ok = False; brow_detail.append(f"{bn}: lock={tuple(pb.lock_location)}")
    check(8, "Eyebrow parent + axis lock", brow_ok, "; ".join(brow_detail))

    # Check 9 — Eyebrow ORG constraints
    brow_con_ok = (
        has_constraint(rig, "ORG-Eyebrow_L", "COPY_LOCATION") and
        has_constraint(rig, "ORG-Eyebrow_L", "DAMPED_TRACK", "eyebrow_ctrl.L") and
        has_constraint(rig, "ORG-Eyebrow_R", "COPY_LOCATION") and
        has_constraint(rig, "ORG-Eyebrow_R", "DAMPED_TRACK", "eyebrow_ctrl.R")
    )
    check(9, "Eyebrow ORG constraints", brow_con_ok)

    # Check 10 — DEF-Eyebrow bones
    def_brow_ok = (
        "DEF-Eyebrow_L" in bones and bone_parent_name(rig, "DEF-Eyebrow_L") == "ORG-Eyebrow_L" and
        "DEF-Eyebrow_R" in bones and bone_parent_name(rig, "DEF-Eyebrow_R") == "ORG-Eyebrow_R"
    )
    check(10, "DEF-Eyebrow bones with correct parents", def_brow_ok)

    # Check 11 — Full DEF hierarchy
    # DEF-spine.006 may have been renamed to DEF-head
    PARENTS_RESOLVED = {}
    for bn, pn in DEF_PARENTS.items():
        resolved_bn = "DEF-head" if bn == "DEF-spine.006" else bn
        resolved_pn = "DEF-head" if pn == "DEF-spine.006" else pn
        PARENTS_RESOLVED[resolved_bn] = resolved_pn

    wrong_parents = []
    for bn, expected_pn in PARENTS_RESOLVED.items():
        if bn not in bones: continue
        actual_pn = bone_parent_name(rig, bn)
        if actual_pn != expected_pn:
            wrong_parents.append(f"{bn}: expected {expected_pn}, found {actual_pn}")
    checked_count = sum(1 for bn in PARENTS_RESOLVED if bn in bones)
    wrong_count   = len(wrong_parents)
    hier_detail   = f"{checked_count - wrong_count}/{checked_count} correct"
    if wrong_parents:
        hier_detail += "\n" + "\n".join(f"       ✗ {w}" for w in wrong_parents[:5])
        if len(wrong_parents) > 5: hier_detail += f"\n       ... and {len(wrong_parents)-5} more"
    check(11, f"Full DEF hierarchy ({checked_count} pairs)", wrong_count == 0, hier_detail)

    # Check 12 — Split DEF bones disabled
    wrong_deform = [
        bn for bn in SPLIT_DEF_TO_DISABLE
        if bn in bones and bones[bn].use_deform
    ]
    present_count = sum(1 for bn in SPLIT_DEF_TO_DISABLE if bn in bones)
    check(12, "Split DEF bones disabled", not wrong_deform,
          f"still enabled: {', '.join(wrong_deform)}" if wrong_deform else f"{present_count}/{len(SPLIT_DEF_TO_DISABLE)} present")

    # ── Report ─────────────────────────────────────────────────────────────────
    status = "READY FOR EXPORT" if applied_count == 12 else "INCOMPLETE"
    print(f"SUMMARY: {applied_count}/12 steps applied — {status}\n")
    print("FIX STEPS")
    print("──────────")
    for n, label, ok, detail in results:
        icon = "✓" if ok else "✗"
        state = "APPLIED" if ok else "NOT_APPLIED"
        line = f"  [{n:>2}] {label:<40}: {icon} {state}"
        if detail and not ok:
            line += f" ({detail})" if "\n" not in detail else ""
        print(line)
        if detail and "\n" in detail and not ok:
            print(detail)
    print()


run()

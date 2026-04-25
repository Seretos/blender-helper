import bpy
import os

# ── Parameters ────────────────────────────────────────────────────────────────
# No user parameters — reads entire active scene

# USAGE:
# No parameters needed. Run to get a full scene overview.
# Output is structured text for the skill to parse before acting.


# ── Helpers ───────────────────────────────────────────────────────────────────

def classify_armature(obj):
    """Return 'metarig', 'rig', or 'source'."""
    if obj.data.get("rigify_target_rig") is not None:
        return "metarig"
    if obj.name.startswith("META-") or obj.name.lower() == "metarig":
        return "metarig"
    if obj.pose:
        bones = obj.pose.bones
        has_def = any(b.name in ("DEF-spine", "DEF-spine.001", "DEF-neck", "DEF-head") for b in bones)
        has_org = any(b.name in ("ORG-spine", "ORG-spine.001", "ORG-neck", "ORG-head") for b in bones)
        if has_def and has_org:
            return "rig"
    return "source"


def classify_action(name):
    if name.startswith("FACE-"):
        return "face"
    if name.startswith("Armature|Take 001|BaseLayer"):
        return "blacklisted"
    return "body"


def check_copy_transforms(rig, def_bone, org_bone):
    pb = rig.pose.bones.get(def_bone)
    if not pb:
        return False
    return any(
        c.type == 'COPY_TRANSFORMS' and c.target == rig and c.subtarget == org_bone
        for c in pb.constraints
    )


def run():
    scene = bpy.context.scene
    filepath = bpy.data.filepath
    basename = os.path.basename(filepath) if filepath else "unsaved"

    # ── Collect ───────────────────────────────────────────────────────────────
    all_objs = list(bpy.data.objects)
    armatures = [o for o in all_objs if o.type == 'ARMATURE']
    meshes    = [o for o in all_objs if o.type == 'MESH']
    empties   = [o for o in all_objs if o.type == 'EMPTY']

    classified = {obj: classify_armature(obj) for obj in armatures}
    metarigs = [o for o, t in classified.items() if t == "metarig"]
    rigs     = [o for o, t in classified.items() if t == "rig"]
    sources  = [o for o, t in classified.items() if t == "source"]

    metarig = metarigs[0] if metarigs else None
    rig     = rigs[0]     if rigs     else None

    # ── Mesh binding counts ───────────────────────────────────────────────────
    mesh_rig, mesh_src, mesh_unbound = 0, 0, 0
    for m in meshes:
        arm_mod = next((mod for mod in m.modifiers if mod.type == 'ARMATURE'), None)
        if not arm_mod or not arm_mod.object:
            mesh_unbound += 1
        elif arm_mod.object in rigs:
            mesh_rig += 1
        elif arm_mod.object in sources:
            mesh_src += 1
        else:
            mesh_unbound += 1

    # ── Actions ───────────────────────────────────────────────────────────────
    body_actions       = [a for a in bpy.data.actions if classify_action(a.name) == "body"]
    face_actions       = [a for a in bpy.data.actions if classify_action(a.name) == "face"]
    blacklisted_actions = [a for a in bpy.data.actions if classify_action(a.name) == "blacklisted"]

    # ── SLOT items ────────────────────────────────────────────────────────────
    slot_items = [o for o in empties if o.name.startswith("SLOT-")]

    # ── Print ─────────────────────────────────────────────────────────────────
    sep = "═" * 51
    print(f"\n{sep}")
    print(f"  SCENE OVERVIEW — {scene.name} | {basename}")
    print(f"{sep}\n")

    print("SCENE STATE FLAGS")
    print("─────────────────")
    print(f"  Metarig         : {'✓ ' + metarig.name if metarig else '✗ not found'}")
    print(f"  Generated Rig   : {'✓ ' + rig.name if rig else '✗ not found'}")
    src_names = ', '.join(s.name for s in sources)
    print(f"  Source Arms     : {len(sources)}{(' (' + src_names + ')') if sources else ''}")
    print(f"  Meshes (RIG)    : {mesh_rig} / Source: {mesh_src} / Unbound: {mesh_unbound}")
    print(f"  Actions         : {len(body_actions)} body, {len(face_actions)} face, {len(blacklisted_actions)} blacklisted")
    print(f"  Items (SLOT-*)  : {len(slot_items)}\n")

    # ── Metarig ───────────────────────────────────────────────────────────────
    print("METARIG STRUCTURE")
    print("──────────────────")
    if metarig:
        print(f"  Name      : {metarig.name}")
        print(f"  Bones     : {len(metarig.data.bones)}")
        target = metarig.data.get("rigify_target_rig")
        print(f"  Target RIG: {target.name if target else 'not linked'}")
        for b in ["MiddleFinger_01_L","MiddleFinger_01_R","PinkyFinger_01_L","PinkyFinger_01_R",
                  "Eye_L","Eye_R","Eyebrow_L","Eyebrow_R","jaw"]:
            print(f"  {b:<28}: {'✓' if b in metarig.data.bones else '✗'}")
    else:
        print("  (no metarig found)")
    print()

    # ── Generated Rig ─────────────────────────────────────────────────────────
    print("GENERATED RIG")
    print("──────────────")
    if rig:
        bones = rig.data.bones
        print(f"  Name  : {rig.name}")
        print(f"  Bones : {len(bones)} total")
        for prefix in ("DEF-", "ORG-", "MCH-"):
            print(f"    {prefix:<8}: {sum(1 for b in bones if b.name.startswith(prefix))}")
        ctrl = sum(1 for b in bones if not any(b.name.startswith(p) for p in ("DEF-","ORG-","MCH-")))
        print(f"    CTRL    : {ctrl}")
        FACE_PAIRS = [("DEF-Eye_L","ORG-Eye_L"),("DEF-Eye_R","ORG-Eye_R"),
                      ("DEF-Eyebrow_L","ORG-Eyebrow_L"),("DEF-Eyebrow_R","ORG-Eyebrow_R")]
        print("  Face DEF bones:")
        for def_b, org_b in FACE_PAIRS:
            present = def_b in bones
            ct = check_copy_transforms(rig, def_b, org_b) if present else False
            print(f"    {def_b:<22}: {'✓' if present else '✗'} | COPY_TRANSFORMS→{org_b}: {'✓' if ct else '✗'}")
        print("  Control bones:")
        for b in ["eye_ctrl.L","eye_ctrl.R","eyes_ctrl","eyebrow_ctrl.L","eyebrow_ctrl.R","eyebrow_ctrl_center"]:
            print(f"    {b:<24}: {'✓' if b in bones else '✗'}")
    else:
        print("  (no generated rig found)")
    print()

    # ── Source Armatures ──────────────────────────────────────────────────────
    print("SOURCE ARMATURE(S)")
    print("───────────────────")
    if sources:
        for src in sources:
            mc = [c for c in src.children if c.type == 'MESH']
            print(f"  {src.name}: {len(src.data.bones)} bones, {len(mc)} mesh children")
    else:
        print("  (none)")
    print()

    # ── Meshes ────────────────────────────────────────────────────────────────
    print("MESHES")
    print("───────")
    for m in meshes:
        arm_mod = next((mod for mod in m.modifiers if mod.type == 'ARMATURE'), None)
        arm_target = arm_mod.object.name if (arm_mod and arm_mod.object) else "none"
        vg_count = len(m.vertex_groups)
        def_vg   = sum(1 for vg in m.vertex_groups if vg.name.startswith("DEF-"))
        sk_count = 0; face_sk = 0
        if m.data.shape_keys:
            sks = m.data.shape_keys.key_blocks
            sk_count = len(sks)
            face_sk  = sum(1 for sk in sks if sk.name.startswith("FACE_"))
        slot_child = any(e.name.startswith("SLOT-") and m in (e.children or []) for e in empties)
        print(f"  {m.name[:24]:<24} arm={arm_target[:18]:<18} VGs={vg_count}(DEF:{def_vg}) SKs={sk_count}(FACE:{face_sk}) SLOT={'✓' if slot_child else '✗'}")
    print()

    # ── Actions ───────────────────────────────────────────────────────────────
    print("ACTIONS")
    print("────────")
    print(f"  Body ({len(body_actions)}):")
    for a in body_actions[:10]:
        print(f"    {a.name[:40]:<40} frames {int(a.frame_range[0])}–{int(a.frame_range[1])}")
    if len(body_actions) > 10:
        print(f"    ... and {len(body_actions) - 10} more")
    print(f"  Face ({len(face_actions)}):")
    for a in face_actions[:5]:
        print(f"    {a.name}")
    blk = ', '.join(a.name for a in blacklisted_actions) or 'none'
    print(f"  Blacklisted ({len(blacklisted_actions)}): {blk}")
    print()

    # ── Items ─────────────────────────────────────────────────────────────────
    print("ITEMS (SLOT-*)")
    print("───────────────")
    if slot_items:
        for slot in slot_items:
            mc = [c for c in slot.children if c.type == 'MESH']
            vtx = sum(len(m.data.vertices) for m in mc)
            print(f"  {slot.name}: {len(mc)} mesh(es), {vtx} vertices")
    else:
        print("  (none)")
    print()

    # ── Export Readiness ──────────────────────────────────────────────────────
    print("EXPORT READINESS")
    print("─────────────────")
    checks = []

    checks.append((
        metarig is not None and metarig.data.get("rigify_target_rig") is not None,
        "Metarig present and linked to generated RIG"
    ))
    checks.append((rig is not None, "Generated RIG present with DEF/ORG structure"))
    checks.append((
        rig is not None and mesh_src == 0 and mesh_unbound == 0 and len(meshes) > 0,
        "All meshes rebound (armature modifier → RIG)"
    ))
    face_vg_names = {"DEF-Eye_L","DEF-Eye_R","DEF-Eyebrow_L","DEF-Eyebrow_R"}
    all_vg_names  = {vg.name for m in meshes for vg in m.vertex_groups}
    checks.append((face_vg_names.issubset(all_vg_names), "Face VGs present (DEF-Eye_L/R, DEF-Eyebrow_L/R)"))
    checks.append((
        any(
            m.data.shape_keys and any(sk.name.startswith("FACE_") for sk in m.data.shape_keys.key_blocks)
            for m in meshes
        ),
        "Face shape keys exist (FACE_* pattern)"
    ))
    checks.append((len(face_actions) > 0, "FACE- actions present"))
    checks.append((
        all(not any(c.type == 'MESH' for c in src.children) for src in sources) if sources else True,
        "No source armature still has meshes bound"
    ))
    checks.append((bool(filepath), "Blend file saved"))

    blockers = []
    for ok, label in checks:
        print(f"  [{'✓' if ok else '✗'}] {label}")
        if not ok:
            blockers.append(label)
    print()
    if blockers:
        print("  BLOCKERS:")
        for b in blockers:
            print(f"    - {b}")
    else:
        print("  BLOCKERS: none")
    print()


run()

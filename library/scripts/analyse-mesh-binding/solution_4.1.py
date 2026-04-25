import bpy

# ── Parameters ────────────────────────────────────────────────────────────────
RIG_NAME = ""   # Auto-detect if empty (armature with both DEF- and ORG- pose bones)

# USAGE:
# RIG_NAME - exact name of the generated Rigify rig; leave empty to auto-detect.
#            Auto-detect finds the first armature with both DEF-spine and ORG-spine pose bones.

# ── Hardcoded reference data ───────────────────────────────────────────────────
SYNTY_VG_NAMES = {"Eyes", "Eyebrows", "Eyebrow_L", "Eyebrow_R"}
SYNTY_BONE_PATTERNS = {
    "spine", "thigh", "hand", "forearm", "shoulder", "shin",
    "Thumb", "IndexFinger", "MiddleFinger", "PinkyFinger", "RingFinger",
    "Root", "Hips", "UpperArm", "LowerArm", "UpperLeg", "LowerLeg",
}

FACE_DEF_TO_ORG = [
    ("DEF-Eye_L",      "ORG-Eye_L"),
    ("DEF-Eye_R",      "ORG-Eye_R"),
    ("DEF-Eyebrow_L",  "ORG-Eyebrow_L"),
    ("DEF-Eyebrow_R",  "ORG-Eyebrow_R"),
]


def is_synty_vg(name):
    """True if a VG name looks like a pre-rebind Synty bone name."""
    if name.startswith("DEF-"):
        return False
    if name in SYNTY_VG_NAMES:
        return True
    return any(pattern in name for pattern in SYNTY_BONE_PATTERNS)


def find_rig():
    """Auto-detect the generated Rigify rig."""
    for obj in bpy.data.objects:
        if obj.type != 'ARMATURE' or not obj.pose: continue
        bones = obj.pose.bones
        has_def = any(b.name in ("DEF-spine","DEF-neck","DEF-head") for b in bones)
        has_org = any(b.name in ("ORG-spine","ORG-neck","ORG-head") for b in bones)
        if has_def and has_org: return obj
    return None


def check_copy_transforms(rig, def_bone, org_bone):
    pb = rig.pose.bones.get(def_bone)
    if not pb: return False
    return any(
        c.type == 'COPY_TRANSFORMS' and c.target == rig and c.subtarget == org_bone
        for c in pb.constraints
    )


def run():
    rig = bpy.data.objects.get(RIG_NAME) if RIG_NAME else find_rig()
    rig_name = rig.name if rig else "not found"
    rig_bones = set(rig.pose.bones.keys()) if rig else set()

    sep = "═" * 59
    print(f"\n{sep}")
    print(f"  MESH BINDING ANALYSIS")
    print(f"  Rig: {rig_name}")
    print(f"{sep}\n")

    meshes = [o for o in bpy.data.objects if o.type == 'MESH']

    # ── Per-mesh data ──────────────────────────────────────────────────────────
    mesh_data = []
    for m in meshes:
        arm_mod = next((mod for mod in m.modifiers if mod.type == 'ARMATURE'), None)
        arm_target = arm_mod.object if (arm_mod and arm_mod.object) else None
        arm_name   = arm_target.name if arm_target else "none"

        mapped   = []
        unmapped = []
        synty    = []
        for vg in m.vertex_groups:
            if vg.name in rig_bones:
                mapped.append(vg.name)
            else:
                unmapped.append(vg.name)
                if is_synty_vg(vg.name):
                    synty.append(vg.name)

        # Rebind state
        if not arm_target:
            state = "UNBOUND"
        elif rig and arm_target == rig:
            if not unmapped:
                state = "FULL"
            elif not mapped:
                state = "UNBOUND"
            else:
                state = "PARTIAL"
        else:
            state = "UNBOUND"

        mesh_data.append({
            "name": m.name,
            "arm_name": arm_name,
            "arm_target": arm_target,
            "vg_count": len(m.vertex_groups),
            "mapped": mapped,
            "unmapped": unmapped,
            "synty": synty,
            "state": state,
        })

    # ── Print per-mesh table ───────────────────────────────────────────────────
    print("PER-MESH BINDING")
    print("─────────────────")
    header = f"  {'Mesh':<24} {'ArmMod':<20} VGs   Mapped  Unmapped  State"
    print(header)
    print("  " + "─" * (len(header) - 2))
    for d in mesh_data:
        print(f"  {d['name'][:24]:<24} {d['arm_name'][:20]:<20} {d['vg_count']:<5} "
              f"{len(d['mapped']):<7} {len(d['unmapped']):<9} {d['state']}")
    print()

    # ── Unmapped VG details ────────────────────────────────────────────────────
    has_unmapped = any(d['unmapped'] for d in mesh_data)
    if has_unmapped:
        print("UNMAPPED VERTEX GROUPS")
        print("───────────────────────")
        for d in mesh_data:
            if not d['unmapped']: continue
            print(f"  {d['name']} ({len(d['unmapped'])} unmapped):")
            for vg_name in d['unmapped']:
                tag = " [Synty-era]" if is_synty_vg(vg_name) else " [unknown]"
                print(f"    - {vg_name}{tag}")
        print()

    # ── Face binding status ────────────────────────────────────────────────────
    print("FACE BINDING STATUS")
    print("────────────────────")
    all_vg_names = {vg.name for m in meshes for vg in m.vertex_groups}
    for def_b, org_b in FACE_DEF_TO_ORG:
        vg_ok = def_b in all_vg_names
        ct_ok = check_copy_transforms(rig, def_b, org_b) if rig else False
        print(f"  {def_b:<22}: VG {'✓' if vg_ok else '✗'} | COPY_TRANSFORMS→{org_b} {'✓' if ct_ok else '✗'}")
    print()

    # ── Summary ───────────────────────────────────────────────────────────────
    print("SUMMARY")
    print("────────")
    counts = {"FULL": 0, "PARTIAL": 0, "UNBOUND": 0}
    for d in mesh_data: counts[d['state']] += 1
    print(f"  FULL:    {counts['FULL']} mesh(es)")
    print(f"  PARTIAL: {counts['PARTIAL']} mesh(es)")
    print(f"  UNBOUND: {counts['UNBOUND']} mesh(es)")
    print()

    incomplete = counts['PARTIAL'] + counts['UNBOUND'] > 0
    print(f"  Status: {'INCOMPLETE' if incomplete else 'COMPLETE'}")

    needs_rebind = [d['name'] for d in mesh_data if d['state'] in ('UNBOUND','PARTIAL')]
    missing_ct = [f"{def_b}/{org_b}" for def_b, org_b in FACE_DEF_TO_ORG
                  if rig and not check_copy_transforms(rig, def_b, org_b)]

    if needs_rebind or missing_ct:
        print("  Next steps:")
        if needs_rebind:
            print(f"    1. Run rebind-to-rig on: {', '.join(needs_rebind)}")
        if missing_ct:
            step = 2 if needs_rebind else 1
            print(f"    {step}. Fix face constraints: {', '.join(missing_ct)}")
    print()


run()

#!/usr/bin/env python3
"""validate_rbxmx.py — structural checks on generated .rbxmx files.

    python3 tools/validate_rbxmx.py models/block/*.rbxmx
"""
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter

MAT_OK = {256, 272, 288, 512, 528, 784, 788, 800, 816, 820, 832, 836, 848, 864, 880, 896,
          912, 1040, 1056, 1072, 1088, 1280, 1284, 1296, 1312, 1344, 1360, 1376, 1568}


VARIANT_BASE = {}


def _load_variants():
    sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(
        __import__("os").path.abspath(__file__))))
    from blockgen import style, rbxlib
    for name, (base, _tile) in style.VARIANTS.items():
        VARIANT_BASE[name] = rbxlib.MAT[base]


def check(path):
    if not VARIANT_BASE:
        _load_variants()
    problems = []
    tree = ET.parse(path)                      # raises if not well-formed
    root = tree.getroot()
    items = list(root.iter("Item"))
    refs = [i.get("referent") for i in items]
    if len(refs) != len(set(refs)):
        problems.append("duplicate referents")
    refset = set(refs)
    classes = Counter(i.get("class") for i in items)
    n_parts = 0
    variants_used = Counter()
    ymin, ymax = 1e9, -1e9
    xmin = zmin = 1e9
    xmax = zmax = -1e9
    for it in items:
        props = it.find("Properties")
        if props is None:
            problems.append("item without Properties: " + it.get("class"))
            continue
        name = props.find("string[@name='Name']")
        if name is None or not (name.text or "").strip():
            problems.append("unnamed %s" % it.get("class"))
        for r in props.findall("Ref"):
            if r.text not in refset:
                problems.append("dangling Ref %s" % r.text)
        if it.get("class") == "Part":
            n_parts += 1
            cf = props.find("CoordinateFrame[@name='CFrame']")
            sz = props.find("Vector3[@name='size']")
            if cf is None or sz is None:
                problems.append("Part missing CFrame/size")
                continue
            vals = {c.tag: float(c.text) for c in cf}
            size = [float(c.text) for c in sz]
            if not all(math.isfinite(v) for v in vals.values()):
                problems.append("non-finite CFrame")
            if not all(math.isfinite(v) and v >= 0.001 for v in size):
                problems.append("bad size (non-positive/non-finite)")
            # rotation must be orthonormal
            R = [[vals["R%d%d" % (i, j)] for j in range(3)] for i in range(3)]
            for i in range(3):
                for j in range(3):
                    dot = sum(R[k][i] * R[k][j] for k in range(3))
                    if abs(dot - (1 if i == j else 0)) > 1e-3:
                        problems.append("non-orthonormal rotation")
                        break
            ymin, ymax = min(ymin, vals["Y"]), max(ymax, vals["Y"])
            xmin, xmax = min(xmin, vals["X"]), max(xmax, vals["X"])
            zmin, zmax = min(zmin, vals["Z"]), max(zmax, vals["Z"])
            mat = props.find("token[@name='Material']")
            if mat is None or int(mat.text) not in MAT_OK:
                problems.append("bad material %s" % (mat.text if mat is not None else None))
            mv = props.find("string[@name='MaterialVariantSerialized']")
            if mv is not None:
                want = VARIANT_BASE.get(mv.text)
                if want is None:
                    problems.append("unknown MaterialVariant %s" % mv.text)
                elif mat is not None and int(mat.text) != want:
                    problems.append("variant %s on wrong base material (%s)" % (mv.text, mat.text))
                variants_used[mv.text] += 1
            col = props.find("Color3uint8[@name='Color3uint8']")
            if col is None or not (0xFF000000 <= int(col.text) <= 0xFFFFFFFF):
                problems.append("bad colour")
    problems = sorted(set(problems))
    return {"path": path, "items": len(items), "parts": n_parts, "classes": dict(classes),
            "y": (ymin, ymax) if n_parts else None,
            "x": (xmin, xmax) if n_parts else None, "z": (zmin, zmax) if n_parts else None,
            "variants": dict(variants_used), "problems": problems}


if __name__ == "__main__":
    bad = 0
    for p in sys.argv[1:]:
        try:
            r = check(p)
        except ET.ParseError as e:
            print("FAIL", p, "not well-formed:", e)
            bad += 1
            continue
        status = "OK  " if not r["problems"] else "FAIL"
        print("%s %s: %d items, %d parts" % (status, p, r["items"], r["parts"]))
        if r["parts"]:
            print("     X %.0f..%.0f  Y %.1f..%.1f  Z %.0f..%.0f" % (*r["x"], *r["y"], *r["z"]))
        print("     classes:", r["classes"])
        if r.get("variants"):
            print("     variants used:", r["variants"])
        for pr in r["problems"]:
            print("     !", pr)
        bad += bool(r["problems"])
    sys.exit(1 if bad else 0)

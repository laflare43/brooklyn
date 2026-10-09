#!/usr/bin/env python3
"""
make_block.py — builds the Pitkin Ave / Van Siclen / Bradford / Glenmore block
(Fiorentino Plaza and its surroundings) as Roblox .rbxmx models from an
OpenStreetMap export.

    python3 tools/make_block.py --osm data/map.osm --out models/block

Scale: 1 stud = 0.30 m by default (--stud-m).  X = east, Z = south, Y = up, and
the origin is the map centre (lat 40.672833, lon -73.891728).  Every file keeps
absolute coordinates, so all of them line up when inserted at the origin.
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blockgen import rbxlib, streets, style, buildings, variants, textures   # noqa: E402
from blockgen.osmdata import World                    # noqa: E402

LAT0, LON0 = 40.672833, -73.891728


def write(path, roots):
    xml = rbxlib.to_rbxmx(roots)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(xml)
    return len(xml)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--osm", default="data/map.osm")
    ap.add_argument("--out", default="models/block")
    ap.add_argument("--stud-m", type=float, default=0.30)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--no-trees", action="store_true")
    ap.add_argument("--only", default="", help="comma list: streets,project,buildings,variants")
    ap.add_argument("--preview-dir", default="")
    ap.add_argument("--textures", action="store_true",
                    help="(re)generate the PBR texture PNGs into --texture-dir")
    ap.add_argument("--texture-dir", default="textures")
    ap.add_argument("--flip-green", action="store_true",
                    help="flip the normal maps' green channel (DirectX convention)")
    ap.add_argument("--ids", default="textures/asset_ids.json",
                    help="json of uploaded texture asset ids (see README)")
    a = ap.parse_args(argv)

    world = World(a.osm, LAT0, LON0, a.stud_m)
    only = set(x for x in a.only.split(",") if x)
    want = lambda k: not only or k in only          # noqa: E731
    rng = random.Random(a.seed)

    print("world: %d buildings, %d roads, %d sidewalks, %d crossings, %.0f x %.0f studs"
          % (len(world.buildings), len(world.roads), len(world.sidewalks),
             len(world.crossings), world.box[2] - world.box[0], world.box[3] - world.box[1]))

    outputs = {}

    # ─── streets, ground, lots ──────────────────────────────────────────────
    if want("streets"):
        scene = rbxlib.Scene()
        ctx = streets.Ctx(world, rng)
        ctx.building_rings = [b["outer"] for b in world.buildings]
        root = scene.model("Block_Streets")
        root.add(streets.build_ground(world, scene))
        root.add(streets.build_roads(world, scene, ctx))
        streets.classify_sidewalks(world, ctx)
        sw, paths = streets.build_sidewalks(world, scene, ctx)
        root.add(sw)
        root.add(paths)
        root.add(streets.build_crossings(world, scene, ctx))
        root.add(streets.build_markings(world, scene, ctx))
        root.add(streets.build_areas(world, scene, ctx,
                                     [b["outer"] for b in world.buildings]))
        root.add(streets.build_furniture(world, scene, ctx, trees=not a.no_trees))
        outputs["Block_Streets.rbxmx"] = (scene, [root])

    # ─── buildings ──────────────────────────────────────────────────────────
    if want("project") or want("buildings"):
        ctx2 = streets.Ctx(world, rng)
        # the road list is needed for frontage tests even when streets are skipped
        for road in world.roads:
            pass
        scene_s = rbxlib.Scene()
        ctx2.building_rings = [b["outer"] for b in world.buildings]
        streets.build_roads(world, scene_s, ctx2)
        bld = buildings.Builder(world, ctx2, {"seed": a.seed})
        groups = {"project": rbxlib.Scene(), "west": rbxlib.Scene(), "east": rbxlib.Scene()}
        roots = {k: groups[k].model(n) for k, n in
                 (("project", "Block_Project_FiorentinoPlaza"),
                  ("west", "Block_Buildings_West"), ("east", "Block_Buildings_East"))}
        others = [b for b in bld.bs if b.kind not in ("project",)]
        xs = sorted(b.centroid[0] for b in others)
        xsplit = xs[len(xs) // 2] if xs else 0
        counts = {}
        for b in bld.bs:
            if b.kind == "project":
                g = "project"
            else:
                g = "west" if b.centroid[0] < xsplit else "east"
            if g == "project" and not want("project"):
                continue
            if g != "project" and not want("buildings"):
                continue
            roots[g].add(bld.build(b, groups[g]))
            counts[b.kind] = counts.get(b.kind, 0) + 1
        print("buildings:", counts)
        names = {"project": "Block_Project_FiorentinoPlaza.rbxmx",
                 "west": "Block_Buildings_West.rbxmx", "east": "Block_Buildings_East.rbxmx"}
        for g, sc in groups.items():
            if sc.parts:
                outputs[names[g]] = (sc, [roots[g]])

    # ─── MaterialVariants (+ optional texture regeneration) ─────────────────
    if a.textures:
        written = textures.generate_all(a.texture_dir, flip_green=a.flip_green)
        print("textures: %d sets written to %s" % (len(written), a.texture_dir))
    if want("variants"):
        ids = variants.load_ids(a.ids)
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "MaterialVariants.rbxmx"), "w", encoding="utf-8") as fh:
            fh.write(variants.build_rbxmx(a.stud_m, ids))
        with open(os.path.join(a.out, "MaterialVariants_Setup.luau"), "w", encoding="utf-8") as fh:
            fh.write(variants.build_luau(a.stud_m, ids))
        print("wrote MaterialVariants.rbxmx + MaterialVariants_Setup.luau (%d texture ids applied)"
              % len(ids))

    for fname, (scene, roots) in outputs.items():
        path = os.path.join(a.out, fname)
        size = write(path, roots)
        print("wrote %-28s %6d parts  %6.1f MB" % (fname, len(scene.parts), size / 1e6))
        if a.preview_dir:
            from blockgen import preview
            os.makedirs(a.preview_dir, exist_ok=True)
            preview.top_view(scene.parts, os.path.join(a.preview_dir, fname + ".top.png"),
                             xlim=(world.box[0] - 20, world.box[2] + 20),
                             zlim=(world.box[1] - 20, world.box[3] + 20), title=fname)
    if a.preview_dir and len(outputs) > 1:
        from blockgen import preview
        allp = [p for (sc, _r) in outputs.values() for p in sc.parts]
        print("combined preview of %d parts..." % len(allp))
        for tag, kw in (
                ("aerial_NE", dict(target=(-40, 10, 30), az=205, el=38, dist=1500,
                                   half_w=470, half_h=300)),
                ("aerial_SW", dict(target=(-40, 10, 30), az=25, el=38, dist=1500,
                                   half_w=470, half_h=300)),
                ("street_pitkin", dict(target=(-60, 12, 120), az=115, el=9, dist=900,
                                       half_w=130, half_h=70)),
                ("project_court", dict(target=(-40, 8, -20), az=170, el=16, dist=800,
                                       half_w=170, half_h=80))):
            preview.iso_view(allp, os.path.join(a.preview_dir, "combined_%s.png" % tag),
                             title=tag, dpi=70, **kw)
    return 0


if __name__ == "__main__":
    sys.exit(main())

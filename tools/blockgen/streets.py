"""
streets.py — ground, roads, curbs, sidewalks, crosswalks, markings, parks,
courtyards, pools and street furniture, all from the OSM export.
"""
import math
import random

from . import geo, style
from .rbxlib import basis, Rz90, SHAPE_CYLINDER, SHAPE_BALL, IDENT

ROAD_TOP = 0.05           # studs above the base ground
ROAD_STEP = 0.03          # per-road height step so overlapping roads never z-fight


def dp_line(pts, eps):
    """Douglas–Peucker for an open polyline."""
    if len(pts) < 3:
        return list(pts)
    a, b = pts[0], pts[-1]
    dmax, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d, _ = geo.dist_pt_seg(pts[i], a, b)
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        left = dp_line(pts[:idx + 1], eps)
        right = dp_line(pts[idx:], eps)
        return left[:-1] + right
    return [a, b]


class Ctx:
    """Shared state other modules (buildings) can query."""

    def __init__(self, world, rng):
        self.w = world
        self.S = world.S
        self.rng = rng
        self.roads = []     # dicts: name, kind, runs, half, order
        self.street_walks = []   # polylines classified as street sidewalks
        self.paths = []

    def M(self, metres):
        return metres * self.S

    def nearest_road(self, p, kinds=None):
        best = (1e18, None, None)
        for r in self.roads:
            if kinds and r["kind"] not in kinds:
                continue
            for run in r["runs"]:
                for a, b in zip(run, run[1:]):
                    d, t = geo.dist_pt_seg(p, a, b)
                    if d < best[0]:
                        best = (d, r, geo.lerp(a, b, t))
        return best


def seg_part(scene, name, a, b, width, y_top, thick, off=0.0, ext=0.0, **kw):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    if L < 1e-4:
        return None
    dx, dz = dx / L, dz / L
    nx, nz = -dz, dx
    cx = (a[0] + b[0]) / 2 + nx * off
    cz = (a[1] + b[1]) / 2 + nz * off
    return scene.part(name, (L + 2 * ext, thick, width), (cx, y_top - thick / 2, cz),
                      basis(dx, dz), **kw)


def disc(scene, name, p, diameter, y_top, thick, **kw):
    return scene.part(name, (thick, diameter, diameter), (p[0], y_top - thick / 2, p[1]),
                      Rz90(), shape=SHAPE_CYLINDER, **kw)


def turn_angle(a, b, c):
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    l1, l2 = math.hypot(*v1), math.hypot(*v2)
    if l1 < 1e-6 or l2 < 1e-6:
        return 0.0
    cs = max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)))
    return math.degrees(math.acos(cs))


def stroke_polyline(scene, folder, name, pts, width, y_top, thick, joint_deg=1.5,
                    off=0.0, ext=0.05, **kw):
    """Lay a polyline as overlapping boxes, with a disc at every real bend."""
    for a, b in zip(pts, pts[1:]):
        p = seg_part(scene, name, a, b, width, y_top, thick, off=off, ext=ext, **kw)
        if p:
            folder.add(p)
    if off == 0.0:
        for i in range(1, len(pts) - 1):
            if turn_angle(pts[i - 1], pts[i], pts[i + 1]) > joint_deg:
                folder.add(disc(scene, name + "Joint", pts[i], width, y_top, thick, **kw))


# ─── measuring road widths from the mapped sidewalks ────────────────────────
def measure_half_width(world, road, runs):
    S = world.S
    dists = []
    for run in runs:
        for a, b in zip(run, run[1:]):
            L = math.dist(a, b)
            if L < 1e-6:
                continue
            dx, dz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            n = max(1, int(L / (8 * S)))
            for i in range(n):
                p = geo.lerp(a, b, (i + 0.5) / n)
                for side in (1, -1):
                    best = 1e18
                    for sw in world.sidewalks:
                        for s0, s1 in zip(sw, sw[1:]):
                            sx, sz = s1[0] - s0[0], s1[1] - s0[1]
                            sl = math.hypot(sx, sz)
                            if sl < 1e-6 or abs((sx * dx + sz * dz) / sl) < 0.95:
                                continue
                            d, t = geo.dist_pt_seg(p, s0, s1)
                            cp = geo.lerp(s0, s1, t)
                            sd = 1 if ((cp[0] - p[0]) * (-dz) + (cp[1] - p[1]) * dx) > 0 else -1
                            if sd == side and d < best:
                                best = d
                    if best < 20 * S:
                        dists.append(best)
    if len(dists) >= 6:
        dists.sort()
        med = dists[len(dists) // 2]
        return max(med - style.SIDEWALK_W * S / 2, 3.0 * S)
    return (5.2 if road["kind"] != "tertiary" else 9.0) * S


# ─── builders ───────────────────────────────────────────────────────────────
def build_ground(world, scene):
    # cover the whole export box AND any building that spills past its edge, so
    # nothing is left hanging over empty space
    x0, z0, x1, z1 = world.clip_box(6)
    for b in world.buildings:
        bx0, bz0, bx1, bz1 = geo.bbox(b["outer"])
        x0, z0, x1, z1 = min(x0, bx0 - 6), min(z0, bz0 - 6), max(x1, bx1 + 6), max(z1, bz1 + 6)
    f = scene.folder("Ground")
    f.add(scene.part("BaseGround", (x1 - x0, 6, z1 - z0),
                     ((x0 + x1) / 2, -3.0, (z0 + z1) / 2),
                     color=style.LOT, material="Concrete", variant="FB_SidewalkConcrete"))
    return f


def build_roads(world, scene, ctx):
    f = scene.folder("Roads")
    box = world.clip_box(4)
    S = world.S
    order = 0
    for road in world.roads:
        runs = [dp_line(r, 0.25 * S) for r in geo.clip_polyline(road["pts"], box)]
        if not runs:
            continue
        if road["kind"] == "service":
            half = 2.4 * S
            if road["private"]:
                continue        # private driveways: leave as bare lot
        else:
            half = measure_half_width(world, road, runs)
        top = ROAD_TOP + ROAD_STEP * order
        order += 1
        sub = f.add(scene.folder(road["name"] or "Service road"))
        for run in runs:
            stroke_polyline(scene, sub, "Asphalt", run, half * 2, top, 0.4,
                            color=style.ASPHALT, material="Asphalt", variant="FB_AsphaltRoad",
                            ext=0.5)
        ctx.roads.append({"name": road["name"], "kind": road["kind"], "runs": runs,
                          "half": half, "top": top, "oneway": road["oneway"],
                          "tags": road["tags"]})
    return f


def classify_sidewalks(world, ctx):
    """Street sidewalks run beside a road; everything else is an interior path."""
    S = world.S
    for sw in world.sidewalks:
        for run in geo.clip_polyline(sw, world.clip_box(4)):
            run = dp_line(run, 0.12 * S)
            mid = run[len(run) // 2]
            d, road, cp = ctx.nearest_road(mid, kinds=("residential", "tertiary"))
            if road is not None and d < road["half"] + style.SIDEWALK_W * S * 1.1:
                ctx.street_walks.append(run)
            else:
                ctx.paths.append(run)


def build_sidewalks(world, scene, ctx):
    S = world.S
    f = scene.folder("Sidewalks")
    top = style.SIDEWALK_H * S
    sw_w = style.SIDEWALK_W * S
    curb_w = style.CURB_W * S
    for run in ctx.street_walks:
        stroke_polyline(scene, f, "Sidewalk", run, sw_w, top, top,
                        color=style.SIDEWALK, material="Concrete",
                        variant="FB_SidewalkConcrete", ext=0.04)
        # curb on the road side of each straight stretch
        for a, b in zip(run, run[1:]):
            L = math.dist(a, b)
            if L < 0.5:
                continue
            dx, dz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            mid = geo.lerp(a, b, 0.5)
            d, road, cp = ctx.nearest_road(mid, kinds=("residential", "tertiary"))
            if road is None or d > road["half"] + sw_w:
                continue
            # only where the road runs the same way as this sidewalk
            best = None
            for rr in road["runs"]:
                for ra, rb in zip(rr, rr[1:]):
                    dd, t = geo.dist_pt_seg(mid, ra, rb)
                    if best is None or dd < best[0]:
                        best = (dd, ra, rb)
            rl = math.dist(best[1], best[2])
            if rl < 1e-6 or abs(((best[2][0] - best[1][0]) * dx
                                 + (best[2][1] - best[1][1]) * dz) / rl) < 0.97:
                continue
            side = 1 if ((cp[0] - mid[0]) * (-dz) + (cp[1] - mid[1]) * dx) > 0 else -1
            off = side * (sw_w / 2 - curb_w / 2)
            p = seg_part(scene, "Curb", a, b, curb_w, top + 0.03, top + 0.03, off=off,
                         ext=0.04, color=style.CURB, material="Granite",
                         variant="FB_GraniteCurb")
            if p:
                f.add(p)
    pf = scene.folder("Paths")
    ptop = 0.14
    for run in ctx.paths:
        stroke_polyline(scene, pf, "Path", run, style.PATH_W * S, ptop, ptop,
                        color=(176, 172, 164), material="Concrete",
                        variant="FB_SidewalkConcrete", ext=0.04)
    return f, pf


def build_crossings(world, scene, ctx):
    S = world.S
    f = scene.folder("Crosswalks")
    for cr in world.crossings:
        for run in geo.clip_polyline(cr["pts"], world.clip_box(3)):
            if len(run) < 2:
                continue
            a, b = run[0], run[-1]
            L = math.dist(a, b)
            if L < 3 * S:
                continue
            dx, dz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            # find the part of the line that is actually on the road
            ts = []
            steps = int(L / (0.25 * S)) + 1
            for k in range(steps + 1):
                p = geo.lerp(a, b, k / steps)
                d, road, _ = ctx.nearest_road(p, kinds=("residential", "tertiary"))
                if road is not None and d < road["half"]:
                    ts.append(k / steps)
            if not ts:
                continue
            t0, t1 = min(ts), max(ts)
            p0, p1 = geo.lerp(a, b, t0), geo.lerp(a, b, t1)
            span = math.dist(p0, p1)
            if span < 2 * S:
                continue
            _, road, _ = ctx.nearest_road(geo.lerp(p0, p1, 0.5),
                                          kinds=("residential", "tertiary"))
            top = (road["top"] if road else ROAD_TOP) + 0.03
            cw = 2.6 * S                       # bar length, along the traffic direction
            bar = 0.55 * S
            gap = 0.55 * S
            n = max(1, int((span - bar) / (bar + gap)) + 1)
            used = n * bar + (n - 1) * gap
            start = (span - used) / 2 + bar / 2
            if cr["markings"] == "ladder":
                for sgn in (-1, 1):
                    q0 = (p0[0] + (-dz) * sgn * cw / 2, p0[1] + dx * sgn * cw / 2)
                    q1 = (p1[0] + (-dz) * sgn * cw / 2, p1[1] + dx * sgn * cw / 2)
                    f.add(seg_part(scene, "LadderRail", q0, q1, 0.3 * S, top, 0.04,
                                   color=style.PAINT_WHITE, material="SmoothPlastic",
                                   collide=False, query=False))
                bars = range(0, n, 2)
            else:
                bars = range(n)
            for i in bars:
                c = start + i * (bar + gap)
                cx, cz = p0[0] + dx * c, p0[1] + dz * c
                f.add(scene.part("ZebraBar", (bar, 0.04, cw), (cx, top - 0.02, cz),
                                 basis(dx, dz), color=style.PAINT_WHITE,
                                 material="SmoothPlastic", collide=False, query=False))
    return f


def build_markings(world, scene, ctx):
    S = world.S
    f = scene.folder("Markings")
    for r in ctx.roads:
        if r["kind"] != "tertiary":
            continue
        top = r["top"] + 0.03
        for run in r["runs"]:
            for off in (-0.14 * S, 0.14 * S):
                for a, b in zip(run, run[1:]):
                    p = seg_part(scene, "CenterLine", a, b, 0.1 * S, top, 0.04, off=off,
                                 ext=0.05, color=style.PAINT_YELLOW,
                                 material="SmoothPlastic", collide=False, query=False)
                    if p:
                        f.add(p)
            for sgn in (-1, 1):
                for a, b in zip(run, run[1:]):
                    p = seg_part(scene, "LaneEdge", a, b, 0.14 * S, top, 0.04,
                                 off=sgn * (r["half"] - 2.4 * S), ext=0.05,
                                 color=style.PAINT_WHITE, material="SmoothPlastic",
                                 collide=False, query=False)
                    if p:
                        f.add(p)
    return f


def build_areas(world, scene, ctx, building_rings):
    S = world.S
    f = scene.folder("Lots")
    for a in world.areas:
        ring = geo.orient(geo.simplify_ring(a["ring"], 0.05 * S))
        kind = a["kind"]
        if kind in ("park", "garden"):
            cx, cz = geo.centroid(ring)
            ang = geo.dominant_angle(ring)
            for rect in geo.decompose([ring], ang):
                (px, pz), (du, dv) = geo.rect_world(rect, ang)
                if du < 0.05 or dv < 0.05:
                    continue
                f.add(scene.part("Grass", (du, 0.2, dv), (px, 0.1, pz),
                                 basis(math.cos(ang), math.sin(ang)), color=style.GRASS,
                                 material="Grass"))
        elif kind == "school":
            ang = geo.dominant_angle(ring)
            for rect in geo.decompose([ring], ang):
                (px, pz), (du, dv) = geo.rect_world(rect, ang)
                if du < 0.05 or dv < 0.05:
                    continue
                f.add(scene.part("Schoolyard", (du, 0.2, dv), (px, 0.1, pz),
                                 basis(math.cos(ang), math.sin(ang)), color=(86, 88, 92),
                                 material="Asphalt", variant="FB_AsphaltRoad"))
        elif kind == "swimming_pool":
            cx, cz = geo.centroid(ring)
            r = sum(math.dist((cx, cz), p) for p in ring) / len(ring)
            f.add(disc(scene, "PoolRim", (cx, cz), 2 * r + 0.7 * S, 0.9, 0.9,
                       color=(190, 186, 176), material="Concrete"))
            f.add(disc(scene, "PoolWater", (cx, cz), 2 * r, 0.93, 0.3,
                       color=(86, 168, 204), material="SmoothPlastic", transparency=0.25,
                       collide=False))
        elif kind == "residential":
            # the housing complex grounds: lawn everywhere that is not a building
            # only the buildings that stand inside the grounds are cut out of the
            # lawn; the rest are irrelevant here and would only add slivers
            inner = [geo.orient(geo.simplify_ring(b, 0.05 * S)) for b in building_rings
                     if geo.point_in_poly(geo.centroid(b), ring)]
            rings = [ring] + inner
            ang = geo.dominant_angle(ring)
            for rect in geo.decompose(rings, ang, tol=0.3):
                (px, pz), (du, dv) = geo.rect_world(rect, ang)
                if du < 0.3 or dv < 0.3 or not geo.point_in_poly((px, pz), ring):
                    continue
                f.add(scene.part("CourtyardLawn", (du, 0.14, dv), (px, 0.07, pz),
                                 basis(math.cos(ang), math.sin(ang)), color=style.GRASS,
                                 material="Grass"))
    return f


# ─── street furniture (procedural: not in the map data) ─────────────────────
def along(run, spacing, offset=0.0):
    """Yield (point, dir) every `spacing` along a polyline."""
    dist = offset
    out = []
    for a, b in zip(run, run[1:]):
        L = math.dist(a, b)
        if L < 1e-6:
            continue
        d = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        while dist < L:
            out.append((geo.lerp(a, b, dist / L), d))
            dist += spacing
        dist -= L
    return out


def build_furniture(world, scene, ctx, trees=True):
    S, rng = world.S, ctx.rng
    f = scene.folder("StreetFurniture")
    sw_h = style.SIDEWALK_H * S
    lamps = f.add(scene.folder("StreetLamps"))
    hyd = f.add(scene.folder("Hydrants"))
    man = f.add(scene.folder("Manholes"))
    sig = f.add(scene.folder("PedSignals"))
    tf = f.add(scene.folder("Trees"))

    # lamps + hydrants along each real road, on the sidewalk next to the curb
    for r in ctx.roads:
        if r["kind"] == "service":
            continue
        for run in r["runs"]:
            side = 1
            for p, d in along(run, 30 * S, offset=6 * S):
                nx, nz = -d[1], d[0]
                off = r["half"] + 0.9 * S * 0.5 + 0.55 * S
                lx, lz = p[0] + nx * side * off, p[1] + nz * side * off
                # skip lamps that fall inside a building or off the map
                if any(geo.point_in_poly((lx, lz), b) for b in ctx.building_rings):
                    side = -side
                    continue
                if not (world.box[0] < lx < world.box[2] and world.box[1] < lz < world.box[3]):
                    side = -side
                    continue
                H = 8.6 * S
                lamps.add(scene.part("LampPole", (H, 0.28 * S, 0.28 * S),
                                     (lx, sw_h + H / 2, lz), Rz90(), color=(52, 56, 60),
                                     material="Metal", shape=SHAPE_CYLINDER))
                ax, az = -nx * side, -nz * side           # arm points toward the road
                arm_len = 2.2 * S
                lamps.add(scene.part("LampArm", (arm_len, 0.14 * S, 0.14 * S),
                                     (lx + ax * arm_len / 2, sw_h + H, lz + az * arm_len / 2),
                                     basis(ax, az), color=(52, 56, 60), material="Metal"))
                hx, hz = lx + ax * arm_len, lz + az * arm_len
                lamps.add(scene.part("LampHead", (1.0 * S, 0.3 * S, 0.45 * S),
                                     (hx, sw_h + H - 0.05, hz), basis(ax, az),
                                     color=(70, 74, 78), material="Metal"))
                lamps.add(scene.part("LampLens", (0.8 * S, 0.05 * S, 0.35 * S),
                                     (hx, sw_h + H - 0.05 - 0.17 * S, hz), basis(ax, az),
                                     color=(255, 238, 190), material="Neon", collide=False,
                                     query=False))
                side = -side
        # a few hydrants and manholes
        for run in r["runs"]:
            for p, d in along(run, 55 * S, offset=rng.uniform(5, 40) * S):
                nx, nz = -d[1], d[0]
                sgn = rng.choice((-1, 1))
                off = r["half"] + 0.9 * S * 0.4 + 0.5 * S
                hx, hz = p[0] + nx * sgn * off, p[1] + nz * sgn * off
                if any(geo.point_in_poly((hx, hz), b) for b in ctx.building_rings):
                    continue
                if not (world.box[0] < hx < world.box[2] and world.box[1] < hz < world.box[3]):
                    continue
                hyd.add(scene.part("Hydrant", (0.8 * S, 0.34 * S, 0.34 * S),
                                   (hx, sw_h + 0.4 * S, hz), Rz90(), color=(186, 38, 30),
                                   material="Metal", shape=SHAPE_CYLINDER))
                hyd.add(scene.part("HydrantCap", (0.14 * S, 0.4 * S, 0.4 * S),
                                   (hx, sw_h + 0.82 * S, hz), Rz90(), color=(196, 168, 40),
                                   material="Metal", shape=SHAPE_CYLINDER))
            for p, d in along(run, 40 * S, offset=rng.uniform(5, 30) * S):
                nx, nz = -d[1], d[0]
                mx, mz = p[0] + nx * rng.uniform(-0.3, 0.3) * r["half"], \
                    p[1] + nz * rng.uniform(-0.3, 0.3) * r["half"]
                if not (world.box[0] < mx < world.box[2] and world.box[1] < mz < world.box[3]):
                    continue
                man.add(disc(scene, "Manhole", (mx, mz), 0.8 * S, r["top"] + 0.06, 0.05,
                             color=(60, 58, 56), material="Metal", collide=False, query=False))

    # pedestrian signals at signalised crossings
    for cr in world.crossings:
        if not cr["signals"] or len(cr["pts"]) < 2:
            continue
        a, b = cr["pts"][0], cr["pts"][-1]
        L = math.dist(a, b)
        if L < 1e-6:
            continue
        dx, dz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        for end, face in ((a, 1), (b, -1)):
            if not (world.box[0] < end[0] < world.box[2] and world.box[1] < end[1] < world.box[3]):
                continue
            # step back from the crossing end so the pole stands beside the ramp
            px = end[0] - dx * face * 0.0 + (-dz) * 1.3 * S
            pz = end[1] - dz * face * 0.0 + dx * 1.3 * S
            if any(geo.point_in_poly((px, pz), bb) for bb in ctx.building_rings):
                continue
            H = 3.3 * S
            sig.add(scene.part("SignalPole", (H, 0.18 * S, 0.18 * S),
                               (px, sw_h + H / 2, pz), Rz90(), color=(54, 58, 62),
                               material="Metal", shape=SHAPE_CYLINDER))
            hx, hz = px + dx * face * 0.2 * S, pz + dz * face * 0.2 * S
            sig.add(scene.part("PedHead", (0.5 * S, 0.62 * S, 0.22 * S),
                               (hx, sw_h + H - 0.2 * S, hz), basis(dx * -face, dz * -face),
                               color=(40, 42, 46), material="Metal"))
            sig.add(scene.part("PedLamp", (0.26 * S, 0.3 * S, 0.04 * S),
                               (hx - dx * face * 0.12 * S, sw_h + H - 0.08 * S,
                                hz - dz * face * 0.12 * S), basis(dx * -face, dz * -face),
                               color=(255, 150, 40), material="Neon", collide=False,
                               query=False))

    if trees:
        for run in ctx.street_walks:
            L = sum(math.dist(a, b) for a, b in zip(run, run[1:]))
            if L < 8 * S:
                continue
            for p, d in along(run, 10.5 * S, offset=rng.uniform(2, 6) * S):
                if rng.random() < 0.35:
                    continue
                d0, road, cp = ctx.nearest_road(p, kinds=("residential", "tertiary"))
                if road is None:
                    continue
                vx, vz = cp[0] - p[0], cp[1] - p[1]
                vl = math.hypot(vx, vz) or 1
                # toward the curb, 0.9 m in from the curb line
                tx = p[0] + vx / vl * (style.SIDEWALK_W * S / 2 - 0.9 * S)
                tz = p[1] + vz / vl * (style.SIDEWALK_W * S / 2 - 0.9 * S)
                if any(geo.point_in_poly((tx, tz), bb) for bb in ctx.building_rings):
                    continue
                if not (world.box[0] < tx < world.box[2] and world.box[1] < tz < world.box[3]):
                    continue
                th = rng.uniform(3.0, 4.2) * S
                tf.add(scene.part("TreePit", (1.3 * S, 0.04, 2.2 * S),
                                  (tx, sw_h + 0.02, tz), basis(d[0], d[1]),
                                  color=(70, 56, 44), material="Ground", collide=False,
                                  query=False))
                tf.add(scene.part("Trunk", (th, 0.38 * S, 0.38 * S),
                                  (tx, sw_h + th / 2, tz), Rz90(), color=(86, 66, 48),
                                  material="Wood", shape=SHAPE_CYLINDER))
                rad = rng.uniform(2.3, 3.4) * S
                g = rng.randint(0, 28)
                col = (58 + g, 104 + g, 50 + g // 2)
                for ox, oy, oz, k in ((0, 0, 0, 1.0), (0.55, -0.15, 0.2, 0.75),
                                      (-0.5, -0.1, -0.3, 0.8)):
                    tf.add(scene.part("Canopy", (rad * 2 * k,) * 3,
                                      (tx + ox * rad, sw_h + th + rad * 0.7 + oy * rad,
                                       tz + oz * rad), color=col, material="LeafyGrass",
                                      shape=SHAPE_BALL, collide=False))
    return f

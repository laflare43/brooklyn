"""
buildings.py — turns OSM building footprints into Roblox models.

Each building is built from the real footprint (exact for these rectilinear
outlines): hollow brick walls, a flat tar roof with a parapet, window bays on
every exposed wall, a water-table course, and a type-specific treatment:

    project     red-brick walk-up/elevator slabs inside the housing grounds
                (stair-bay entrances with canopies, security-barred ground
                floor windows, roof bulkheads)
    commercial  Pitkin Ave frontage: storefronts, roll gates, sign bands,
                awnings, cornice, fire escapes
    row         rowhouses: stoops, doors, cornice, fire escapes on 4+ storeys
    school      the J.H.S. building: tan brick, big window grid
    accessory   garages and sheds: plain walls, roll door

Heights come from the OSM `height` tag (metres).  Everything that is not in
the map data (window layout, doors, store signs without text) is a plausible
generic NYC treatment and is clearly named in the model so it can be edited.
"""
import math
import random

from . import geo, style
from .rbxlib import basis, Rz90, SHAPE_CYLINDER, tilt_x
from .streets import seg_part


class Edge:
    __slots__ = ("p", "q", "L", "d", "n", "mid", "shared", "front", "road", "idx", "hole")


class Bldg:
    pass


def hash01(s):
    h = 2166136261
    for ch in str(s):
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h / 0xFFFFFFFF


def pick(seq, u):
    return seq[min(len(seq) - 1, int(u * len(seq)))]


class Builder:
    def __init__(self, world, ctx, cfg):
        self.w, self.ctx, self.cfg = world, ctx, cfg
        self.S = world.S
        self.fior = None
        for a in world.areas:
            if a["kind"] == "residential" and "Fiorentino" in a["name"]:
                self.fior = geo.orient(a["ring"])
        # normalised footprints for neighbour tests
        self.bs = []
        for b in world.buildings:
            o = geo.simplify_ring(b["outer"], 0.06 * self.S)
            if len(o) < 3 or abs(geo.signed_area(o)) * world.stud_m ** 2 < 4:
                continue
            bb = Bldg()
            bb.id = b["id"]
            bb.tags = b["tags"]
            bb.outer = geo.orient(o, True)
            bb.holes = [geo.orient(geo.simplify_ring(h, 0.06 * self.S), False)
                        for h in b["holes"]]
            bb.area_m2 = abs(geo.signed_area(bb.outer)) * world.stud_m ** 2
            bb.bbox = geo.bbox(bb.outer)
            bb.centroid = geo.centroid(bb.outer)
            try:
                bb.Hm = float(str(bb.tags.get("height", "")).replace("m", "").strip())
            except ValueError:
                bb.Hm = 8.0
            bb.Hm = min(max(bb.Hm, 3.0), 40.0)
            self.bs.append(bb)
        for bb in self.bs:
            bb.kind = self.classify(bb)

    # ── classification ──────────────────────────────────────────────────────
    def classify(self, b):
        t = b.tags
        S = self.S
        if t.get("building") == "school":
            return "school"
        if self.fior and geo.point_in_poly(b.centroid, self.fior):
            return "project"
        if self.fior and b.Hm >= 12 and b.area_m2 > 250:
            # a big 4+ storey slab right beside the grounds belongs to the complex
            dmin = min(geo.dist_pt_seg(b.centroid, self.fior[i], self.fior[(i + 1) % len(self.fior)])[0]
                       for i in range(len(self.fior)))
            if dmin < 14 * S:
                return "project"
        if b.area_m2 < 75 or b.Hm < 4.4:
            return "accessory"
        if t.get("addr:street") == "Pitkin Avenue":
            return "commercial"
        d, road, _ = self.ctx.nearest_road(b.centroid, kinds=("tertiary",))
        if road is not None and d < road["half"] + 16 * S and b.Hm <= 13:
            return "commercial"
        return "row"

    # ── geometry helpers ────────────────────────────────────────────────────
    def edges_of(self, ring, hole, b):
        S = self.S
        out = []
        n = len(ring)
        for i in range(n):
            p, q = ring[i], ring[(i + 1) % n]
            L = math.dist(p, q)
            if L < 0.05 * S:
                continue
            e = Edge()
            e.p, e.q, e.L, e.idx, e.hole = p, q, L, i, hole
            e.d = ((q[0] - p[0]) / L, (q[1] - p[1]) / L)
            e.n = (-e.d[1], e.d[0])
            e.mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
            e.shared = self.is_shared(e, b)
            e.road = None
            e.front = False
            if not e.shared and not hole:
                dist, road, cp = self.ctx.nearest_road(e.mid, kinds=("residential", "tertiary"))
                if road is not None and dist < road["half"] + 18 * S:
                    vx, vz = cp[0] - e.mid[0], cp[1] - e.mid[1]
                    vl = math.hypot(vx, vz) or 1
                    if (vx * e.n[0] + vz * e.n[1]) / vl > 0.88:
                        e.front = True
                        e.road = road
            out.append(e)
        return out

    def is_shared(self, e, b):
        S = self.S
        hits = 0
        for t in (0.2, 0.5, 0.8):
            px = e.p[0] + (e.q[0] - e.p[0]) * t + e.n[0] * 0.18 * S
            pz = e.p[1] + (e.q[1] - e.p[1]) * t + e.n[1] * 0.18 * S
            for o in self.bs:
                if o is b:
                    continue
                x0, z0, x1, z1 = o.bbox
                if not (x0 - 1 < px < x1 + 1 and z0 - 1 < pz < z1 + 1):
                    continue
                if geo.point_in_poly((px, pz), o.outer):
                    hits += 1
                    break
        return hits >= 2

    # ── the building ────────────────────────────────────────────────────────
    def build(self, b, scene):
        S, w = self.S, self.w
        rng = random.Random(self.cfg["seed"] * 7919 + int(hash01(b.id) * 1e9))
        H = b.Hm * S
        kind = b.kind
        if kind == "commercial":
            n_floors = max(2, round((b.Hm - 0.6) / 3.1))
        elif kind == "accessory":
            n_floors = 1
        else:
            n_floors = max(1, round(b.Hm / 3.1))
        gh = H / n_floors
        ground_h = gh
        if kind == "commercial":
            ground_h = min(3.8 * S, H * 0.45)
        b.floors, b.H, b.gh, b.ground_h = n_floors, H, gh, ground_h
        # floor level heights
        b.levels = [0.0]
        upper = (H - ground_h) / max(1, n_floors - 1) if n_floors > 1 else 0
        for i in range(1, n_floors):
            b.levels.append(ground_h + upper * (i - 1))
        b.upper_h = upper if n_floors > 1 else ground_h

        if kind == "project":
            b.brick = pick(style.PROJECT_BRICKS, hash01(b.id))
            b.variant = "FB_BrickProject"
            b.trim = (214, 208, 192)
        elif kind == "school":
            b.brick = (172, 128, 92)
            b.variant = "FB_BrickRow"
            b.trim = (214, 208, 192)
        elif kind == "accessory":
            b.brick = pick(style.ROW_BRICKS, hash01(b.id + "a"))
            b.variant = "FB_BrickRow"
            b.trim = style.CONC_DARK
        else:
            b.brick = pick(style.ROW_BRICKS, hash01(b.id))
            b.variant = "FB_BrickRow"
            b.trim = pick([(214, 208, 192), (196, 190, 176), (232, 228, 214), (170, 150, 120)],
                          hash01(b.id + "t"))

        model = scene.model("%s %s" % (kind.capitalize(), self.label(b)))
        model.add(scene.part("Pivot", (0.2, 0.2, 0.2), (b.centroid[0], 0.1, b.centroid[1]),
                             transparency=1, collide=False, query=False, shadow=False))
        shell = model.add(scene.folder("Shell"))
        wins = model.add(scene.folder("Windows"))
        det = model.add(scene.folder("Details"))
        roof = model.add(scene.folder("Roof"))

        rings = [(b.outer, False)] + [(h, True) for h in b.holes]
        edges = []
        for ring, hole in rings:
            edges.extend(self.edges_of(ring, hole, b))
        b.edges = edges

        self.shell(scene, shell, b, edges)
        self.roof(scene, roof, b, edges, rng)
        for e in edges:
            self.facade(scene, wins, det, b, e, rng)
        if kind == "project":
            self.project_entrances(scene, det, b, edges, rng)
        return model

    def label(self, b):
        t = b.tags
        if t.get("addr:housenumber") and t.get("addr:street"):
            return "%s %s" % (t["addr:housenumber"], t["addr:street"])
        return "#%s" % b.id

    # ── shell: walls, water table, parapet ──────────────────────────────────
    def shell(self, scene, f, b, edges):
        S = self.S
        t = style.WALL_T * S
        top = b.H - 0.04 * S
        for e in edges:
            p = seg_part(scene, "Wall", e.p, e.q, t, top, top, off=-t / 2, ext=0.0,
                         color=b.brick, material="Brick", variant=b.variant)
            if p:
                f.add(p)
            if e.L > 1.2 * S and not e.shared:
                wt = 0.14 * S
                p = seg_part(scene, "WaterTable", e.p, e.q, wt, 0.75 * S, 0.75 * S,
                             off=wt / 2, ext=-0.02 * S, color=style.CONC_DARK,
                             material="Concrete", variant="FB_ConcreteTrim", shadow=False)
                if p:
                    f.add(p)
            pt = 0.34 * S
            p = seg_part(scene, "Parapet", e.p, e.q, pt, b.H + style.PARAPET_H * S,
                         style.PARAPET_H * S, off=-pt / 2, ext=0.0, color=b.brick,
                         material="Brick", variant=b.variant)
            if p:
                f.add(p)
            cap = seg_part(scene, "Coping", e.p, e.q, pt + 0.1 * S,
                           b.H + style.PARAPET_H * S + 0.06 * S, 0.06 * S,
                           off=-pt / 2 + 0.03 * S, ext=0.0, color=style.CONC_TRIM,
                           material="Concrete", variant="FB_ConcreteTrim", shadow=False)
            if cap:
                f.add(cap)

    # ── roof ────────────────────────────────────────────────────────────────
    def roof(self, scene, f, b, edges, rng):
        S = self.S
        ang = geo.dominant_angle(b.outer)
        rings = [b.outer] + b.holes
        rects = geo.decompose(rings, ang, tol=0.2 * S)
        d = (math.cos(ang), math.sin(ang))
        thick = 0.3 * S
        for r in rects:
            (px, pz), (du, dv) = geo.rect_world(r, ang)
            if du < 0.05 or dv < 0.05:
                continue
            f.add(scene.part("RoofSlab", (du + 0.02, thick, dv + 0.02),
                             (px, b.H - thick / 2, pz), basis(*d), color=style.ROOF,
                             material="Concrete", variant="FB_RoofGravel"))
        # roof furniture, kept well inside the footprint
        rng2 = rng
        def free_spot(w, l, tries=60):
            x0, z0, x1, z1 = b.bbox
            for _ in range(tries):
                px, pz = rng2.uniform(x0, x1), rng2.uniform(z0, z1)
                ok = True
                for (sx, sz) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    cx = px + (math.cos(ang) * sx * w / 2 - math.sin(ang) * sz * l / 2)
                    cz = pz + (math.sin(ang) * sx * w / 2 + math.cos(ang) * sz * l / 2)
                    if not geo.point_in_poly((cx, cz), b.outer) or any(
                            geo.point_in_poly((cx, cz), h) for h in b.holes):
                        ok = False
                        break
                    # stay clear of the edges
                    for e in edges:
                        if geo.dist_pt_seg((cx, cz), e.p, e.q)[0] < 1.0 * S:
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    return px, pz
            return None
        placed = []
        def place(name, w, l, h, color, material="Concrete", variant=None, count=1):
            for _ in range(count):
                spot = free_spot(w, l)
                if not spot:
                    continue
                if any(math.dist(spot, q) < (w + l) * 0.6 for q in placed):
                    continue
                placed.append(spot)
                f.add(scene.part(name, (w, h, l), (spot[0], b.H + h / 2, spot[1]),
                                 basis(*d), color=color, material=material,
                                 variant=variant))
        k = b.kind
        if k == "project":
            place("StairBulkhead", 3.4 * S, 4.2 * S, 2.7 * S, (150, 146, 138), variant="FB_ConcreteTrim", count=2 + int(b.area_m2 > 400))
            place("ElevatorHousing", 3.0 * S, 3.0 * S, 3.2 * S, (140, 138, 132), variant="FB_ConcreteTrim", count=1)
            place("RoofVent", 1.0 * S, 1.0 * S, 1.1 * S, (176, 178, 180), material="Metal", count=4)
        elif k in ("row", "commercial", "school"):
            place("RoofHatch", 1.2 * S, 1.2 * S, 1.0 * S, (140, 138, 132), variant="FB_ConcreteTrim")
            if b.area_m2 > 100:
                place("StairBulkhead", 2.4 * S, 2.8 * S, 2.4 * S, (160, 152, 140), variant="FB_ConcreteTrim")
            place("RoofVent", 0.8 * S, 0.8 * S, 0.9 * S, (176, 178, 180), material="Metal", count=2)
            if b.Hm > 12 and b.area_m2 > 90:
                spot = free_spot(3.4 * S, 3.4 * S)
                if spot:
                    base = 0.9 * S
                    for lx in (-1, 1):
                        for lz in (-1, 1):
                            f.add(scene.part("TankLeg", (0.12 * S, base, 0.12 * S),
                                             (spot[0] + lx * 1.2 * S, b.H + base / 2,
                                              spot[1] + lz * 1.2 * S), color=style.STEEL,
                                             material="Metal"))
                    th = 2.9 * S
                    f.add(scene.part("WaterTank", (th, 3.0 * S, 3.0 * S),
                                     (spot[0], b.H + base + th / 2, spot[1]), Rz90(),
                                     color=(112, 82, 54), material="WoodPlanks",
                                     shape=SHAPE_CYLINDER))
        else:
            place("RoofVent", 0.7 * S, 0.7 * S, 0.7 * S, (176, 178, 180), material="Metal")

    # ── facades ─────────────────────────────────────────────────────────────
    def fpart(self, scene, e, name, size, u, y, v, **kw):
        """Place a part in the edge's local frame: u along, v outward."""
        cx = e.p[0] + e.d[0] * u + e.n[0] * v
        cz = e.p[1] + e.d[1] * u + e.n[1] * v
        return scene.part(name, size, (cx, y, cz), basis(*e.d), **kw)

    def facade(self, scene, wins, det, b, e, rng):
        S = self.S
        if e.shared or e.L < 1.5 * S:
            return
        kind = b.kind
        if kind == "accessory":
            return
        spec = {
            "project": dict(bay=3.3, w=1.15, h=1.55, sill=0.95),
            "row": dict(bay=2.9, w=1.05, h=1.75, sill=0.85),
            "commercial": dict(bay=3.1, w=1.15, h=1.7, sill=0.9),
            "school": dict(bay=3.2, w=1.5, h=1.9, sill=0.9),
        }[kind]
        # ground floor treatment for street fronts of storefront buildings
        store = (kind == "commercial" and e.front and e.L >= 4.0 * S)
        if store:
            self.storefront(scene, det, b, e, rng)
        door_u = None
        if kind == "row" and e.front and e.L >= 4.3 * S and not e.hole:
            door_u = self.stoop(scene, det, b, e, rng)
        if kind == "commercial" and e.front and e.L >= 4.0 * S and not store:
            door_u = None

        nb = max(1, int(round(e.L / (spec["bay"] * S))))
        if e.L < 1.7 * S:
            return
        sp = e.L / nb
        w, h = spec["w"] * S, spec["h"] * S
        first = 1 if store else 0
        bars_ground = kind in ("project", "row", "school") and not store
        for fl in range(first, b.floors):
            base = b.levels[fl]
            fh = (b.levels[fl + 1] - base) if fl + 1 < b.floors else (b.H - base)
            wy = base + min(spec["sill"] * S, fh * 0.34) + h / 2
            if wy + h / 2 > base + fh - 0.35 * S:
                continue
            for k in range(nb):
                u = sp * (k + 0.5)
                if door_u is not None and abs(u - door_u) < 1.1 * S and fl == 0:
                    continue
                if door_u is not None and abs(u - door_u) < 0.9 * S and fl == 1 and kind == "row":
                    pass
                self.window(scene, wins, b, e, u, wy, w, h, rng, bars=(bars_ground and fl == 0),
                            lintel=(kind in ("project", "commercial", "school")))
        # cornice on street fronts of older buildings
        if kind in ("row", "commercial") and e.front:
            wd = 0.42 * S
            wins.add(seg_part(scene, "Cornice", e.p, e.q, wd, b.H - 0.05 * S, 0.34 * S,
                              off=wd / 2 - 0.02 * S, ext=0.0, color=b.trim,
                              material="Concrete", variant="FB_ConcreteTrim", shadow=False))
        # fire escapes: older 3+ storey buildings, on the street side
        if kind in ("row", "commercial") and e.front and b.floors >= 3 and e.L >= 4.5 * S:
            if kind == "commercial" or b.floors >= 4:
                self.fire_escape(scene, det, b, e, nb, sp, rng)

    def window(self, scene, f, b, e, u, y, w, h, rng, bars=False, lintel=False):
        S = self.S
        f.add(self.fpart(scene, e, "Frame", (w + 0.16 * S, h + 0.16 * S, 0.12 * S), u, y, 0.06 * S,
                         color=b.trim if b.kind != "project" else (205, 200, 186),
                         material="Concrete" if b.kind != "project" else "SmoothPlastic",
                         shadow=False))
        gc = pick([style.GLASS, (30, 40, 52), (40, 50, 62), (26, 34, 44)], rng.random())
        f.add(self.fpart(scene, e, "Glass", (w, h, 0.05 * S), u, y, 0.12 * S, color=gc,
                         material="Glass", reflectance=0.08, shadow=False))
        f.add(self.fpart(scene, e, "Sill", (w + 0.3 * S, 0.1 * S, 0.24 * S), u,
                         y - h / 2 - 0.1 * S, 0.12 * S, color=style.CONC_TRIM,
                         material="Concrete", variant="FB_ConcreteTrim", shadow=False))
        if lintel:
            f.add(self.fpart(scene, e, "Lintel", (w + 0.3 * S, 0.14 * S, 0.14 * S), u,
                             y + h / 2 + 0.12 * S, 0.07 * S, color=style.CONC_TRIM,
                             material="Concrete", variant="FB_ConcreteTrim", shadow=False))
        r = rng.random()
        if r < 0.34:
            # curtains / blinds drawn part-way
            frac = rng.choice((0.35, 0.5, 0.7, 1.0))
            col = pick([style.BLIND, (236, 232, 222), (190, 200, 214), (200, 170, 150),
                        (170, 186, 170)], rng.random())
            f.add(self.fpart(scene, e, "Blind", (w - 0.04 * S, h * frac, 0.03 * S), u,
                             y + h / 2 - h * frac / 2, 0.16 * S, color=col,
                             material="Fabric", shadow=False))
        elif r < 0.34 + (0.16 if b.kind == "project" else 0.22):
            f.add(self.fpart(scene, e, "ACUnit", (0.62 * S, 0.42 * S, 0.5 * S), u + rng.uniform(-0.1, 0.1) * w,
                             y - h / 2 + 0.34 * S, 0.12 * S + 0.25 * S, color=style.AC_GREY,
                             material="Metal", shadow=False))
        if bars:
            for i in range(3):
                bu = u - w / 2 + (i + 0.5) * w / 3
                f.add(self.fpart(scene, e, "Bar", (0.035 * S, h + 0.1 * S, 0.035 * S), bu, y,
                                 0.28 * S, color=(36, 38, 42), material="Metal", shadow=False))
            f.add(self.fpart(scene, e, "BarRail", (w + 0.1 * S, 0.035 * S, 0.035 * S), u, y,
                             0.28 * S, color=(36, 38, 42), material="Metal", shadow=False))

    # ── type specific bits ──────────────────────────────────────────────────
    def stoop(self, scene, f, b, e, rng):
        S = self.S
        u = e.L * (0.27 if hash01(b.id + "s") < 0.5 else 0.73)
        rise, run = 0.18 * S, 0.30 * S
        nrise = 6 if b.Hm > 7 else 5
        top = rise * nrise
        land = 1.1 * S
        wdt = 1.5 * S
        conc = dict(color=(150, 146, 138), material="Concrete", variant="FB_ConcreteTrim")
        # landing against the door, then treads running outward and down
        f.add(self.fpart(scene, e, "StoopLanding", (wdt, top, land), u, top / 2, land / 2, **conc))
        for j in range(1, nrise):
            v = land + (nrise - 1 - j) * run + run / 2
            f.add(self.fpart(scene, e, "StoopStep", (wdt, rise * j, run), u, rise * j / 2, v, **conc))
        for sgn in (-1, 1):
            f.add(self.fpart(scene, e, "StoopCheek", (0.18 * S, top + 0.25 * S, land),
                             u + sgn * (wdt / 2 + 0.09 * S), (top + 0.25 * S) / 2, land / 2,
                             color=(140, 136, 128), material="Concrete",
                             variant="FB_ConcreteTrim", shadow=False))
            f.add(self.fpart(scene, e, "StoopRailPost", (0.05 * S, 0.9 * S, 0.05 * S),
                             u + sgn * (wdt / 2 + 0.09 * S), top + 0.25 * S + 0.45 * S,
                             land - 0.1 * S, color=(30, 32, 34), material="Metal",
                             shadow=False))
        dh, dw = 2.15 * S, 1.0 * S
        f.add(self.fpart(scene, e, "DoorFrame", (dw + 0.3 * S, dh + 0.2 * S, 0.18 * S), u,
                         top + (dh + 0.2 * S) / 2, 0.09 * S, color=b.trim, material="Concrete",
                         variant="FB_ConcreteTrim", shadow=False))
        f.add(self.fpart(scene, e, "Door", (dw, dh, 0.08 * S), u, top + dh / 2,
                         0.16 * S, color=pick([(54, 38, 30), (30, 52, 40), (48, 36, 60),
                                               (74, 30, 28)], hash01(b.id + "d")),
                         material="Wood", shadow=False))
        return u

    def storefront(self, scene, f, b, e, rng):
        S = self.S
        gh = b.ground_h
        L = e.L
        # sign band, then glazing between a bulkhead and the sign
        sign_h = 0.75 * S
        sign_col = pick(style.SIGN_COLORS, hash01(b.id + "g"))
        f.add(self.fpart(scene, e, "StoreSign", (L - 0.2 * S, sign_h, 0.18 * S), L / 2,
                         gh - sign_h / 2 - 0.12 * S, 0.09 * S, color=sign_col,
                         material="SmoothPlastic", shadow=False))
        f.add(self.fpart(scene, e, "Bulkhead", (L - 0.2 * S, 0.65 * S, 0.14 * S), L / 2,
                         0.325 * S, 0.07 * S, color=(88, 88, 92), material="Granite",
                         variant="FB_GraniteCurb", shadow=False))
        glass_h = gh - sign_h - 0.65 * S - 0.35 * S
        gy = 0.65 * S + glass_h / 2
        npane = max(1, int(round((L - 1.2 * S) / (1.5 * S))))
        door_pane = npane - 1 if hash01(b.id + "p") > 0.5 else 0
        gate = hash01(b.id + "r") < 0.55
        pw = (L - 0.2 * S) / npane
        for i in range(npane):
            cu = 0.1 * S + pw * (i + 0.5)
            f.add(self.fpart(scene, e, "StoreGlass", (pw - 0.08 * S, glass_h, 0.05 * S), cu, gy,
                             0.1 * S, color=(54, 62, 70), material="Glass", transparency=0.15,
                             reflectance=0.1, shadow=False))
            f.add(self.fpart(scene, e, "Mullion", (0.07 * S, glass_h, 0.1 * S),
                             0.1 * S + pw * i, gy, 0.1 * S, color=(34, 34, 38),
                             material="Metal", shadow=False))
            if i == door_pane:
                f.add(self.fpart(scene, e, "StoreDoor", (min(1.0 * S, pw - 0.2 * S), 2.1 * S, 0.07 * S),
                                 cu, 0.65 * S + 1.05 * S - 0.0, 0.14 * S, color=(36, 38, 42),
                                 material="Metal", shadow=False))
        f.add(self.fpart(scene, e, "Mullion", (0.07 * S, glass_h, 0.1 * S), 0.1 * S + L - 0.2 * S,
                         gy, 0.1 * S, color=(34, 34, 38), material="Metal", shadow=False))
        if gate:
            # security shutter pulled down over the glazing, leaving the door side clear
            if npane > 1:
                gw = L - 0.3 * S - pw
                gu0 = 0.15 * S + (pw if door_pane == 0 else 0)
            else:
                gw, gu0 = L - 0.3 * S, 0.15 * S
            f.add(self.fpart(scene, e, "RollGate", (gw, glass_h + 0.55 * S, 0.07 * S),
                             gu0 + gw / 2, (glass_h + 0.55 * S) / 2 + 0.1 * S, 0.22 * S,
                             color=(118, 120, 124), material="Metal", variant="FB_RollGate",
                             shadow=False))
            f.add(self.fpart(scene, e, "GateBox", (gw, 0.3 * S, 0.3 * S), gu0 + gw / 2,
                             0.1 * S + glass_h + 0.55 * S + 0.1 * S, 0.24 * S,
                             color=(100, 102, 106), material="Metal", shadow=False))
        elif hash01(b.id + "w") < 0.4:
            # fabric awning
            rot = tilt_x(basis(*e.d), 14)
            col = pick(style.AWNING_COLORS, hash01(b.id + "n"))
            cx = e.p[0] + e.d[0] * (L / 2) + e.n[0] * 0.55 * S
            cz = e.p[1] + e.d[1] * (L / 2) + e.n[1] * 0.55 * S
            f.add(scene.part("Awning", (L - 0.5 * S, 0.05 * S, 1.2 * S),
                             (cx, gh - sign_h - 0.15 * S - 0.1 * S, cz), rot, color=col,
                             material="Fabric", shadow=False))

    def fire_escape(self, scene, f, b, e, nb, sp, rng):
        S = self.S
        # platforms across the middle two bays, stacked from floor 2 up
        k0 = max(0, nb // 2 - 1) if nb > 1 else 0
        k1 = min(nb - 1, k0 + 1)
        u0, u1 = sp * (k0 + 0.5) - 0.9 * S, sp * (k1 + 0.5) + 0.9 * S
        if nb == 1:
            u0, u1 = e.L / 2 - 1.2 * S, e.L / 2 + 1.2 * S
        wl = u1 - u0
        uc = (u0 + u1) / 2
        col = (30, 32, 36)
        for fl in range(1, b.floors):
            y = b.levels[fl] + 0.12 * S
            f.add(self.fpart(scene, e, "FEPlatform", (wl, 0.06 * S, 1.0 * S), uc, y, 0.62 * S,
                             color=col, material="DiamondPlate", shadow=False))
            f.add(self.fpart(scene, e, "FERailTop", (wl, 0.04 * S, 0.04 * S), uc,
                             y + 0.95 * S, 1.1 * S, color=col, material="Metal", shadow=False))
            f.add(self.fpart(scene, e, "FERailMid", (wl, 0.03 * S, 0.03 * S), uc,
                             y + 0.5 * S, 1.1 * S, color=col, material="Metal", shadow=False))
            for sgn in (-1, 1):
                f.add(self.fpart(scene, e, "FEPost", (0.04 * S, 0.95 * S, 0.04 * S),
                                 uc + sgn * (wl / 2 - 0.02 * S), y + 0.48 * S, 1.1 * S,
                                 color=col, material="Metal", shadow=False))
                f.add(self.fpart(scene, e, "FESide", (0.03 * S, 0.04 * S, 1.0 * S),
                                 uc + sgn * (wl / 2 - 0.02 * S), y + 0.95 * S, 0.62 * S,
                                 color=col, material="Metal", shadow=False))
            # drop ladder to the platform below
            if fl >= 2:
                run = b.levels[fl] - b.levels[fl - 1]
                for sgn in (-1, 1):
                    f.add(self.fpart(scene, e, "FELadderRail", (0.03 * S, run, 0.03 * S),
                                     u1 - 0.55 * S + sgn * 0.22 * S, y - run / 2, 0.62 * S,
                                     color=col, material="Metal", shadow=False))
                f.add(self.fpart(scene, e, "FELadderRungs", (0.44 * S, run * 0.92, 0.02 * S),
                                 u1 - 0.55 * S, y - run / 2, 0.62 * S, color=col,
                                 material="DiamondPlate", transparency=0.55, shadow=False))

    def project_entrances(self, scene, f, b, edges, rng):
        S = self.S
        cands = []
        n = len(edges)
        outer = [e for e in edges if not e.hole]
        m = len(outer)
        for i, e in enumerate(outer):
            if e.shared or not (2.4 * S <= e.L <= 7.5 * S):
                continue
            pe, ne = outer[i - 1], outer[(i + 1) % m]
            def perp(a, c):
                return abs(a.d[0] * c.d[0] + a.d[1] * c.d[1]) < 0.3
            def convex(a, c):
                # cross of consecutive directions; ring is oriented so convex = positive
                return (a.d[0] * c.d[1] - a.d[1] * c.d[0]) < 0
            if perp(pe, e) and perp(e, ne) and convex(pe, e) and convex(e, ne):
                cands.append(e)
        # keep a spread: >= 14 m apart, at most 5 per building
        chosen = []
        for e in sorted(cands, key=lambda e: -e.L):
            if all(math.dist(e.mid, c.mid) > 14 * S for c in chosen):
                chosen.append(e)
            if len(chosen) >= 5:
                break
        for e in chosen:
            u = e.L / 2
            dh, dw = 2.25 * S, 1.7 * S
            f.add(self.fpart(scene, e, "EntranceFrame", (dw + 0.35 * S, dh + 0.25 * S, 0.2 * S),
                             u, (dh + 0.25 * S) / 2, 0.1 * S, color=(80, 80, 84),
                             material="Metal", shadow=False))
            for sgn in (-1, 1):
                f.add(self.fpart(scene, e, "EntranceDoor", (dw / 2 - 0.03 * S, dh - 0.1 * S, 0.06 * S),
                                 u + sgn * dw / 4, dh / 2, 0.17 * S, color=(46, 62, 74),
                                 material="Glass", transparency=0.1, shadow=False))
            f.add(self.fpart(scene, e, "EntranceCanopy", (dw + 1.2 * S, 0.14 * S, 1.2 * S),
                             u, dh + 0.55 * S, 0.62 * S, color=(150, 146, 138),
                             material="Concrete", variant="FB_ConcreteTrim"))
            f.add(self.fpart(scene, e, "EntrancePad", (dw + 1.6 * S, 0.1 * S, 1.8 * S),
                             u, 0.05 * S, 0.9 * S, color=style.SIDEWALK,
                             material="Concrete", variant="FB_SidewalkConcrete",
                             shadow=False))
            # stair window above the door on each floor
            for fl in range(1, b.floors):
                y = b.levels[fl] - 0.9 * S
                f.add(self.fpart(scene, e, "StairWindow", (0.8 * S, 1.3 * S, 0.05 * S), u, y,
                                 0.1 * S, color=(150, 170, 180), material="Glass",
                                 transparency=0.25, shadow=False))

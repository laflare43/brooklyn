"""
osmdata.py — read an OpenStreetMap .osm export and return everything in
Roblox ground coordinates (X east, Z south, studs).
"""
import math
import xml.etree.ElementTree as ET

from . import geo


class World:
    def __init__(self, path, lat0, lon0, stud_m=0.30):
        self.stud_m = stud_m
        self.S = 1.0 / stud_m                 # studs per metre
        self.lat0, self.lon0 = lat0, lon0
        self.kx = 111320.0 * math.cos(math.radians(lat0))
        self.ky = 110574.0
        root = ET.parse(path).getroot()
        b = root.find("bounds")
        self.nodes = {}
        for n in root.iter("node"):
            self.nodes[n.get("id")] = (float(n.get("lat")), float(n.get("lon")))
        self.node_tags = {}
        for n in root.iter("node"):
            tags = {t.get("k"): t.get("v") for t in n.findall("tag")}
            if tags:
                self.node_tags[n.get("id")] = tags
        self.ways = {}
        for w in root.iter("way"):
            self.ways[w.get("id")] = {
                "id": w.get("id"),
                "refs": [nd.get("ref") for nd in w.findall("nd")],
                "tags": {t.get("k"): t.get("v") for t in w.findall("tag")},
            }
        self.relations = []
        for r in root.iter("relation"):
            self.relations.append({
                "id": r.get("id"),
                "tags": {t.get("k"): t.get("v") for t in r.findall("tag")},
                "members": [(m.get("type"), m.get("ref"), m.get("role"))
                            for m in r.findall("member")],
            })
        if b is not None:
            c = [self.to_xz(float(b.get("minlat")), float(b.get("minlon"))),
                 self.to_xz(float(b.get("maxlat")), float(b.get("maxlon")))]
            self.box = (min(c[0][0], c[1][0]), min(c[0][1], c[1][1]),
                        max(c[0][0], c[1][0]), max(c[0][1], c[1][1]))
        else:
            self.box = (-500, -500, 500, 500)
        self._classify()

    # -- projection -----------------------------------------------------------
    def to_xz(self, lat, lon):
        return ((lon - self.lon0) * self.kx * self.S,
                -(lat - self.lat0) * self.ky * self.S)

    def ring(self, way):
        pts = [self.to_xz(*self.nodes[r]) for r in way["refs"] if r in self.nodes]
        if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-6:
            pts.pop()
        return pts

    def line(self, way):
        return [self.to_xz(*self.nodes[r]) for r in way["refs"] if r in self.nodes]

    # -- classification ---------------------------------------------------------
    def _classify(self):
        self.buildings = []     # dicts: id, outer, holes, tags
        self.roads = []         # dicts: id, name, kind, oneway, pts, tags
        self.sidewalks = []     # polylines
        self.crossings = []     # dicts: pts, markings, signals
        self.areas = []         # dicts: kind, name, ring, tags
        self.signal_nodes = []
        claimed = set()

        # multipolygon buildings first, so their member ways aren't double-counted
        for rel in self.relations:
            t = rel["tags"]
            if t.get("type") == "multipolygon" and "building" in t:
                outers, inners = [], []
                for typ, ref, role in rel["members"]:
                    w = self.ways.get(ref)
                    if typ != "way" or not w:
                        continue
                    claimed.add(ref)
                    ring = self.ring(w)
                    if len(ring) < 3:
                        continue
                    (inners if role == "inner" else outers).append(ring)
                for k, outer in enumerate(outers):
                    holes = [h for h in inners
                             if geo.point_in_poly(geo.centroid(h), outer)]
                    self.buildings.append({"id": "r%s_%d" % (rel["id"], k),
                                           "outer": outer, "holes": holes, "tags": t})

        for wid, w in self.ways.items():
            if wid in claimed:
                continue
            t = w["tags"]
            if "building" in t:
                ring = self.ring(w)
                if len(ring) >= 3:
                    self.buildings.append({"id": wid, "outer": ring, "holes": [], "tags": t})
                continue
            hw = t.get("highway")
            if hw in ("residential", "tertiary", "secondary", "primary", "service",
                      "unclassified"):
                self.roads.append({"id": wid, "name": t.get("name", ""), "kind": hw,
                                   "oneway": t.get("oneway") == "yes",
                                   "private": t.get("access") == "private",
                                   "pts": self.line(w), "tags": t})
            elif hw == "footway":
                if t.get("footway") == "crossing":
                    self.crossings.append({"pts": self.line(w),
                                           "markings": t.get("crossing:markings", "zebra"),
                                           "signals": t.get("crossing") == "traffic_signals",
                                           "tags": t})
                else:
                    self.sidewalks.append(self.line(w))
            elif t.get("leisure") or t.get("amenity") or t.get("landuse"):
                kind = t.get("leisure") or t.get("amenity") or t.get("landuse")
                ring = self.ring(w)
                if len(ring) >= 3:
                    self.areas.append({"kind": kind, "name": t.get("name", ""),
                                       "ring": ring, "tags": t})
        for nid, tags in self.node_tags.items():
            if tags.get("highway") == "traffic_signals":
                self.signal_nodes.append(self.to_xz(*self.nodes[nid]))

    def drop_outside(self, margin_m=6.0):
        """Drop buildings whose centre lies outside the mapped box (+ margin).
        They have no streets or sidewalks around them in this export, so they
        would stand alone on bare ground (e.g. J.H.S. 292, 99 % outside)."""
        x0, z0, x1, z1 = self.clip_box(margin_m)
        keep, dropped = [], []
        for b in self.buildings:
            cx, cz = geo.centroid(b["outer"])
            (keep if (x0 <= cx <= x1 and z0 <= cz <= z1) else dropped).append(b)
        self.buildings = keep
        # open areas (schoolyard, parks...) follow the same rule
        self.areas = [a for a in self.areas
                      if x0 <= geo.centroid(a["ring"])[0] <= x1 and z0 <= geo.centroid(a["ring"])[1] <= z1]
        return dropped

    def clip_box(self, margin_m=0.0):
        m = margin_m * self.S
        x0, z0, x1, z1 = self.box
        return (x0 - m, z0 - m, x1 + m, z1 + m)

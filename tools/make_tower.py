#!/usr/bin/env python3
"""
make_tower.py — generates a Brooklyn housing-project tower as a Roblox .rbxmx

    python3 tools/make_tower.py                      # -> models/HousingTower.rbxmx
    python3 tools/make_tower.py --floors 6 --sign "TILDEN HOUSES" --address 1650

Import in Studio: right-click Workspace (or drag the file into the viewport)
> Insert from File... > pick the .rbxmx.  The model's pivot (the invisible
"Pivot" part) sits at the centre of the ground floor, so it drops on the
ground where you place it.  The FRONT of the building faces +Z.

Everything is built from anchored Parts (no meshes, no unions), so it imports
without any asset permissions.
"""
import argparse
import math
import random
import sys
from xml.sax.saxutils import escape

# ─── ROBLOX ENUM VALUES (as stored in rbxmx) ─────────────────────────────────
MAT = {
    "Plastic": 256, "SmoothPlastic": 272, "Neon": 288, "Wood": 512,
    "WoodPlanks": 528, "Slate": 800, "Concrete": 816, "Granite": 832,
    "Brick": 848, "Metal": 1088, "DiamondPlate": 1056, "Glass": 1568,
}
SHAPE_BALL, SHAPE_BLOCK, SHAPE_CYLINDER = 0, 1, 2
NORMAL_BACK = 2          # Enum.NormalId.Back  (= local +Z face of a part)
FONT_GOTHAM_BOLD = 19

# ─── PALETTE ─────────────────────────────────────────────────────────────────
BRICK = (128, 70, 52)
BUFF = (196, 188, 168)      # trim, bands, corner pillars
CONC = (150, 148, 142)
CONC_DARK = (110, 108, 104)
DARK = (40, 40, 44)
FRAME = (58, 60, 64)
GLASS = (36, 48, 62)
LIT = (255, 214, 140)
BLIND = (205, 198, 180)
AC = (176, 178, 180)
ROOF = (62, 62, 66)
SIGN_BG = (26, 26, 28)
CREAM = (220, 212, 198)
RED = (190, 20, 20)
TANK = (120, 84, 52)


# ─── TINY SCENE GRAPH ────────────────────────────────────────────────────────
class Node:
    _count = 0

    def __init__(self, cls, name, props="", children=None):
        Node._count += 1
        self.ref = "RBX%d" % Node._count
        self.cls, self.name, self.props = cls, name, props
        self.children = children if children is not None else []

    def add(self, child):
        self.children.append(child)
        return child

    def xml(self, out, depth=0):
        pad = "  " * depth
        out.append('%s<Item class="%s" referent="%s">' % (pad, self.cls, self.ref))
        out.append("%s  <Properties>" % pad)
        out.append('%s    <string name="Name">%s</string>' % (pad, escape(self.name)))
        if self.props:
            out.append(self.props)
        out.append("%s  </Properties>" % pad)
        for c in self.children:
            c.xml(out, depth + 1)
        out.append("%s</Item>" % pad)


def f(v):
    s = "%.5f" % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def color3u8(c):
    return 0xFF000000 | (c[0] << 16) | (c[1] << 8) | c[2]


def Ry(deg):
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return ((c, 0, s), (0, 1, 0), (-s, 0, c))


def Rz(deg):
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


IDENT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def matvec(R, v):
    return tuple(sum(R[i][j] * v[j] for j in range(3)) for i in range(3))


PARTS = []   # (name, size, pos, rot) — kept for the preview and sanity checks


def make_part(name, size, pos, rot=IDENT, color=BRICK, material="SmoothPlastic",
              transparency=0.0, collide=True, shape=SHAPE_BLOCK, query=True,
              children=None):
    assert all(s > 0 for s in size), "non-positive size on %s: %r" % (name, size)
    r = rot
    props = []
    props.append('    <bool name="Anchored">true</bool>')
    props.append('    <bool name="CanCollide">%s</bool>' % ("true" if collide else "false"))
    props.append('    <bool name="CanQuery">%s</bool>' % ("true" if query else "false"))
    props.append('    <bool name="CanTouch">%s</bool>' % ("true" if collide else "false"))
    props.append(
        "    <CoordinateFrame name=\"CFrame\"><X>%s</X><Y>%s</Y><Z>%s</Z>"
        "<R00>%s</R00><R01>%s</R01><R02>%s</R02>"
        "<R10>%s</R10><R11>%s</R11><R12>%s</R12>"
        "<R20>%s</R20><R21>%s</R21><R22>%s</R22></CoordinateFrame>"
        % (f(pos[0]), f(pos[1]), f(pos[2]),
           f(r[0][0]), f(r[0][1]), f(r[0][2]),
           f(r[1][0]), f(r[1][1]), f(r[1][2]),
           f(r[2][0]), f(r[2][1]), f(r[2][2])))
    props.append('    <Color3uint8 name="Color3uint8">%d</Color3uint8>' % color3u8(color))
    props.append('    <token name="Material">%d</token>' % MAT[material])
    props.append('    <float name="Reflectance">0</float>')
    props.append('    <float name="Transparency">%s</float>' % f(transparency))
    props.append('    <Vector3 name="size"><X>%s</X><Y>%s</Y><Z>%s</Z></Vector3>'
                 % (f(size[0]), f(size[1]), f(size[2])))
    props.append('    <token name="shape">%d</token>' % shape)
    for surf in ("Top", "Bottom", "Left", "Right", "Front", "Back"):
        props.append('    <token name="%sSurface">0</token>' % surf)
    node = Node("Part", name, "\n".join(props), children)
    PARTS.append((name, size, pos, rot, color, transparency, shape))
    return node


class Frame:
    """A local coordinate frame: +Z is 'outward' for the face it describes."""

    def __init__(self, origin, theta=0.0):
        self.origin = origin
        self.R = Ry(theta)

    def world(self, local):
        v = matvec(self.R, local)
        return (self.origin[0] + v[0], self.origin[1] + v[1], self.origin[2] + v[2])

    def part(self, name, size, local, **kw):
        return make_part(name, size, self.world(local), self.R, **kw)


def point_light(color, brightness, rng):
    return Node(
        "PointLight", "Light",
        '    <float name="Brightness">%s</float>\n'
        '    <Color3 name="Color"><R>%s</R><G>%s</G><B>%s</B></Color3>\n'
        '    <bool name="Enabled">true</bool>\n'
        '    <float name="Range">%s</float>\n'
        '    <bool name="Shadows">false</bool>'
        % (f(brightness), f(color[0] / 255), f(color[1] / 255), f(color[2] / 255), f(rng)))


def sign_gui(text, canvas=(1200, 200), text_color=CREAM):
    label = Node(
        "TextLabel", "Text",
        '    <float name="BackgroundTransparency">1</float>\n'
        '    <UDim2 name="Size"><XS>1</XS><XO>0</XO><YS>1</YS><YO>0</YO></UDim2>\n'
        '    <string name="Text">%s</string>\n'
        '    <Color3 name="TextColor3"><R>%s</R><G>%s</G><B>%s</B></Color3>\n'
        '    <bool name="TextScaled">true</bool>\n'
        '    <token name="Font">%d</token>'
        % (escape(text), f(text_color[0] / 255), f(text_color[1] / 255),
           f(text_color[2] / 255), FONT_GOTHAM_BOLD))
    return Node(
        "SurfaceGui", "SignGui",
        '    <token name="Face">%d</token>\n'
        '    <Vector2 name="CanvasSize"><X>%d</X><Y>%d</Y></Vector2>\n'
        '    <float name="LightInfluence">0</float>' % (NORMAL_BACK, canvas[0], canvas[1]),
        [label])


# ─── THE BUILDING ────────────────────────────────────────────────────────────
def build(cfg):
    rng = random.Random(cfg["seed"])
    W, D = cfg["width"], cfg["depth"]
    FLOORS, LOBBY_H, FLOOR_H = cfg["floors"], cfg["lobby_h"], cfg["floor_h"]
    H = LOBBY_H + FLOORS * FLOOR_H
    detail = cfg["detail"]

    model = Node("Model", cfg["name"])
    pivot = model.add(make_part("Pivot", (1, 0.2, 1), (0, 0.1, 0), color=DARK,
                                transparency=1, collide=False, query=False))
    model.props = '    <Ref name="PrimaryPart">%s</Ref>' % pivot.ref

    structure = model.add(Node("Folder", "Structure"))
    windows = model.add(Node("Folder", "Windows"))
    entrance = model.add(Node("Folder", "Entrance"))
    roof = model.add(Node("Folder", "Roof"))
    service = model.add(Node("Folder", "BackDoor"))

    # Body, set into the ground a little so a slope never shows a gap.
    structure.add(make_part("Body", (W, H + 2, D), (0, (H - 2) / 2, 0),
                            color=BRICK, material="Brick"))
    structure.add(make_part("Plinth", (W + 3.0, 3.2, D + 3.0), (0, -0.4, 0),
                            color=CONC_DARK, material="Concrete"))

    # Corner pillars.
    for sx in (-1, 1):
        for sz in (-1, 1):
            structure.add(make_part("CornerPillar", (2.4, H, 2.4),
                                    (sx * W / 2, H / 2, sz * D / 2),
                                    color=BUFF, material="Concrete"))

    # Floor bands (every few storeys).
    # (Not at FLOORS: a full slab there would bury the roof surface; the
    # parapet and coping finish the roofline instead.)
    for fl in range(0, FLOORS, cfg["band_every"]):
        structure.add(make_part("Band", (W + 0.8, 0.7, D + 0.8),
                                (0, LOBBY_H + fl * FLOOR_H, 0),
                                color=BUFF, material="Concrete"))

    # Faces: (name, outward-Z frame, face width, columns)
    faces = [
        ("Front", Frame((0, 0, D / 2), 0), W, cfg["cols_long"]),
        ("Back", Frame((0, 0, -D / 2), 180), W, cfg["cols_long"]),
        ("Right", Frame((W / 2, 0, 0), 90), D, cfg["cols_side"]),
        ("Left", Frame((-W / 2, 0, 0), -90), D, cfg["cols_side"]),
    ]

    def window(folder, fr, u, y, w, h, allow_ac=True, bars=False):
        lit = rng.random() < cfg["lit_chance"]
        folder.add(fr.part("Frame", (w + 0.8, h + 0.8, 0.5), (u, y, 0.25),
                           color=FRAME, material="Metal", collide=False))
        glass_col = LIT if lit else GLASS
        folder.add(fr.part("Glass", (w, h, 0.3), (u, y, 0.55), color=glass_col,
                           material="SmoothPlastic" if lit else "Glass", collide=False))
        folder.add(fr.part("Sill", (w + 1.4, 0.4, 1.0), (u, y - h / 2 - 0.6, 0.5),
                           color=BUFF, material="Concrete", collide=False))
        if detail and not lit:
            if rng.random() < 0.35:
                folder.add(fr.part("Blind", (w - 0.3, h * 0.45, 0.06),
                                   (u, y + h * 0.25, 0.74), color=BLIND, collide=False))
            if rng.random() < 0.3:
                folder.add(fr.part("Mullion", (0.25, h, 0.15), (u, y, 0.75),
                                   color=FRAME, material="Metal", collide=False))
        if allow_ac and not lit and rng.random() < cfg["ac_chance"]:
            folder.add(fr.part("ACUnit", (3.0, 1.9, 1.6), (u, y - h / 2 + 1.15, 1.5),
                               color=AC, collide=False))
            folder.add(fr.part("ACGrille", (2.4, 1.0, 0.1), (u, y - h / 2 + 1.15, 2.33),
                               color=DARK, collide=False))
        if bars:
            n = 5
            for i in range(n):
                bu = u - w / 2 + 0.35 + i * (w - 0.7) / (n - 1)
                folder.add(fr.part("Bar", (0.18, h, 0.18), (bu, y, 0.9),
                                   color=FRAME, material="Metal", collide=False))

    for fname, fr, fw, cols in faces:
        ff = windows.add(Node("Folder", fname))
        colw = fw / cols
        win_w = min(4.0, colw * 0.5)
        win_h = 5.2
        # Residential floors.
        for fl in range(FLOORS):
            y = LOBBY_H + fl * FLOOR_H + FLOOR_H * 0.5 + 0.2
            for c in range(cols):
                u = -fw / 2 + colw * (c + 0.5)
                window(ff, fr, u, y, win_w, win_h)
        # Pilaster strips between window columns.
        for c in range(1, cols):
            u = -fw / 2 + colw * c
            ff.add(fr.part("Pilaster", (0.9, H - LOBBY_H - 1.0, 0.3),
                           (u, LOBBY_H + (H - LOBBY_H - 1.0) / 2 + 0.5, 0.15),
                           color=BUFF, material="Concrete", collide=False))
        # Ground floor.
        if fname == "Front":
            for u in (-28.0, -21.0, -14.0, 14.0, 21.0, 28.0):
                if abs(u) + 2.0 + 0.4 < W / 2 - 1.3:
                    window(ff, fr, u, 7.0, 4.0, 4.6, allow_ac=False, bars=True)
        else:
            for c in range(cols):
                u = -fw / 2 + colw * (c + 0.5)
                if fname == "Back" and abs(u) < 4.0:
                    continue   # room for the service door
                window(ff, fr, u, 7.0, win_w, 4.6, allow_ac=False, bars=True)

    # ── Front entrance ──────────────────────────────────────────────────────
    fr = faces[0][1]
    door_w, door_h = 8.0, 8.5
    plat_top = 1.2
    entrance.add(fr.part("Platform", (18, 1.2, 8), (0, 0.6, 4),
                         color=CONC, material="Concrete"))
    entrance.add(fr.part("StepUpper", (18, 0.8, 1.4), (0, 0.4, 8.7),
                         color=CONC, material="Concrete"))
    entrance.add(fr.part("StepLower", (18, 0.4, 1.6), (0, 0.2, 10.2),
                         color=CONC, material="Concrete"))
    entrance.add(fr.part("DoorRecess", (door_w + 1.6, door_h + 1.0, 0.6),
                         (0, plat_top + (door_h + 1.0) / 2, 0.3),
                         color=DARK, material="Metal", collide=False))
    pw = door_w / 2 - 0.2
    for sgn in (-1, 1):
        cu = sgn * (door_w / 4)
        entrance.add(fr.part("DoorFrame", (pw + 0.3, door_h, 0.15),
                             (cu, plat_top + door_h / 2, 0.55), color=FRAME,
                             material="Metal", collide=False))
        entrance.add(fr.part("DoorGlass", (pw, door_h - 0.4, 0.2),
                             (cu, plat_top + door_h / 2, 0.68), color=GLASS,
                             material="Glass", transparency=0.15, collide=False))
        entrance.add(fr.part("DoorHandle", (0.2, 2.2, 0.25),
                             (sgn * 0.7, plat_top + 4.0, 0.95), color=CONC,
                             material="Metal", collide=False))
    for sgn in (-1, 1):
        entrance.add(fr.part("CanopyColumn", (1.2, 10.0, 1.2),
                             (sgn * 8.2, plat_top + 5.0, 7.2),
                             color=BUFF, material="Concrete"))
    entrance.add(fr.part("Canopy", (door_w + 10, 0.8, 8.0), (0, 11.6, 4.0),
                         color=CONC, material="Concrete"))
    entrance.add(fr.part("CanopyFascia", (door_w + 10, 1.0, 0.4), (0, 11.5, 8.0),
                         color=BUFF, material="Concrete"))
    for sgn in (-1, 1):
        lamp = fr.part("CanopyLamp", (1.0, 0.3, 1.0), (sgn * 5.0, 11.05, 4.5),
                       color=LIT, material="Neon", collide=False,
                       children=[point_light((255, 214, 150), 1.4, 24)])
        entrance.add(lamp)
    sign = fr.part("Sign", (door_w + 8, 1.9, 0.3), (0, 12.95, 0.15),
                   color=SIGN_BG, material="SmoothPlastic", collide=False,
                   children=[sign_gui(cfg["sign"])])
    entrance.add(sign)
    plaque = fr.part("AddressPlaque", (2.6, 2.6, 0.3), (6.4, 6.0, 0.15),
                     color=SIGN_BG, material="SmoothPlastic", collide=False,
                     children=[sign_gui(str(cfg["address"]), canvas=(400, 400))])
    entrance.add(plaque)

    # ── Back service door ───────────────────────────────────────────────────
    br = faces[1][1]
    service.add(br.part("StoopSlab", (7, 1.0, 3.5), (0, 0.5, 1.75),
                        color=CONC, material="Concrete"))
    service.add(br.part("ServiceDoorFrame", (4.8, 8.4, 0.5), (0, 1.0 + 4.2, 0.25),
                        color=FRAME, material="Metal", collide=False))
    service.add(br.part("ServiceDoor", (4.0, 7.8, 0.3), (0, 1.0 + 3.9, 0.55),
                        color=(70, 74, 78), material="Metal", collide=False))
    service.add(br.part("ServiceCanopy", (6.4, 0.4, 2.2), (0, 10.2, 1.1),
                        color=FRAME, material="Metal", collide=False))

    # ── Roof ────────────────────────────────────────────────────────────────
    roof.add(make_part("RoofSurface", (W - 1.0, 0.3, D - 1.0), (0, H + 0.15, 0),
                       color=ROOF, material="Slate"))
    for sz in (-1, 1):
        roof.add(make_part("ParapetLong", (W + 0.6, 3.0, 1.0),
                           (0, H + 1.5, sz * (D / 2 - 0.2)),
                           color=BRICK, material="Brick"))
        roof.add(make_part("CopingLong", (W + 1.0, 0.4, 1.4),
                           (0, H + 3.2, sz * (D / 2 - 0.2)),
                           color=BUFF, material="Concrete"))
    for sx in (-1, 1):
        roof.add(make_part("ParapetShort", (1.0, 3.0, D - 1.4),
                           (sx * (W / 2 - 0.2), H + 1.5, 0),
                           color=BRICK, material="Brick"))
        roof.add(make_part("CopingShort", (1.4, 0.4, D - 0.6),
                           (sx * (W / 2 - 0.2), H + 3.2, 0),
                           color=BUFF, material="Concrete"))

    bx, bz = W * 0.18, -D * 0.12
    roof.add(make_part("Bulkhead", (16, 9, 9), (bx, H + 0.3 + 4.5, bz),
                       color=CONC, material="Concrete"))
    roof.add(make_part("BulkheadCap", (16.8, 0.6, 9.8), (bx, H + 0.3 + 9.3, bz),
                       color=BUFF, material="Concrete"))
    roof.add(make_part("BulkheadDoor", (3.2, 6.4, 0.3),
                       (bx, H + 0.3 + 3.2, bz + 4.65), color=FRAME, material="Metal",
                       collide=False))
    # Antenna with a red aviation light.
    cyl = Rz(90)
    roof.add(make_part("Antenna", (14, 0.5, 0.5), (bx, H + 0.3 + 9.6 + 7, bz), rot=cyl,
                       color=FRAME, material="Metal", shape=SHAPE_CYLINDER))
    roof.add(make_part("AviationLight", (1.1, 1.1, 1.1),
                       (bx, H + 0.3 + 9.6 + 14.3, bz), color=RED, material="Neon",
                       shape=SHAPE_BALL, collide=False,
                       children=[point_light(RED, 2.0, 30)]))
    # Water tank on legs.
    tx, tz = -W * 0.22, D * 0.1
    leg = 4.5
    for lx in (-2.6, 2.6):
        for lz in (-2.6, 2.6):
            roof.add(make_part("TankLeg", (0.6, leg, 0.6),
                               (tx + lx, H + 0.3 + leg / 2, tz + lz),
                               color=FRAME, material="Metal"))
    roof.add(make_part("WaterTank", (10.0, 8.0, 8.0), (tx, H + 0.3 + leg + 5.0, tz),
                       rot=cyl, color=TANK, material="WoodPlanks",
                       shape=SHAPE_CYLINDER))
    roof.add(make_part("TankLid", (0.5, 8.4, 8.4), (tx, H + 0.3 + leg + 10.25, tz),
                       rot=cyl, color=DARK, material="Metal", shape=SHAPE_CYLINDER))
    # Vents and units.
    vents = [(-W * 0.38, -D * 0.2, 3, 2.4, 3), (-W * 0.3, D * 0.28, 4, 2, 2.6),
             (W * 0.05, D * 0.25, 3, 1.6, 3), (W * 0.36, D * 0.2, 5, 2.6, 3.4),
             (W * 0.4, -D * 0.28, 2.4, 1.4, 2.4), (-W * 0.05, -D * 0.25, 4, 2.2, 3)]
    for i, (vx, vz, sx, sy, sz) in enumerate(vents):
        roof.add(make_part("RoofUnit", (sx, sy, sz), (vx, H + 0.3 + sy / 2, vz),
                           color=AC if i % 2 else CONC, material="Metal"))

    return model, H


def to_rbxmx(model):
    out = [
        '<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">',
        '  <Meta name="ExplicitAutoJoints">true</Meta>',
    ]
    model.xml(out, 1)
    out.append("</roblox>")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="models/HousingTower.rbxmx")
    ap.add_argument("--name", default="Housing Tower")
    ap.add_argument("--sign", default="BROWNSVILLE HOUSES")
    ap.add_argument("--address", default="310")
    ap.add_argument("--floors", type=int, default=14)
    ap.add_argument("--width", type=float, default=64.0)
    ap.add_argument("--depth", type=float, default=30.0)
    ap.add_argument("--lobby-height", type=float, default=14.0)
    ap.add_argument("--floor-height", type=float, default=11.0)
    ap.add_argument("--cols-long", type=int, default=9)
    ap.add_argument("--cols-side", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-detail", action="store_true",
                    help="skip blinds/mullions (fewer parts)")
    a = ap.parse_args()

    cfg = dict(name=a.name, sign=a.sign, address=a.address, floors=a.floors,
               width=a.width, depth=a.depth, lobby_h=a.lobby_height,
               floor_h=a.floor_height, cols_long=a.cols_long, cols_side=a.cols_side,
               band_every=4, lit_chance=0.22, ac_chance=0.2, seed=a.seed,
               detail=not a.no_detail)
    model, height = build(cfg)
    xml = to_rbxmx(model)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(xml)
    print("wrote %s  |  %d parts  |  %.0f studs tall  |  %.1f KB"
          % (a.out, len(PARTS), height, len(xml) / 1024))


if __name__ == "__main__":
    sys.exit(main())

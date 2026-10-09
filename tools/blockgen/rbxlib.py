"""
rbxlib.py — a tiny Roblox .rbxmx writer (Parts, Models, Folders, lights, GUIs,
MaterialVariants) with a tracked parts list for previews and sanity checks.
"""
import math
from xml.sax.saxutils import escape

# ─── ENUM VALUES (as stored in rbxmx) ───────────────────────────────────────
MAT = {
    "Plastic": 256, "SmoothPlastic": 272, "Neon": 288, "Wood": 512,
    "WoodPlanks": 528, "Marble": 784, "Basalt": 788, "Slate": 800,
    "Concrete": 816, "Limestone": 820, "Granite": 832, "Pavement": 836,
    "Brick": 848, "Pebble": 864, "Cobblestone": 880, "Rock": 896,
    "Sandstone": 912, "CorrodedMetal": 1040, "DiamondPlate": 1056,
    "Foil": 1072, "Metal": 1088, "Grass": 1280, "LeafyGrass": 1284,
    "Sand": 1296, "Fabric": 1312, "Mud": 1344, "Ground": 1360,
    "Asphalt": 1376, "Glass": 1568,
}
SHAPE_BALL, SHAPE_BLOCK, SHAPE_CYLINDER = 0, 1, 2
NORMAL_BACK = 2
FONT_GOTHAM_BOLD = 19


def f(v):
    s = "%.4f" % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def color3u8(c):
    return 0xFF000000 | (int(c[0]) << 16) | (int(c[1]) << 8) | int(c[2])


# ─── MATH ────────────────────────────────────────────────────────────────────
IDENT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def basis(dx, dz):
    """Rotation whose local +X points along (dx,dz) on the ground plane and
    whose local +Z is (-dz, dx), i.e. +X rotated 90 degrees. Y stays up."""
    return ((dx, 0, -dz), (0, 1, 0), (dz, 0, dx))


def Rz90():
    # local X axis -> world Y (cylinders stand upright)
    return ((0, -1, 0), (1, 0, 0), (0, 0, 1))


def matvec(R, v):
    return (R[0][0] * v[0] + R[0][1] * v[1] + R[0][2] * v[2],
            R[1][0] * v[0] + R[1][1] * v[1] + R[1][2] * v[2],
            R[2][0] * v[0] + R[2][1] * v[1] + R[2][2] * v[2])


def matmul(A, B):
    return tuple(tuple(sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3))
                 for i in range(3))


def tilt_x(rot, deg):
    """Rotate `rot` about its own local X axis by deg (used for slopes)."""
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    Rx = ((1, 0, 0), (0, c, -s), (0, s, c))
    return matmul(rot, Rx)


# ─── SCENE GRAPH ─────────────────────────────────────────────────────────────
class Scene:
    """Holds the referent counter and a flat list of parts for one output file."""

    def __init__(self):
        self.count = 0
        self.parts = []   # (name, size, pos, rot, color, transp, shape, material)

    def node(self, cls, name, props="", children=None):
        self.count += 1
        return Node(self, "RBX%d" % self.count, cls, name, props, children)

    # -- convenience builders ------------------------------------------------
    def folder(self, name):
        return self.node("Folder", name)

    def model(self, name):
        return self.node("Model", name)

    def part(self, name, size, pos, rot=IDENT, color=(128, 128, 128),
             material="SmoothPlastic", variant=None, transparency=0.0,
             collide=True, shape=SHAPE_BLOCK, query=True, children=None,
             reflectance=0.0, shadow=True):
        for s in size:
            if not s > 0:
                raise ValueError("bad size on %s: %r" % (name, size))
        size = tuple(max(s, 0.002) for s in size)      # never round to 0 in the file
        r = rot
        p = []
        p.append('<bool name="Anchored">true</bool>')
        if not collide:
            p.append('<bool name="CanCollide">false</bool>')
            p.append('<bool name="CanTouch">false</bool>')
        if not query:
            p.append('<bool name="CanQuery">false</bool>')
        if not shadow:
            p.append('<bool name="CastShadow">false</bool>')
        p.append('<CoordinateFrame name="CFrame"><X>%s</X><Y>%s</Y><Z>%s</Z>'
                 '<R00>%s</R00><R01>%s</R01><R02>%s</R02>'
                 '<R10>%s</R10><R11>%s</R11><R12>%s</R12>'
                 '<R20>%s</R20><R21>%s</R21><R22>%s</R22></CoordinateFrame>'
                 % (f(pos[0]), f(pos[1]), f(pos[2]),
                    f(r[0][0]), f(r[0][1]), f(r[0][2]),
                    f(r[1][0]), f(r[1][1]), f(r[1][2]),
                    f(r[2][0]), f(r[2][1]), f(r[2][2])))
        p.append('<Color3uint8 name="Color3uint8">%d</Color3uint8>' % color3u8(color))
        p.append('<token name="Material">%d</token>' % MAT[material])
        if variant:
            p.append('<string name="MaterialVariantSerialized">%s</string>' % escape(variant))
        if reflectance:
            p.append('<float name="Reflectance">%s</float>' % f(reflectance))
        if transparency:
            p.append('<float name="Transparency">%s</float>' % f(transparency))
        p.append('<Vector3 name="size"><X>%s</X><Y>%s</Y><Z>%s</Z></Vector3>'
                 % (f(size[0]), f(size[1]), f(size[2])))
        if shape != SHAPE_BLOCK:
            p.append('<token name="shape">%d</token>' % shape)
        for surf in ("Top", "Bottom", "Left", "Right", "Front", "Back"):
            p.append('<token name="%sSurface">0</token>' % surf)
        self.parts.append((name, size, pos, rot, color, transparency, shape, material))
        return self.node("Part", name, "\n".join(p), children)

    def point_light(self, color, brightness, rng, shadows=False):
        return self.node(
            "PointLight", "Light",
            '<float name="Brightness">%s</float>'
            '<Color3 name="Color"><R>%s</R><G>%s</G><B>%s</B></Color3>'
            '<float name="Range">%s</float><bool name="Shadows">%s</bool>'
            % (f(brightness), f(color[0] / 255), f(color[1] / 255), f(color[2] / 255),
               f(rng), "true" if shadows else "false"))

    def surface_text(self, text, canvas=(1200, 200), text_color=(220, 212, 198),
                     face=NORMAL_BACK):
        label = self.node(
            "TextLabel", "Text",
            '<float name="BackgroundTransparency">1</float>'
            '<UDim2 name="Size"><XS>1</XS><XO>0</XO><YS>1</YS><YO>0</YO></UDim2>'
            '<string name="Text">%s</string>'
            '<Color3 name="TextColor3"><R>%s</R><G>%s</G><B>%s</B></Color3>'
            '<bool name="TextScaled">true</bool><token name="Font">%d</token>'
            % (escape(text), f(text_color[0] / 255), f(text_color[1] / 255),
               f(text_color[2] / 255), FONT_GOTHAM_BOLD))
        return self.node(
            "SurfaceGui", "SignGui",
            '<token name="Face">%d</token>'
            '<Vector2 name="CanvasSize"><X>%d</X><Y>%d</Y></Vector2>'
            '<float name="LightInfluence">0</float>' % (face, canvas[0], canvas[1]),
            [label])

    def material_variant(self, name, base, studs_per_tile, color_map=None,
                         normal_map=None, roughness_map=None, metalness_map=None,
                         pattern=0):
        def content(prop, url):
            if url:
                return '<Content name="%s"><url>%s</url></Content>' % (prop, escape(url))
            return '<Content name="%s"><null></null></Content>' % prop
        props = (
            '<token name="BaseMaterial">%d</token>' % MAT[base]
            + content("ColorMap", color_map) + content("NormalMap", normal_map)
            + content("RoughnessMap", roughness_map)
            + content("MetalnessMap", metalness_map)
            + '<float name="StudsPerTile">%s</float>' % f(studs_per_tile)
            + '<token name="MaterialPattern">%d</token>' % pattern)
        return self.node("MaterialVariant", name, props)


class Node:
    def __init__(self, scene, ref, cls, name, props="", children=None):
        self.scene, self.ref, self.cls, self.name = scene, ref, cls, name
        self.props = props
        self.children = children if children is not None else []

    def add(self, child):
        self.children.append(child)
        return child

    def xml(self, out, depth=0):
        pad = "  " * depth
        out.append('%s<Item class="%s" referent="%s"><Properties>'
                   '<string name="Name">%s</string>%s</Properties>'
                   % (pad, self.cls, self.ref, escape(self.name), self.props))
        for c in self.children:
            c.xml(out, depth + 1)
        out.append("%s</Item>" % pad)


def to_rbxmx(roots):
    out = [
        '<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">',
        '  <Meta name="ExplicitAutoJoints">true</Meta>',
    ]
    for r in roots:
        r.xml(out, 1)
    out.append("</roblox>")
    return "\n".join(out) + "\n"

"""
style.py — palette, MaterialVariant names and shared constants.

Part.Color is the REAL colour (so the model looks right even before any
textures are uploaded).  The generated texture maps are near-neutral luminance
patterns that multiply with it, so a variant adds brick/concrete/asphalt detail
without changing the hue.
"""

# ─── real-world dimensions (metres) ─────────────────────────────────────────
SIDEWALK_W = 3.0           # sidewalk width
CURB_W = 0.30              # granite curb width
SIDEWALK_H = 0.15          # sidewalk height above the road (6 in)
PATH_W = 2.2               # interior footpaths
FLOOR_H = 3.1              # floor-to-floor
PARAPET_H = 0.75
WALL_T = 0.5               # hollow wall thickness

# ─── colours ────────────────────────────────────────────────────────────────
ASPHALT = (60, 62, 66)
ASPHALT_PATCH = (48, 50, 54)
SIDEWALK = (170, 167, 160)
CURB = (140, 138, 134)
LOT = (122, 118, 110)
LOT_DARK = (100, 98, 94)
GRASS = (88, 118, 64)
PAINT_WHITE = (232, 232, 226)
PAINT_YELLOW = (238, 196, 40)
STEEL = (74, 78, 84)
STEEL_DARK = (48, 50, 54)
GLASS = (52, 66, 82)
GLASS_LIT = (255, 214, 140)
CONC_TRIM = (200, 194, 180)
CONC_DARK = (128, 126, 120)
ROOF = (58, 58, 62)
ROOF_LIGHT = (150, 150, 146)
AC_GREY = (176, 178, 180)
BLIND = (214, 206, 188)

PROJECT_BRICKS = [(148, 74, 58), (142, 70, 54), (154, 80, 62)]
ROW_BRICKS = [(128, 76, 58), (150, 96, 72), (118, 66, 52), (170, 128, 92),
              (196, 172, 128), (136, 84, 62), (112, 70, 58)]
SIGN_COLORS = [(20, 20, 24), (30, 60, 110), (120, 26, 26), (30, 90, 56),
               (200, 160, 40), (70, 70, 76), (110, 40, 110)]
AWNING_COLORS = [(30, 70, 120), (120, 30, 30), (30, 100, 60), (180, 140, 40),
                 (60, 60, 66)]

# ─── MaterialVariants: name -> (BaseMaterial, tile size in metres) ──────────
VARIANTS = {
    "FB_BrickProject": ("Brick", 1.2),
    "FB_BrickRow": ("Brick", 1.2),
    "FB_SidewalkConcrete": ("Concrete", 1.5),
    "FB_ConcreteTrim": ("Concrete", 1.5),
    "FB_AsphaltRoad": ("Asphalt", 4.0),
    "FB_GraniteCurb": ("Granite", 1.5),
    "FB_RoofGravel": ("Concrete", 2.0),
    "FB_RollGate": ("Metal", 0.6),
}

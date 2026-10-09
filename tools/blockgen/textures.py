"""
textures.py — procedural, seamlessly tileable PBR maps for the MaterialVariants.

Every set is generated with numpy (no external assets):
    <name>_color.png      near-neutral luminance pattern (it MULTIPLIES Part.Color,
                          so the real brick/concrete colours stay in the parts)
    <name>_normal.png     tangent-space normal map (OpenGL convention, +Y up)
    <name>_rough.png      roughness (8-bit grey)
    <name>_metal.png      metalness (roll gate only)

All noise is generated in the frequency domain, so each map wraps perfectly.
"""
import math
import os

import numpy as np
from PIL import Image


# ─── helpers ────────────────────────────────────────────────────────────────
def tile_noise(n, cells, rng, aniso=(1.0, 1.0)):
    """Seamless band-limited noise in [-1, 1].  `cells` ~ features across the tile."""
    w = rng.standard_normal((n, n))
    F = np.fft.fft2(w)
    fy = np.fft.fftfreq(n)[:, None] * n
    fx = np.fft.fftfreq(n)[None, :] * n
    r2 = (fx / aniso[0]) ** 2 + (fy / aniso[1]) ** 2
    sigma = max(cells, 0.5)
    filt = np.exp(-r2 / (2 * sigma * sigma))
    out = np.real(np.fft.ifft2(F * filt))
    out -= out.mean()
    m = np.abs(out).max()
    return out / m if m > 0 else out


def fbm(n, rng, octaves=((4, 1.0), (12, 0.5), (36, 0.25)), aniso=(1.0, 1.0)):
    acc = np.zeros((n, n))
    tot = 0.0
    for cells, amp in octaves:
        acc += amp * tile_noise(n, cells, rng, aniso)
        tot += amp
    return acc / tot


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    # image y grows downward; OpenGL normal maps want +Y up, so flip dy
    nx, ny, nz = -dx * strength, dy * strength, np.ones_like(h)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / L, ny / L, nz / L], axis=-1)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def to_u8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def save(outdir, name, color=None, normal=None, rough=None, metal=None, flip_green=False):
    os.makedirs(outdir, exist_ok=True)
    files = {}
    if color is not None:
        im = to_u8(color) if color.dtype != np.uint8 else color
        p = os.path.join(outdir, name + "_color.png")
        Image.fromarray(im, "RGB").save(p, optimize=True)
        files["color"] = p
    if normal is not None:
        nm = normal.copy()
        if flip_green:
            nm[..., 1] = 255 - nm[..., 1]
        p = os.path.join(outdir, name + "_normal.png")
        Image.fromarray(nm, "RGB").save(p, optimize=True)
        files["normal"] = p
    if rough is not None:
        p = os.path.join(outdir, name + "_rough.png")
        Image.fromarray(to_u8(rough), "L").save(p, optimize=True)
        files["rough"] = p
    if metal is not None:
        p = os.path.join(outdir, name + "_metal.png")
        Image.fromarray(to_u8(metal), "L").save(p, optimize=True)
        files["metal"] = p
    return files


# ─── brick (running bond, 5 bricks x 16 courses over 1.2 m) ────────────────
def make_brick(n=1024, seed=1):
    rng = np.random.default_rng(seed)
    cols, rows = 5, 16
    y, x = np.mgrid[0:n, 0:n].astype(float) / n
    row = np.floor(y * rows).astype(int)
    bx = x * cols + 0.5 * (row % 2)
    col = np.floor(bx).astype(int) % cols
    u = bx - np.floor(bx)                 # 0..1 across a brick
    v = y * rows - np.floor(y * rows)     # 0..1 up a course
    mu, mv = 0.050, 0.150                 # mortar share (10 mm joints)
    # distance to nearest mortar edge, in brick units
    du = np.minimum(u, 1 - u) / mu
    dv = np.minimum(v, 1 - v) / mv
    edge = np.minimum(du, dv)
    brick = smoothstep(0.55, 1.35, edge)          # 0 in mortar, 1 on the brick face

    per_lum = rng.uniform(0.78, 0.93, (rows, cols))
    clinker = rng.random((rows, cols)) < 0.07
    per_lum[clinker] *= 0.78
    per_tint = rng.uniform(-0.03, 0.03, (rows, cols, 3))
    lum = per_lum[row % rows, col]
    tint = per_tint[row % rows, col]

    grain = fbm(n, rng, ((96, 1.0), (180, 0.6)))
    stain = fbm(n, rng, ((3, 1.0), (9, 0.5)), aniso=(1.0, 0.35))   # vertical streaks
    face = lum * (1 + 0.05 * grain) * (1 + 0.06 * stain)
    mortar = 0.985 + 0.02 * grain
    base = brick * face + (1 - brick) * mortar
    color = np.stack([base * (1 + tint[..., i]) for i in range(3)], axis=-1)

    height = brick * (0.88 + 0.12 * (grain * 0.5 + 0.5)) + (1 - brick) * 0.0
    height += 0.04 * fbm(n, rng, ((30, 1.0),))
    normal = normal_from_height(height * 18.0, 1.0)
    rough = np.clip(brick * (0.90 + 0.05 * grain) + (1 - brick) * 0.99, 0, 1)
    return color, normal, rough


# ─── sidewalk concrete (one 1.5 m slab per tile) ────────────────────────────
def make_sidewalk(n=512, seed=2):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n].astype(float) / n
    d = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y)) * 1.5    # metres to joint
    groove = 1 - smoothstep(0.004, 0.022, d)                             # tooled joint
    fine = fbm(n, rng, ((120, 1.0), (60, 0.7)))
    mid = fbm(n, rng, ((10, 1.0), (24, 0.5)))
    stain = fbm(n, rng, ((2.5, 1.0), (5, 0.4)))
    pores = (rng.random((n, n)) > 0.9965).astype(float)
    pores = np.maximum(pores, np.roll(pores, 1, axis=0))
    lum = 0.90 + 0.045 * fine + 0.05 * mid + 0.06 * stain - 0.22 * groove - 0.22 * pores
    color = np.stack([lum * 0.995, lum, lum * 1.005], axis=-1)
    height = -1.0 * groove + 0.12 * fine + 0.1 * mid - 0.3 * pores
    normal = normal_from_height(height * 10.0, 1.0)
    rough = np.clip(0.88 + 0.05 * fine + 0.06 * groove, 0, 1)
    return color, normal, rough


def make_trim(n=512, seed=3):
    rng = np.random.default_rng(seed)
    fine = fbm(n, rng, ((140, 1.0), (60, 0.6)))
    mid = fbm(n, rng, ((6, 1.0), (16, 0.5)))
    pores = (rng.random((n, n)) > 0.997).astype(float)
    lum = 0.93 + 0.035 * fine + 0.04 * mid - 0.2 * pores
    color = np.stack([lum] * 3, axis=-1)
    normal = normal_from_height((0.2 * fine + 0.1 * mid - 0.4 * pores) * 8, 1.0)
    rough = np.clip(0.78 + 0.06 * fine, 0, 1)
    return color, normal, rough


# ─── asphalt (4 m tile, aggregate + hairline cracks + a patch) ──────────────
def make_asphalt(n=512, seed=4):
    rng = np.random.default_rng(seed)
    fine = fbm(n, rng, ((200, 1.0), (90, 0.8)))
    mid = fbm(n, rng, ((10, 1.0), (28, 0.6)))
    stone = (rng.random((n, n)) > 0.985).astype(float)
    stone = np.maximum(stone, np.roll(stone, 1, axis=1))
    # cracks: a few meandering polylines drawn as thin dark lines (wrapping)
    crack = np.zeros((n, n))
    for _ in range(4):
        px, py = rng.uniform(0, n, 2)
        ang = rng.uniform(0, 2 * math.pi)
        for _s in range(int(rng.integers(120, 320))):
            ang += rng.normal(0, 0.10)
            px = (px + math.cos(ang) * 1.6) % n
            py = (py + math.sin(ang) * 1.6) % n
            ix, iy = int(px), int(py)
            crack[iy, ix] = 1.0
            crack[(iy + 1) % n, ix] = max(crack[(iy + 1) % n, ix], 0.5)
    # a rectangular repair patch
    patch = np.zeros((n, n))
    x0, y0 = int(rng.uniform(0.1, 0.5) * n), int(rng.uniform(0.1, 0.6) * n)
    patch[y0:y0 + int(0.22 * n), x0:x0 + int(0.3 * n)] = 1.0
    lum = (0.86 + 0.07 * fine + 0.06 * mid + 0.10 * stone - 0.16 * crack
           - 0.05 * patch * (0.5 + 0.5 * fine))
    color = np.stack([lum] * 3, axis=-1)
    height = 0.25 * fine + 0.12 * mid + 0.3 * stone - 0.4 * crack - 0.06 * patch
    normal = normal_from_height(height * 9, 1.0)
    rough = np.clip(0.86 + 0.06 * fine - 0.08 * stone, 0, 1)
    return color, normal, rough


def make_granite(n=512, seed=5):
    rng = np.random.default_rng(seed)
    speck = fbm(n, rng, ((200, 1.0), (120, 0.8)))
    big = (rng.random((n, n)) > 0.992).astype(float)
    dark = (rng.random((n, n)) > 0.994).astype(float)
    mid = fbm(n, rng, ((5, 1.0), (14, 0.5)))
    lum = 0.88 + 0.07 * speck + 0.04 * mid + 0.10 * big - 0.22 * dark
    color = np.stack([lum] * 3, axis=-1)
    normal = normal_from_height((0.08 * speck + 0.04 * mid) * 6, 1.0)
    rough = np.clip(0.55 + 0.1 * speck, 0, 1)
    return color, normal, rough


def make_gravel(n=512, seed=6):
    rng = np.random.default_rng(seed)
    blob = fbm(n, rng, ((70, 1.0), (140, 0.7)))
    stones = smoothstep(0.1, 0.5, blob)
    mid = fbm(n, rng, ((6, 1.0), (16, 0.5)))
    lum = 0.74 + 0.20 * stones + 0.06 * mid + 0.04 * fbm(n, rng, ((200, 1.0),))
    color = np.stack([lum] * 3, axis=-1)
    normal = normal_from_height((stones * 0.9 + 0.1 * blob) * 12, 1.0)
    rough = np.clip(0.93 + 0.05 * blob, 0, 1)
    return color, normal, rough


def make_gate(n=512, seed=7):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n].astype(float) / n
    slats = 10
    phase = (y * slats) % 1.0
    wave = 0.5 + 0.5 * np.sin(phase * 2 * math.pi)
    seam = smoothstep(0.0, 0.05, phase) * (1 - smoothstep(0.95, 1.0, phase))
    scuff = fbm(n, rng, ((80, 1.0), (30, 0.6)), aniso=(0.3, 1.0))
    lum = 0.80 + 0.14 * wave - 0.25 * (1 - seam) + 0.04 * scuff
    color = np.stack([lum] * 3, axis=-1)
    normal = normal_from_height((wave * 0.9 + 0.1 * scuff) * 10, 1.0)
    rough = np.clip(0.42 + 0.1 * (1 - wave) + 0.08 * scuff, 0, 1)
    metal = np.clip(0.88 - 0.1 * (1 - seam) + 0.05 * scuff, 0, 1)
    return color, normal, rough, metal


# name -> (generator kwargs, which maps)
SETS = {
    "brick": (make_brick, dict(n=1024, seed=1)),
    "sidewalk": (make_sidewalk, dict(n=512, seed=2)),
    "trim": (make_trim, dict(n=512, seed=3)),
    "asphalt": (make_asphalt, dict(n=512, seed=4)),
    "granite": (make_granite, dict(n=512, seed=5)),
    "gravel": (make_gravel, dict(n=512, seed=6)),
    "gate": (make_gate, dict(n=512, seed=7)),
}

# MaterialVariant name -> texture set
VARIANT_SET = {
    "FB_BrickProject": "brick",
    "FB_BrickRow": "brick",
    "FB_SidewalkConcrete": "sidewalk",
    "FB_ConcreteTrim": "trim",
    "FB_AsphaltRoad": "asphalt",
    "FB_GraniteCurb": "granite",
    "FB_RoofGravel": "gravel",
    "FB_RollGate": "gate",
}


def generate_all(outdir, flip_green=False):
    written = {}
    for name, (fn, kw) in SETS.items():
        res = fn(**kw)
        if name == "gate":
            c, nrm, r, m = res
            written[name] = save(outdir, name, c, nrm, r, m, flip_green)
        else:
            c, nrm, r = res
            written[name] = save(outdir, name, c, nrm, r, None, flip_green)
    return written

"""
preview.py — quick matplotlib renders of a Scene's parts (top view + elevations).
Only for sanity-checking the geometry; it is not part of the deliverable.
"""
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle


def _ext(size, rot):
    return [sum(abs(rot[i][j]) * size[j] / 2 for j in range(3)) for i in range(3)]


def _footprint(size, pos, rot, shape):
    if shape == 2 and abs(rot[1][0]) > 0.99:           # upright cylinder
        return ("circle", (pos[0], pos[2]), size[1] / 2)
    if shape == 0:
        return ("circle", (pos[0], pos[2]), size[0] / 2)
    pts = []
    for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        lx, lz = sx * size[0] / 2, sz * size[2] / 2
        # local Y contributes nothing to the plan outline of an upright box
        wx = rot[0][0] * lx + rot[0][2] * lz
        wz = rot[2][0] * lx + rot[2][2] * lz
        pts.append((pos[0] + wx, pos[2] + wz))
    return ("poly", pts, None)


def top_view(parts, path, xlim=None, zlim=None, figsize=(22, 16), dpi=70,
             skip=("Pivot",), title="", min_top=-1e9):
    items = []
    for (name, size, pos, rot, color, transp, shape, material) in parts:
        if name in skip or transp >= 0.99:
            continue
        top = pos[1] + _ext(size, rot)[1]
        items.append((top, name, size, pos, rot, color, transp, shape))
    items.sort(key=lambda t: t[0])
    fig, ax = plt.subplots(figsize=figsize)
    for top, name, size, pos, rot, color, transp, shape in items:
        kind, a, b = _footprint(size, pos, rot, shape)
        fc = tuple(c / 255 for c in color)
        if kind == "circle":
            ax.add_patch(Circle(a, b, fc=fc, ec="none", alpha=1 - transp * 0.6))
        else:
            ax.add_patch(Polygon(a, closed=True, fc=fc, ec=(0, 0, 0, 0.15),
                                 lw=0.2, alpha=1 - transp * 0.6))
    ax.set_aspect("equal")
    ax.autoscale_view()
    if xlim:
        ax.set_xlim(*xlim)
    if zlim:
        ax.set_ylim(*zlim[::-1])      # Z grows southward (down the page)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


def elevation(parts, path, axis="x", lo=None, hi=None, ylim=(-5, 80), figsize=(22, 8),
              dpi=70, skip=("Pivot",), title="", slab=None):
    """Orthographic elevation looking along Z (axis='x': x across) or X ('z')."""
    items = []
    for (name, size, pos, rot, color, transp, shape, material) in parts:
        if name in skip or transp >= 0.99:
            continue
        e = _ext(size, rot)
        depth = pos[2] if axis == "x" else pos[0]
        if slab and not (slab[0] <= depth <= slab[1]):
            continue
        items.append((-depth if axis == "x" else depth, name, size, pos, e, color, transp))
    items.sort(key=lambda t: t[0])
    fig, ax = plt.subplots(figsize=figsize)
    for key, name, size, pos, e, color, transp in items:
        c = pos[0] if axis == "x" else pos[2]
        w = e[0] if axis == "x" else e[2]
        ax.add_patch(plt.Rectangle((c - w, pos[1] - e[1]), 2 * w, 2 * e[1],
                                   fc=tuple(v / 255 for v in color), ec=(0, 0, 0, 0.12),
                                   lw=0.15, alpha=1 - transp * 0.6))
    ax.set_aspect("equal")
    ax.autoscale_view()
    if lo is not None and hi is not None:
        ax.set_xlim(lo, hi)
    ax.set_ylim(*ylim)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


# ─── shaded oblique / perspective-free 3D preview ────────────────────────────
def iso_view(parts, path, target, az=35.0, el=28.0, dist=400.0, half_w=120.0,
             half_h=75.0, figsize=(18, 11), dpi=80, min_alpha=0.1, clip=None,
             skip=("Pivot",), title="", bg=(0.78, 0.86, 0.95)):
    """Orthographic shaded render. az: degrees around Y (0 = looking north from
    the south), el: elevation. clip = (x0, z0, x1, z1) world rect of parts to draw."""
    import numpy as np
    from matplotlib.collections import PolyCollection
    a, e = math.radians(az), math.radians(el)
    eye = np.array(target) + dist * np.array([math.sin(a) * math.cos(e), math.sin(e),
                                              math.cos(a) * math.cos(e)])
    fwd = np.array(target) - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0, 1, 0.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    light = np.array([0.45, 0.82, 0.38])
    light /= np.linalg.norm(light)
    polys, cols, depths = [], [], []
    tgt = np.array(target)
    for (name, size, pos, rot, color, transp, shape, material) in parts:
        if name in skip or transp > 0.9:
            continue
        if clip and not (clip[0] <= pos[0] <= clip[2] and clip[1] <= pos[2] <= clip[3]):
            continue
        R = np.array(rot, dtype=float)
        c = np.array(pos, dtype=float)
        h = np.array(size, dtype=float) / 2
        base = np.array(color, dtype=float) / 255
        for axis in range(3):
            for s in (-1, 1):
                nrm = s * R[:, axis]
                if np.dot(nrm, fwd) >= -1e-6:
                    continue
                others = [i for i in range(3) if i != axis]
                corners = []
                for (u, v) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    loc = np.zeros(3)
                    loc[axis] = s * h[axis]
                    loc[others[0]] = u * h[others[0]]
                    loc[others[1]] = v * h[others[1]]
                    corners.append(c + R @ loc)
                corners = np.array(corners)
                pts2 = np.stack([(corners - tgt) @ right, (corners - tgt) @ up], axis=1)
                shade = 0.42 + 0.58 * max(0.0, float(np.dot(nrm, light)))
                polys.append(pts2)
                cols.append(tuple(np.clip(base * shade, 0, 1)) + (1 - 0.6 * transp,))
                depths.append(float(((corners - eye) @ fwd).max()))
    order = np.argsort(depths)[::-1]
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor(bg)
    pc = PolyCollection([polys[i] for i in order], facecolors=[cols[i] for i in order],
                        edgecolors="none", linewidths=0)
    ax.add_collection(pc)
    ax.set_xlim(-half_w, half_w)
    ax.set_ylim(-half_h, half_h)
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)

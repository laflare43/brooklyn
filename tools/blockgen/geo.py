"""
geo.py — 2D geometry on the Roblox ground plane (X east, Z south).
All polygons are lists of (x, z) tuples WITHOUT a repeated closing point.
"""
import math


def signed_area(pts):
    """Shoelace over (x, z). Negative = the winding the facade code expects for
    outer rings (then the outward normal of an edge d=(dx,dz) is (-dz, dx))."""
    s = 0.0
    n = len(pts)
    for i in range(n):
        x0, z0 = pts[i]
        x1, z1 = pts[(i + 1) % n]
        s += x0 * z1 - x1 * z0
    return s / 2.0


def orient(pts, want_negative=True):
    a = signed_area(pts)
    if (a < 0) != want_negative:
        return list(reversed(pts))
    return list(pts)


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def bbox(pts):
    xs = [p[0] for p in pts]
    zs = [p[1] for p in pts]
    return min(xs), min(zs), max(xs), max(zs)


def point_in_poly(pt, pts):
    x, z = pt
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, zi = pts[i]
        xj, zj = pts[j]
        if (zi > z) != (zj > z):
            xc = (xj - xi) * (z - zi) / (zj - zi) + xi
            if x < xc:
                inside = not inside
        j = i
    return inside


def dist_pt_seg(p, a, b):
    ax, az = a
    bx, bz = b
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    if L2 < 1e-12:
        return math.hypot(p[0] - ax, p[1] - az), 0.0
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - az) * dz) / L2))
    cx, cz = ax + t * dx, az + t * dz
    return math.hypot(p[0] - cx, p[1] - cz), t


def simplify_ring(pts, eps):
    """Drop vertices that sit within eps of the line through their neighbours
    (repeatedly), and exact duplicates. Keeps genuine corners."""
    pts = list(pts)
    # remove consecutive duplicates
    out = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    changed = True
    while changed and len(out) > 3:
        changed = False
        i = 0
        while i < len(out) and len(out) > 3:
            a = out[i - 1]
            b = out[i]
            c = out[(i + 1) % len(out)]
            d, _ = dist_pt_seg(b, a, c)
            if d < eps:
                out.pop(i)
                changed = True
            else:
                i += 1
    return out


def dominant_angle(pts):
    """Angle (radians) of the longest edge — the building's main axis."""
    best, ang = -1.0, 0.0
    n = len(pts)
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        if L > best:
            best = L
            ang = math.atan2(q[1] - p[1], q[0] - p[0])
    return ang


def rot2(x, z, ang):
    c, s = math.cos(ang), math.sin(ang)
    return (x * c - z * s, x * s + z * c)


def decompose(rings, ang, tol=0.25, merge_eps=0.08):
    """Even-odd scanline decomposition into rectangles aligned to `ang`.

    Returns rects (u0, u1, v0, v1) in the frame rotated by -ang (u along the
    direction (cos ang, sin ang), v along (-sin ang, cos ang)).  Exact for
    rectilinear polygons aligned to `ang`; slanted edges are approximated to
    within `tol` by subdividing the slab."""
    R = [[rot2(x, z, -ang) for (x, z) in ring] for ring in rings]
    edges = []
    for ring in R:
        n = len(ring)
        for i in range(n):
            (x0, z0), (x1, z1) = ring[i], ring[(i + 1) % n]
            if abs(z1 - z0) < 1e-9:
                continue
            if z0 > z1:
                x0, z0, x1, z1 = x1, z1, x0, z0
            edges.append((x0, z0, x1, z1, (x1 - x0) / (z1 - z0)))
    zs = sorted({round(e[1], 5) for e in edges} | {round(e[3], 5) for e in edges})
    slabs = []
    for a, b in zip(zs, zs[1:]):
        if b - a < 1e-5:
            continue
        mid = (a + b) / 2
        max_slope = 0.0
        for (x0, z0, x1, z1, k) in edges:
            if z0 <= mid < z1:
                max_slope = max(max_slope, abs(k))
        n_sub = max(1, int(math.ceil(max_slope * (b - a) / tol)))
        for i in range(n_sub):
            slabs.append((a + (b - a) * i / n_sub, a + (b - a) * (i + 1) / n_sub))
    rects = []
    open_ = []   # (x0, x1, z0, z1) still growing downwards
    for (a, b) in slabs:
        mid = (a + b) / 2
        xs = sorted(x0 + (mid - z0) * k for (x0, z0, x1, z1, k) in edges if z0 <= mid < z1)
        ivs = [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)
               if xs[i + 1] - xs[i] > 1e-4]
        new_open = []
        used = [False] * len(ivs)
        for (ox0, ox1, oz0, oz1) in open_:
            hit = None
            if abs(oz1 - a) < 1e-4:
                for j, (x0, x1) in enumerate(ivs):
                    if not used[j] and abs(x0 - ox0) < merge_eps and abs(x1 - ox1) < merge_eps:
                        hit = j
                        break
            if hit is None:
                rects.append((ox0, ox1, oz0, oz1))
            else:
                used[hit] = True
                new_open.append((ox0, ox1, oz0, b))
        for j, (x0, x1) in enumerate(ivs):
            if not used[j]:
                new_open.append((x0, x1, a, b))
        open_ = new_open
    rects.extend(open_)
    return rects


def rect_world(rect, ang):
    """Centre (x, z) and size (du, dv) of a decomposed rect back in world space."""
    u0, u1, v0, v1 = rect
    cx, cz = rot2((u0 + u1) / 2, (v0 + v1) / 2, ang)
    return (cx, cz), (u1 - u0, v1 - v0)


def clip_segment(p, q, box):
    """Liang–Barsky clip of segment p->q to box (x0, z0, x1, z1)."""
    x0, z0, x1, z1 = box
    dx, dz = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dz, p[1] - z0), (dz, z1 - p[1])):
        if abs(pp) < 1e-12:
            if qq < 0:
                return None
        else:
            t = qq / pp
            if pp < 0:
                if t > t1:
                    return None
                t0 = max(t0, t)
            else:
                if t < t0:
                    return None
                t1 = min(t1, t)
    return ((p[0] + t0 * dx, p[1] + t0 * dz), (p[0] + t1 * dx, p[1] + t1 * dz))


def clip_polyline(pts, box):
    """Split a polyline into the runs that lie inside `box`."""
    runs, cur = [], []
    for a, b in zip(pts, pts[1:]):
        seg = clip_segment(a, b, box)
        if seg is None:
            if len(cur) > 1:
                runs.append(cur)
            cur = []
            continue
        s0, s1 = seg
        if cur and math.hypot(cur[-1][0] - s0[0], cur[-1][1] - s0[1]) < 1e-6:
            cur.append(s1)
        else:
            if len(cur) > 1:
                runs.append(cur)
            cur = [s0, s1]
    if len(cur) > 1:
        runs.append(cur)
    return runs


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

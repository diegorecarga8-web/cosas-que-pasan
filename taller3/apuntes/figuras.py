"""Genera las figuras (SVG con trazo de lápiz) de los apuntes y las inserta en apuntes.html.

Los sólidos se modelan en 3D y se proyectan con una vista real (azimut 30°, elevación 20°):
caras ocultas por normal, aristas ocultas punteadas, sombreado por iluminación,
trazo doble "de boceto" con pequeños sobrepasos, y medidas en rojo con flechas.
Uso: python3 figuras.py   (reescribe los <svg class="sk"> de apuntes.html en orden)
"""
import math, random, re, pathlib

PEN = '#56575b'; DASH = '#77787c'; RED = '#b8343b'
COL = {k: '#7d7e82' for k in 'bogypkn'}  # solo grafito, como en el cuaderno
R = random.Random(42)
FIGN = [0]
CUR = [0]
SC = {1:1.2, 2:1.1, 3:1.1, 7:1.05, 8:1.15, 9:1.12, 10:1.22, 11:1.35, 12:1.2, 13:1.22, 14:1.2, 15:1.3, 16:1.4, 17:0.92, 18:1.05, 19:1.0, 20:1.1, 21:1.1, 22:1.3}

# ---------------------------------------------------------------- vector helpers
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def add(a, b): return tuple(x + y for x, y in zip(a, b))
def mul(a, k): return tuple(x * k for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def norm(a):
    l = math.sqrt(dot(a, a)); return tuple(x / l for x in a)

def set_view(az=30, el=20):
    global AZ, EL, V, U, W
    AZ, EL = math.radians(az), math.radians(el)
    V = (math.sin(AZ)*math.cos(EL), math.sin(EL), math.cos(AZ)*math.cos(EL))
    U = norm((V[2], 0, -V[0]))
    W = cross(V, U)
set_view()
LIGHT = norm((-0.45, 0.85, 0.55))

def P3(p):  # world -> raw screen (y down)
    return (dot(p, U), -dot(p, W))
def depth(p): return dot(p, V)

def f(v): return f"{v:.1f}"

class Fig:
    def __init__(self, w, h, pts2d, pad=10, padl=None, padr=None, padt=None, padb=None):
        FIGN[0] += 1; self.n = FIGN[0]; self.k = 0
        k_ = SC.get(CUR[0], 1.0); w, h = round(w*k_), round(h*k_)
        self.w, self.h = w, h; self.defs = []; self.fill = []; self.lines = []; self.top = []
        xs = [p[0] for p in pts2d]; ys = [p[1] for p in pts2d]
        pl = pad if padl is None else padl; pr = pad if padr is None else padr
        pt = pad if padt is None else padt; pb = pad if padb is None else padb
        bw, bh = max(xs) - min(xs), max(ys) - min(ys)
        self.s = min((w - pl - pr) / bw, (h - pt - pb) / bh)
        self.ox = pl + ((w - pl - pr) - bw * self.s) / 2 - min(xs) * self.s
        self.oy = pt + ((h - pt - pb) - bh * self.s) / 2 - min(ys) * self.s
        self.cen = self.T(((min(xs)+max(xs))/2, (min(ys)+max(ys))/2))
    def uid(self):
        self.k += 1; return f"c{self.n}_{self.k}"
    def T(self, p):  # raw 2d -> svg
        return (self.ox + p[0] * self.s, self.oy + p[1] * self.s)
    def S(self, p3):  # 3d -> svg
        return self.T(P3(p3))

    # ---------------- strokes
    def line(self, a, b, dashed=False, color=PEN, w=1.25, layer=None):
        layer = self.lines if layer is None else layer
        if dashed:
            layer.append(f'<path d="M{f(a[0])},{f(a[1])} L{f(b[0])},{f(b[1])}" fill="none" stroke="{DASH if color == PEN else color}" '
                         f'stroke-width="{w*0.85:.2f}" stroke-dasharray="3.4 2.6" stroke-linecap="round" opacity=".85"/>')
            return
        d = norm((b[0]-a[0], b[1]-a[1], 0)); L = math.dist(a, b)
        for k in range(2):
            e1, e2 = R.uniform(-0.5, 2.0), R.uniform(-0.5, 2.0)
            j = lambda: R.uniform(-0.55, 0.55)
            p = (a[0] - d[0]*e1 + j(), a[1] - d[1]*e1 + j()); q = (b[0] + d[0]*e2 + j(), b[1] + d[1]*e2 + j())
            # slight bow, like a hand-drawn line
            m = ((p[0]+q[0])/2 - d[1]*R.uniform(-0.6, 0.6)*min(1, L/40), (p[1]+q[1])/2 + d[0]*R.uniform(-0.6, 0.6)*min(1, L/40))
            op = '0.95' if k == 0 else '0.5'; ww = w if k == 0 else w*0.75
            layer.append(f'<path d="M{f(p[0])},{f(p[1])} Q{f(m[0])},{f(m[1])} {f(q[0])},{f(q[1])}" fill="none" stroke="{color}" '
                         f'stroke-width="{ww:.2f}" stroke-linecap="round" opacity="{op}"/>')
    def poly(self, pts, dashed=False, closed=False, color=PEN, w=1.25, layer=None):
        layer = self.lines if layer is None else layer
        d = 'M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in pts) + (' Z' if closed else '')
        if dashed:
            layer.append(f'<path d="{d}" fill="none" stroke="{DASH if color == PEN else color}" stroke-width="{w*0.85:.2f}" '
                         f'stroke-dasharray="3.4 2.6" stroke-linecap="round" stroke-linejoin="round" opacity=".85"/>')
            return
        for k in range(2):
            dx, dy = (0, 0) if k == 0 else (R.uniform(-0.7, 0.7), R.uniform(-0.7, 0.7))
            d2 = 'M' + ' L'.join(f'{f(x+dx+R.uniform(-.25,.25))},{f(y+dy+R.uniform(-.25,.25))}' for x, y in pts) + (' Z' if closed else '')
            layer.append(f'<path d="{d2}" fill="none" stroke="{color}" stroke-width="{w if k == 0 else w*0.75:.2f}" '
                         f'stroke-linecap="round" stroke-linejoin="round" opacity="{0.95 if k == 0 else 0.5}"/>')

    # ---------------- hatching (colored pencil)
    def hatch(self, pts, color, spacing=4.0, angle=45, op=0.6, sw=0.95, shade_clip=None, evenodd=False, path_d=None):
        op *= 0.55  # sombreado suave, el dibujo es sobre todo de línea
        cid = self.uid()
        d = path_d or ('M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in pts) + ' Z')
        rule = ' clip-rule="evenodd"' if evenodd else ''
        self.defs.append(f'<clipPath id="{cid}"><path d="{d}"{rule}/></clipPath>')
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
        rad = math.hypot(max(xs)-min(xs), max(ys)-min(ys))/2 + 4
        a = math.radians(angle); ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux
        out = []
        t = -rad
        while t < rad:
            tt = t + R.uniform(-0.6, 0.6)
            x0, y0 = cx + nx*tt - ux*rad, cy + ny*tt - uy*rad
            x1, y1 = cx + nx*tt + ux*rad, cy + ny*tt + uy*rad
            out.append(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" stroke-width="{sw*R.uniform(.8,1.15):.2f}" opacity="{op*R.uniform(.75,1.1):.2f}"/>')
            t += spacing * R.uniform(0.85, 1.15)
        g = f'<g clip-path="url(#{cid})" stroke="{color}" stroke-linecap="round">' + ''.join(out) + '</g>'
        if shade_clip:
            sid = self.uid(); sd, srule = shade_clip
            self.defs.append(f'<clipPath id="{sid}"><path d="{sd}"{" clip-rule=\"evenodd\"" if srule else ""}/></clipPath>')
            g = f'<g clip-path="url(#{sid})">{g}</g>'
        self.fill.append(g)

    # ---------------- annotations
    def text(self, p, s, red=False, size=11, anchor='middle'):
        cls = ' class="r"' if red else ''
        self.top.append(f'<text x="{f(p[0])}" y="{f(p[1])}" text-anchor="{anchor}" font-size="{size}"{cls}>{s}</text>')
    def dim(self, a, b, label, off=8, side=1, size=11, lpos=None):
        """dimension line parallel to a-b, offset 'off' px to one side, arrows both ends"""
        dx, dy = b[0]-a[0], b[1]-a[1]; L = math.hypot(dx, dy); ux, uy = dx/L, dy/L
        nx, ny = -uy, ux
        mx0, my0 = (a[0]+b[0])/2 - self.cen[0], (a[1]+b[1])/2 - self.cen[1]
        if nx*mx0 + ny*my0 < 0: nx, ny = -nx, -ny
        A = (a[0]+nx*off, a[1]+ny*off); B = (b[0]+nx*off, b[1]+ny*off)
        self.line(a, (a[0]+nx*(off+3), a[1]+ny*(off+3)), color=RED, w=0.7, layer=self.top)
        self.line(b, (b[0]+nx*(off+3), b[1]+ny*(off+3)), color=RED, w=0.7, layer=self.top)
        self.line(A, B, color=RED, w=0.9, layer=self.top)
        for P, s_ in ((A, 1), (B, -1)):
            for ang in (0.45, -0.45):
                c, sn = math.cos(ang), math.sin(ang)
                vx, vy = (ux*c - uy*sn)*s_, (ux*sn + uy*c)*s_
                self.top.append(f'<path d="M{f(P[0])},{f(P[1])} l{f(vx*5)},{f(vy*5)}" stroke="{RED}" stroke-width="1" stroke-linecap="round"/>')
        mx, my = (A[0]+B[0])/2, (A[1]+B[1])/2
        if lpos is None:
            lpos = (mx + nx*(6+size*0.35), my + ny*(6+size*0.35) + size*0.35)
        self.text(lpos, label, red=True, size=size)
    def redline(self, a, b, label=None, lp=None, size=11, dashed=True):
        self.line(a, b, dashed=dashed, color=RED, w=1.1, layer=self.top)
        if label: self.text(lp, label, red=True, size=size)

    def svg(self):
        return (f'<svg class="sk" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                f'<defs>{"".join(self.defs)}</defs><g style="filter:url(#rough)">{"".join(self.fill)}{"".join(self.lines)}</g>'
                f'{"".join(self.top)}</svg>')

# ---------------------------------------------------------------- polyhedra
def polyhedron(fig, verts, faces, color, extra_face_lines=None):
    c = mul(tuple(map(sum, zip(*verts))), 1/len(verts))
    info = []
    for fc in faces:
        p = [verts[i] for i in fc]
        n = norm(cross(sub(p[1], p[0]), sub(p[2], p[0])))
        fcen = mul(tuple(map(sum, zip(*p))), 1/len(p))
        if dot(n, sub(fcen, c)) < 0: n = mul(n, -1)
        info.append((fc, n, dot(n, V) > 1e-6))
    for fc, n, vis in info:
        if not vis: continue
        pts = [fig.S(verts[i]) for i in fc]
        lam = max(0, dot(n, LIGHT)); dark = 1 - lam
        fig.hatch(pts, COL[color], spacing=7.5 - 4.6*dark, angle=R.choice([40, 48, 55]), op=0.42 + 0.3*dark)
        if dark > 0.55:
            fig.hatch(pts, '#6b6d72', spacing=5.5, angle=-35, op=0.28*dark, sw=0.7)
    edges = {}
    for fc, n, vis in info:
        for i in range(len(fc)):
            e = tuple(sorted((fc[i], fc[(i+1) % len(fc)])))
            edges[e] = edges.get(e, False) or vis
    for e, vis in edges.items():
        if not vis: fig.line(fig.S(verts[e[0]]), fig.S(verts[e[1]]), dashed=True)
    if extra_face_lines: extra_face_lines()
    for e, vis in edges.items():
        if vis: fig.line(fig.S(verts[e[0]]), fig.S(verts[e[1]]))

def prism_data(base, h, shift=(0, 0)):
    n = len(base)
    verts = [(x, 0, z) for x, z in base] + [(x + shift[0], h, z + shift[1]) for x, z in base]
    faces = [list(range(n)), list(range(n, 2*n))] + [[i, (i+1) % n, n + (i+1) % n, n + i] for i in range(n)]
    return verts, faces

def regular(n, r, rot=0):
    return [(r*math.cos(rot + 2*math.pi*i/n), r*math.sin(rot + 2*math.pi*i/n)) for i in range(n)]

def fit_pts3(pts): return [P3(p) for p in pts]

# ---------------------------------------------------------------- round helpers
def circle3(cx, y, cz, r, n=96):
    return [(cx + r*math.cos(2*math.pi*i/n), y, cz + r*math.sin(2*math.pi*i/n)) for i in range(n)]

def split_front_back(fig, ring3, center3):
    """returns front and back arcs (svg pts) of a horizontal circle, by depth"""
    dc = depth(center3)
    front, back = [], []
    n = len(ring3)
    flags = [depth(p) >= dc for p in ring3]
    # rotate list so it starts at a transition
    start = next(i for i in range(n) if flags[i] != flags[i-1])
    seq = [ring3[(start + i) % n] for i in range(n + 1)]
    fl = [flags[(start + i) % n] for i in range(n + 1)]
    cur = [fig.S(seq[0])]; cf = fl[0]
    arcs = []
    for p, fg in zip(seq[1:], fl[1:]):
        cur.append(fig.S(p))
        if fg != cf:
            arcs.append((cf, cur)); cur = [fig.S(p)]; cf = fg
    arcs.append((cf, cur))
    for fg, a in arcs:
        (front if fg else back).append(a)
    return front, back

def silhouette_x(fig, ring3):
    pts = [fig.S(p) for p in ring3]
    i0 = min(range(len(pts)), key=lambda i: pts[i][0]); i1 = max(range(len(pts)), key=lambda i: pts[i][0])
    return i0, i1, pts

def arc_between(pts, i, j):  # indices along ring, going forward from i to j
    n = len(pts); out = []; k = i
    while True:
        out.append(pts[k])
        if k == j: break
        k = (k + 1) % n
    return out

def front_arc_idx(ring3, i0, i1, center3):
    """of the two arcs between i0 and i1, pick the one that is toward the viewer"""
    n = len(ring3)
    mid_a = ring3[(i0 + ((i1 - i0) % n)//2) % n]
    return (i0, i1) if depth(mid_a) >= depth(center3) else (i1, i0)

def cone_tangents(fig, ring3, apex3):
    A = fig.S(apex3); pts = [fig.S(p) for p in ring3]; n = len(pts)
    vals = []
    for i in range(n):
        p, q = pts[i], pts[(i+1) % n]
        vals.append((p[0]-A[0])*(q[1]-p[1]) - (p[1]-A[1])*(q[0]-p[0]))
    idx = [i for i in range(n) if (vals[i] > 0) != (vals[(i+1) % n] > 0)]
    return idx[0], idx[1], pts, A

def shade_right(fig, cx, frac=0.18, evenodd_circle=None):
    """clip region for the shadow side (right part)"""
    x = cx + frac
    return (f'M{f(x)},-500 L{fig.w+500},-500 L{fig.w+500},{fig.h+500} L{f(x)},{fig.h+500} Z', False)

def cylinder_body(fig, r, h, color, y0=0, rings=None, top=True, bottom_visible_arc=True):
    bot = circle3(0, y0, 0, r); topr = circle3(0, y0 + h, 0, r)
    i0, i1, bp = silhouette_x(fig, bot); _, _, tp = silhouette_x(fig, topr)
    fa, fb = front_arc_idx(bot, i0, i1, (0, y0, 0))
    front = arc_between(bp, fa, fb); back = arc_between(bp, fb, fa)
    sil = [tp[i0]] + front + [tp[i1]] + list(reversed(arc_between(tp, fa, fb)))
    body = [tp[i0]] + front + [tp[i1]] + arc_between(tp, fb, fa)[::-1][::-1]
    outline = front + arc_between(tp, i1, i0) if False else None
    # fill: whole silhouette (front arc + top back arc)
    topback = arc_between(tp, fb, fa)
    region = front + topback
    cx = (bp[i0][0] + bp[i1][0]) / 2
    fig.hatch(region, COL[color], spacing=6.2, angle=50, op=0.48)
    fig.hatch(region, COL[color], spacing=3.0, angle=50, op=0.55, shade_clip=shade_right(fig, cx, (bp[i1][0]-cx)*0.35))
    fig.hatch(region, '#6b6d72', spacing=4.5, angle=-40, op=0.22, sw=0.7, shade_clip=shade_right(fig, cx, (bp[i1][0]-cx)*0.6))
    if top:
        fig.hatch(tp, COL[color], spacing=8, angle=20, op=0.3)
    fig.poly(back, dashed=True) if bottom_visible_arc else None
    fig.poly(front)
    if rings:
        for yy in rings:
            rr = circle3(0, yy, 0, r); _, _, rp = silhouette_x(fig, rr)
            fig.poly(arc_between(rp, fa, fb), w=1.0)
    fig.line(bp[i0], tp[i0]); fig.line(bp[i1], tp[i1])
    if top: fig.poly(tp + [tp[0]])
    return bp, tp, i0, i1, fa, fb

def sphere_body(fig, r, color, y=0, upper_only=False):
    C = fig.S((0, y, 0)); rr = r * fig.s
    ring = circle3(0, y, 0, r)
    front, back = split_front_back(fig, ring, (0, y, 0))
    if upper_only:
        d = f'M{f(C[0]-rr)},{f(C[1])} A{f(rr)},{f(rr)} 0 0 1 {f(C[0]+rr)},{f(C[1])} Z'
        pts = [(C[0]-rr, C[1]-rr), (C[0]+rr, C[1])]
    else:
        d = f'M{f(C[0]-rr)},{f(C[1])} A{f(rr)},{f(rr)} 0 1 1 {f(C[0]+rr)},{f(C[1])} A{f(rr)},{f(rr)} 0 1 1 {f(C[0]-rr)},{f(C[1])} Z'
        pts = [(C[0]-rr, C[1]-rr), (C[0]+rr, C[1]+rr)]
    fig.hatch(pts, COL[color], spacing=6.0, angle=48, op=0.45, path_d=d)
    # crescent shadow: everything outside a circle shifted to the upper-left
    k = rr*0.28
    cres = (f'M-500,-500 L{fig.w+500},-500 L{fig.w+500},{fig.h+500} L-500,{fig.h+500} Z '
            f'M{f(C[0]-k-rr*0.95)},{f(C[1]-k)} A{f(rr*0.95)},{f(rr*0.95)} 0 1 0 {f(C[0]-k+rr*0.95)},{f(C[1]-k)} '
            f'A{f(rr*0.95)},{f(rr*0.95)} 0 1 0 {f(C[0]-k-rr*0.95)},{f(C[1]-k)} Z', True)
    fig.hatch(pts, COL[color], spacing=2.8, angle=48, op=0.55, path_d=d, shade_clip=cres)
    fig.hatch(pts, '#6b6d72', spacing=4.5, angle=-40, op=0.22, sw=0.7, path_d=d, shade_clip=cres)
    # highlight: leave it; outline
    if upper_only:
        arc = [(C[0] + rr*math.cos(math.pi + math.pi*i/48), C[1] + rr*math.sin(math.pi + math.pi*i/48)) for i in range(49)]
    else:
        arc = [(C[0] + rr*math.cos(2*math.pi*i/96), C[1] + rr*math.sin(2*math.pi*i/96)) for i in range(97)]
    fig.poly(arc, w=1.3)
    return C, rr, front, back

# ================================================================ FIGURES
figs = []

def fig_hex():
    base = regular(6, 1, math.pi/6)
    v, fc = prism_data(base, 2.5)
    F = Fig(80, 110, fit_pts3(v), pad=6)
    polyhedron(F, v, fc, 'b'); return F.svg()

def fig_sqpyr():
    v = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1), (0, 1.9, 0)]
    fc = [[0, 1, 2, 3], [0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]
    F = Fig(100, 92, fit_pts3(v), pad=6)
    polyhedron(F, v, fc, 'o')
    F.redline(F.S((0, 1.9, 0)), F.S((0, 0, 0)), 'h', (F.S((0, .9, 0))[0]+6, F.S((0, .9, 0))[1]))
    return F.svg()

def fig_cone(r=1, h=2.3, color='g', w=84, hh=100, labels=('h', 'r', 'g'), dims=None):
    ring = circle3(0, 0, 0, r)
    pts = fit_pts3(ring + [(0, h, 0)])
    F = Fig(w, hh, pts, pad=8, padr=14 if dims else 8, padb=12 if dims else 8)
    t0, t1, bp, A = cone_tangents(F, ring, (0, h, 0))
    fa, fb = front_arc_idx(ring, t0, t1, (0, 0, 0))
    front = arc_between(bp, fa, fb); back = arc_between(bp, fb, fa)
    region = [A] + front
    cx = A[0]
    F.hatch(region, COL[color], spacing=6, angle=60, op=0.5)
    F.hatch(region, COL[color], spacing=2.8, angle=60, op=0.55, shade_clip=shade_right(F, cx, (max(p[0] for p in bp)-cx)*0.3))
    F.hatch(region, '#6b6d72', spacing=4.5, angle=-35, op=0.22, sw=0.7, shade_clip=shade_right(F, cx, (max(p[0] for p in bp)-cx)*0.55))
    F.poly(back, dashed=True); F.poly(front)
    F.line(A, bp[fa]); F.line(A, bp[fb])
    O = F.S((0, 0, 0)); Rp = F.S((r*math.cos(-AZ*0) , 0, 0))
    rp = F.S((r, 0, 0))
    F.redline(A, O, None)
    F.line(O, rp, dashed=True, color=RED, w=1.0, layer=F.top)
    if labels:
        F.text(((A[0]+O[0])/2 - 6, (A[1]+O[1])/2), labels[0], red=True)
        F.text(((O[0]+rp[0])/2, (O[1]+rp[1])/2 - 3), labels[1], red=True)
        if labels[2]:
            gp = bp[fb] if bp[fb][0] > bp[fa][0] else bp[fa]
            F.text(((A[0]+gp[0])/2 + 7, (A[1]+gp[1])/2), labels[2], red=True)
    return F

def fig_cube():
    v, fc = prism_data([(-1, -1), (1, -1), (1, 1), (-1, 1)], 2)
    F = Fig(86, 86, fit_pts3(v), pad=7, padb=12)
    polyhedron(F, v, fc, 'y')
    F.dim(F.S((-1, 0, 1)), F.S((1, 0, 1)), 'a', off=5, side=-1)
    return F.svg()

def fig_cyl(r=1, h=2, color='y', w=76, hh=100, rl='r', hl=None, padr=8):
    ring = circle3(0, 0, 0, r) + circle3(0, h, 0, r)
    F = Fig(w, hh, fit_pts3(ring), pad=6, padr=padr)
    cylinder_body(F, r, h, color)
    T = F.S((0, h, 0)); E = F.S((r, h, 0))
    F.line(T, E, dashed=True, color=RED, w=1.0, layer=F.top)
    F.text(((T[0]+E[0])/2, (T[1]+E[1])/2 - 3), rl, red=True)
    if hl:
        bx = max(p[0] for p in [F.S(q) for q in ring])
        F.dim((bx, F.S((r, 0, 0))[1] if False else F.S((0, 0, 0))[1] + r*F.s*math.sin(EL)*0), (bx, T[1]), hl, off=6, side=-1)
    return F

def fig_gen():
    F = Fig(330, 110, [(0, 0), (330, 110)], pad=0)
    def axis(x, y0, y1):
        F.line((x, y0), (x, y1), dashed=True, color=RED, w=1.1, layer=F.top)
        F.top.append(f'<path d="M{f(x-9)},{f(y0+10)} a9,3.5 0 1 0 18,0" fill="none" stroke="{RED}" stroke-width="1.1"/>'
                     f'<path d="M{f(x+9)},{f(y0+10)} l-1,-4 m1,4 l-4,0" stroke="{RED}" stroke-width="1.1" fill="none"/>')
    # triangle -> cone
    x = 40; F.hatch([(x, 14), (x, 82), (x+32, 82)], COL['g'], spacing=3.5, op=.6)
    F.poly([(x, 14), (x, 82), (x+32, 82)], closed=True)
    F.poly([(x, 14), (x-32, 82)], dashed=True); F.poly([(x-32, 82)] + [(x + 32*math.cos(math.pi*i/24), 82 + 6*math.sin(math.pi*i/24)) for i in range(25)][::-1], dashed=True)
    axis(x, 4, 92); F.text((x, 106), 'triángulo → cono', size=10)
    # rectangle -> cylinder
    x = 160; F.hatch([(x, 16), (x+28, 16), (x+28, 80), (x, 80)], COL['y'], spacing=3.5, op=.6)
    F.poly([(x, 16), (x+28, 16), (x+28, 80), (x, 80)], closed=True)
    F.poly([(x-28, 16), (x-28, 80)], dashed=True)
    F.poly([(x + 28*math.cos(2*math.pi*i/48), 16 + 5*math.sin(2*math.pi*i/48)) for i in range(49)], dashed=True)
    F.poly([(x + 28*math.cos(math.pi*i/24), 80 + 5*math.sin(math.pi*i/24)) for i in range(25)], dashed=True)
    axis(x, 4, 92); F.text((x, 106), 'rectángulo → cilindro', size=10)
    # semicircle -> sphere
    x = 275; pts = [(x + 34*math.cos(-math.pi/2 + math.pi*i/40), 48 + 34*math.sin(-math.pi/2 + math.pi*i/40)) for i in range(41)]
    F.hatch(pts, COL['g'], spacing=3.5, op=.6); F.poly(pts + [pts[0]])
    F.poly([(x + 34*math.cos(math.pi/2 + math.pi*i/40), 48 + 34*math.sin(math.pi/2 + math.pi*i/40)) for i in range(41)], dashed=True)
    F.poly([(x + 34*math.cos(math.pi*i/24), 48 + 7*math.sin(math.pi*i/24)) for i in range(49)], dashed=True)
    axis(x, 4, 92); F.text((x, 106), 'semicírculo → esfera', size=10)
    s = F.svg().replace('viewBox="0 0 330 110">', 'viewBox="0 0 330 110" style="zoom:1">', 1)
    return s

def fig_sphere(color='g', label='r', w=84, hh=84):
    F = Fig(w, hh, [(-1, -1), (1, 1)], pad=5)
    C, rr, front, back = sphere_body(F, 1, color)
    # equator: in true view sphere center projects at (0,0)
    for a in back: F.poly(a, dashed=True)
    for a in front: F.poly(a, w=1.1)
    E = F.S((1, 0, 0)) if False else (C[0] + rr, C[1])
    F.top.append(f'<circle cx="{f(C[0])}" cy="{f(C[1])}" r="1.6" fill="#333"/>')
    F.line(C, (C[0]+rr, C[1]), dashed=True, color=RED, w=1.1, layer=F.top)
    F.text((C[0] + rr*0.5, C[1] - 4), label, red=True)
    return F.svg()

def fig_cubitos():
    L, D, H = 5, 3, 4
    v, fc = prism_data([(0, 0), (L, 0), (L, D), (0, D)], H)
    v = [(x, y, -z + D) for x, y, z in v]  # depth goes back
    F = Fig(150, 118, fit_pts3(v), pad=6, padb=16, padr=20)
    def grid():
        for i in range(1, L):  # front face z=D
            F.line(F.S((i, 0, D)), F.S((i, H, D)), w=0.75); F.line(F.S((i, H, D)), F.S((i, H, 0)), w=0.75)
        for j in range(1, H):
            F.line(F.S((0, j, D)), F.S((L, j, D)), w=0.75); F.line(F.S((L, j, D)), F.S((L, j, 0)), w=0.75)
        for k in range(1, D):
            F.line(F.S((L, 0, k)), F.S((L, H, k)), w=0.75); F.line(F.S((0, H, k)), F.S((L, H, k)), w=0.75)
    polyhedron(F, v, fc, 'k', extra_face_lines=grid)
    F.dim(F.S((0, 0, D)), F.S((L, 0, D)), '5 cm', off=5, side=-1, size=10)
    F.dim(F.S((L, 0, D)), F.S((L, 0, 0)), '3 cm', off=5, side=-1, size=10)
    F.dim(F.S((L, 0, 0)), F.S((L, H, 0)), '4', off=6, side=1, size=11)
    return F.svg()

def fig_discos():
    F_r, F_h = 3, 5
    ring = circle3(0, 0, 0, F_r) + circle3(0, F_h, 0, F_r)
    F = Fig(130, 130, fit_pts3(ring), pad=6, padr=18)
    bp, tp, i0, i1, fa, fb = cylinder_body(F, F_r, F_h, 'b', rings=[1, 2, 3, 4])
    T = F.S((0, F_h, 0)); E = F.S((F_r, F_h, 0))
    F.line(T, E, dashed=True, color=RED, w=1.0, layer=F.top); F.text(((T[0]+E[0])/2, (T[1]+E[1])/2 - 3), '3', red=True)
    F.dim(bp[i1], tp[i1], '5', off=7, side=-1)
    return F.svg()

def fig_rectpyr():
    a, b, h = 25, 10, 12
    v = [(-a/2, 0, -b/2), (a/2, 0, -b/2), (a/2, 0, b/2), (-a/2, 0, b/2), (0, h, 0)]
    fc = [[0, 1, 2, 3], [0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]
    F = Fig(140, 80, fit_pts3(v), pad=6, padb=14, padr=12)
    polyhedron(F, v, fc, 'o')
    F.redline(F.S((0, h, 0)), F.S((0, 0, 0)), '12', (F.S((0, h*0.45, 0))[0]+9, F.S((0, h*0.45, 0))[1]))
    F.dim(F.S((-a/2, 0, b/2)), F.S((a/2, 0, b/2)), '25', off=4, side=-1, size=10)
    F.dim(F.S((a/2, 0, b/2)), F.S((a/2, 0, -b/2)), '10', off=4, side=-1, size=10)
    return F.svg()

def fig_cone2():
    F = fig_cone(5, 18, 'b', 70, 100, labels=('18', '5', None))
    return F.svg()

def fig_cyl2():
    ring = circle3(0, 0, 0, 6) + circle3(0, 12, 0, 6)
    F = Fig(86, 100, fit_pts3(ring), pad=6, padr=14)
    bp, tp, i0, i1, fa, fb = cylinder_body(F, 6, 12, 'g')
    T = F.S((0, 12, 0)); E = F.S((6, 12, 0))
    F.line(T, E, dashed=True, color=RED, w=1.0, layer=F.top); F.text(((T[0]+E[0])/2, (T[1]+E[1])/2 - 3), '6', red=True)
    F.dim(bp[i1], tp[i1], '12', off=6, side=-1)
    return F.svg()

def fig_box():
    L, D, H = 6, 2, 1
    v, fc = prism_data([(0, 0), (L, 0), (L, D), (0, D)], H)
    v = [(x, y, -z + D) for x, y, z in v]
    F = Fig(150, 62, fit_pts3(v), pad=4, padb=14, padr=16)
    polyhedron(F, v, fc, 'b')
    F.dim(F.S((0, 0, D)), F.S((L, 0, D)), '6 cm', off=4, side=-1, size=10)
    F.dim(F.S((L, 0, D)), F.S((L, 0, 0)), '2', off=4, side=-1, size=10)
    F.dim(F.S((L, 0, 0)), F.S((L, H, 0)), '1', off=4, side=1, size=10)
    return F.svg()

def fig_penta():
    Rr = 4 / (2*math.sin(math.pi/5))
    base = regular(5, Rr, math.pi/2 + math.pi/5)
    set_view(28, 38)
    v, fc = prism_data(base, 10, shift=(3.0, 0.6))
    F = Fig(100, 130, fit_pts3(v), pad=6, padr=22, padb=12)
    polyhedron(F, v, fc, 'b')
    ys = [F.S(p)[1] for p in v]; xs = [F.S(p)[0] for p in v]
    X = max(xs) + 8
    F.dim((X, max(ys)), (X, min(ys)), '10', off=0, side=1)
    # height marker = vertical, red
    # side length on a front bottom edge
    e = max(((i, (i+1) % 5) for i in range(5)), key=lambda e: depth(mul(add(v[e[0]], v[e[1]]), .5)))
    F.dim(F.S(v[e[0]]), F.S(v[e[1]]), '4', off=4, side=-1 if F.S(v[e[0]])[0] < F.S(v[e[1]])[0] else 1, size=10)
    # apothem on the top face
    ctop = mul(tuple(map(sum, zip(*v[5:]))), 1/5)
    m = mul(add(v[5 + e[0]], v[5 + e[1]]), .5)
    F.redline(F.S(ctop), F.S(m), None)
    F.top.append(f'<circle cx="{f(F.S(ctop)[0])}" cy="{f(F.S(ctop)[1])}" r="1.5" fill="{RED}"/>')
    set_view()
    return F.svg()

def fig_hemicone():
    r, h = 3, 5
    ring = circle3(0, 0, 0, r)
    pts = fit_pts3(ring + [(0, -h, 0)]) + [P3((0, 0, 0))]
    pts += [(P3((0, 0, 0))[0], P3((0, 0, 0))[1] - r)]
    F = Fig(100, 128, pts, pad=6, padr=16)
    t0, t1, bp, A = cone_tangents(F, ring, (0, -h, 0))
    fa, fb = front_arc_idx(ring, t0, t1, (0, 0, 0))
    front = arc_between(bp, fa, fb); back = arc_between(bp, fb, fa)
    cone_reg = [A] + front
    cx = A[0]
    F.hatch(cone_reg, COL['p'], spacing=6, angle=60, op=0.5)
    F.hatch(cone_reg, COL['p'], spacing=2.8, angle=60, op=0.55, shade_clip=shade_right(F, cx, r*F.s*0.3))
    C, rr, _, _ = sphere_body(F, r, 'p', upper_only=True)
    F.poly(back, dashed=True); F.poly(front)
    F.line(A, bp[fa]); F.line(A, bp[fb])
    F.top.append(f'<circle cx="{f(C[0])}" cy="{f(C[1])}" r="1.6" fill="#333"/>')
    E = F.S((r, 0, 0))
    F.line(C, E, dashed=True, color=RED, w=1.0, layer=F.top); F.text(((C[0]+E[0])/2, C[1] - 4), 'r=3', red=True, size=10)
    F.redline(C, A, None); F.text((C[0] + 7, (C[1]+A[1])/2 + 6), '5', red=True)
    return F.svg()

def fig_cylcone():
    r, h, hc = 6, 8, 4
    ring = circle3(0, 0, 0, r) + circle3(0, h, 0, r)
    F = Fig(130, 132, fit_pts3(ring + [(0, -hc, 0)]), pad=6, padr=16, padt=12)
    bot = circle3(0, 0, 0, r)
    t0, t1, bp0, A = cone_tangents(F, bot, (0, -hc, 0))
    fa, fb = front_arc_idx(bot, t0, t1, (0, 0, 0))
    cone_reg = [A] + arc_between(bp0, fa, fb)
    F.hatch(cone_reg, COL['o'], spacing=5, angle=60, op=0.55)
    F.hatch(cone_reg, '#6b6d72', spacing=4.5, angle=-35, op=0.25, sw=0.7)
    bp, tp, i0, i1, _, _ = cylinder_body(F, r, h, 'o')
    F.line(A, bp0[fa]); F.line(A, bp0[fb])
    T1, T2 = tp[i0], tp[i1]
    F.dim(T1, T2, '12', off=6, side=1, size=10)
    F.dim(bp[i1], tp[i1], '8', off=6, side=-1)
    O = F.S((0, 0, 0)); F.redline(O, A, None); F.text((O[0] + 7, (O[1]+A[1])/2 + 4), '4', red=True)
    return F.svg()

# ---------------------------------------------------------------- nets
class Net:
    def __init__(self, w, h, polys, circles=(), pad=6, **kw):
        pts = [p for pl in polys for p in pl]
        for (cx, cy, r) in circles: pts += [(cx-r, cy-r), (cx+r, cy+r)]
        self.F = Fig(w, h, pts, pad=pad, **kw); self.polys = polys
    def draw(self, color, tabs=(), labels=()):
        F = self.F
        for (a, b) in tabs:  # tab on edge a->b, drawn outward (to the right of a->b)
            A, B = F.T(a), F.T(b); dx, dy = B[0]-A[0], B[1]-A[1]; L = math.hypot(dx, dy)
            nx, ny = dy/L, -dx/L; t = min(7, L*0.3)
            if nx*((A[0]+B[0])/2 - F.cen[0]) + ny*((A[1]+B[1])/2 - F.cen[1]) < 0: nx, ny = -nx, -ny
            q = [A, (A[0]+dx*0.18+nx*t, A[1]+dy*0.18+ny*t), (B[0]-dx*0.18+nx*t, B[1]-dy*0.18+ny*t), B]
            F.hatch(q, '#9a9ca1', spacing=3, angle=-30, op=.35, sw=.7)
            F.poly(q, w=0.9, color='#6f7176')
        edges = {}
        for pl in self.polys:
            sp = [F.T(p) for p in pl]
            F.hatch(sp, COL[color], spacing=5.2, angle=R.choice([40, 50, 58]), op=0.45)
            for i in range(len(pl)):
                a, b = pl[i], pl[(i+1) % len(pl)]
                key = tuple(sorted([(round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3))]))
                edges[key] = edges.get(key, 0) + 1
        for (a, b), c in edges.items():
            if c > 1: F.line(F.T(a), F.T(b), dashed=True)
        for (a, b), c in edges.items():
            if c == 1: F.line(F.T(a), F.T(b))
        for p, s, red, size in labels: F.text(F.T(p), s, red=red, size=size)
        return F

def net_box():
    # column x in [0,6]; y downward: front 1, top 2, back 1, bottom 2
    ys = [0, 1, 3, 4, 6]
    polys = [[(0, ys[i]), (6, ys[i]), (6, ys[i+1]), (0, ys[i+1])] for i in range(4)]
    polys += [[(-1, 1), (0, 1), (0, 3), (-1, 3)], [(6, 1), (7, 1), (7, 3), (6, 3)]]
    N = Net(160, 124, polys, pad=8)
    tabs = [((0, 0), (0, 1)), ((6, 1), (6, 0)), ((-1, 3), (-1, 1)), ((0, 6), (0, 4)), ((6, 4), (6, 6))]
    F = N.draw('b', tabs=[(b, a) for a, b in tabs], labels=[((3, .72), '6 × 1', False, 9), ((3, 2.2), '6 × 2', False, 10),
                                                    ((3, 3.72), '6 × 1', False, 9), ((3, 5.2), '6 × 2', False, 10),
                                                    ((-.5, 2.15), '1×2', False, 7), ((6.5, 2.15), '1×2', False, 7)])
    return F.svg()

def net_cyl():
    W_, H_ = 2*math.pi*6, 12
    rect = [(0, 0), (W_, 0), (W_, H_), (0, H_)]
    cx = W_*0.22
    N = Net(170, 100, [rect], circles=[(cx, -6, 6), (cx, H_ + 6, 6)], pad=6, padr=14)
    F = N.F
    for cy in (-6, H_ + 6):
        C = F.T((cx, cy)); rr = 6*F.s
        pts = [(C[0] + rr*math.cos(2*math.pi*i/60), C[1] + rr*math.sin(2*math.pi*i/60)) for i in range(61)]
        F.hatch(pts, COL['y'], spacing=5, angle=30, op=.45); F.poly(pts)
    N.draw('y', tabs=[((W_, 0), (W_, H_))])
    F.dim(F.T((0, H_)), F.T((W_, H_)), '2πr ≈ 37,7', off=4, side=-1, size=9, lpos=(F.T((W_*0.62, H_*0.55))))
    F.dim(F.T((W_, 0)), F.T((W_, H_)), '', off=12, side=1)
    F.text((F.T((W_, H_/2))[0] + 20, F.T((W_, H_/2))[1] + 4), '12', red=True)
    C = F.T((cx, -6)); F.line(C, (C[0] + 6*F.s, C[1]), dashed=True, color=RED, w=1, layer=F.top); F.text((C[0] + 3*F.s, C[1] - 3), '6', red=True, size=9)
    return F.svg()

def net_cone():
    g, r = math.sqrt(349), 5
    ang = 2*math.pi*r/g
    a0 = math.pi/2 - ang/2
    arc = [(g*math.cos(a0 + ang*i/40), g*math.sin(a0 + ang*i/40)) for i in range(41)]
    sector = [(0, 0)] + arc
    cy = g + r
    N = Net(160, 110, [sector], circles=[(0, cy, r)], pad=6)
    F = N.F
    S_ = [F.T(p) for p in sector]
    F.hatch(S_, COL['b'], spacing=5, angle=50, op=.45)
    F.line(S_[0], S_[1]); F.line(S_[0], S_[-1]); F.poly(S_[1:])
    C = F.T((0, cy)); rr = r*F.s
    pts = [(C[0] + rr*math.cos(2*math.pi*i/60), C[1] + rr*math.sin(2*math.pi*i/60)) for i in range(61)]
    F.hatch(pts, COL['b'], spacing=5, angle=20, op=.45); F.poly(pts)
    F.line(C, (C[0] + rr, C[1]), dashed=True, color=RED, w=1, layer=F.top); F.text((C[0] + rr/2, C[1] - 3), '5', red=True, size=9)
    # angle arc
    A = S_[0]; ra = 14
    F.top.append(f'<path d="M{f(A[0] + ra*math.cos(a0))},{f(A[1] + ra*math.sin(a0))} A{ra},{ra} 0 0 1 {f(A[0] + ra*math.cos(a0+ang))},{f(A[1] + ra*math.sin(a0+ang))}" fill="none" stroke="{RED}" stroke-width="1"/>')
    F.text((A[0], A[1] + ra + 11), '96,3°', red=True, size=9)
    m = F.T((g*0.55*math.cos(a0), g*0.55*math.sin(a0))); F.text((m[0] + 9, m[1] - 2), 'g', red=True)
    return F.svg()

def net_pyr():
    a, b = 25, 10; ap1, ap2 = 13, math.sqrt(12**2 + 12.5**2)
    base = [(-a/2, -b/2), (a/2, -b/2), (a/2, b/2), (-a/2, b/2)]
    polys = [base, [(-a/2, -b/2), (a/2, -b/2), (0, -b/2 - ap1)], [(a/2, b/2), (-a/2, b/2), (0, b/2 + ap1)],
             [(a/2, -b/2), (a/2, b/2), (a/2 + ap2, 0)], [(-a/2, b/2), (-a/2, -b/2), (-a/2 - ap2, 0)]]
    N = Net(150, 116, polys, pad=5)
    F = N.draw('o', tabs=[((0, -b/2 - ap1), (a/2, -b/2)), ((-a/2, b/2), (0, b/2 + ap1)), ((a/2 + ap2, 0), (a/2, b/2))],
               labels=[((0, 1.2), '25 × 10', False, 9), ((0, -b/2 - ap1*0.35), '13', True, 9), ((-a/2 - ap2*0.42, 1.2), '17,3', True, 8)])
    F.line(F.T((0, -b/2)), F.T((0, -b/2 - ap1)), dashed=True, color=RED, w=.9, layer=F.top)
    F.line(F.T((-a/2, 0)), F.T((-a/2 - ap2, 0)), dashed=True, color=RED, w=.9, layer=F.top)
    return F.svg()

def net_penta():
    Rr = 4 / (2*math.sin(math.pi/5)); ap = 2.75
    polys = [[(4*i, 0), (4*(i+1), 0), (4*(i+1), 10), (4*i, 10)] for i in range(5)]
    def pent(edge_a, edge_b, outward):
        mx, my = (edge_a[0]+edge_b[0])/2, (edge_a[1]+edge_b[1])/2
        cx, cy = mx, my + outward*ap
        ang0 = math.atan2(edge_a[1]-cy, edge_a[0]-cx)
        return [(cx + Rr*math.cos(ang0 + 2*math.pi*k/5*(-outward)), cy + Rr*math.sin(ang0 + 2*math.pi*k/5*(-outward))) for k in range(5)]
    top = pent((4, 0), (8, 0), -1); bot = pent((4, 10), (8, 10), 1)
    polys += [top, bot]
    N = Net(170, 104, polys, pad=5)
    F = N.draw('b', tabs=[((20, 0), (20, 10))] + [((0, 10), (0, 0))][:0],
               labels=[((2, 5.6), '4×10', False, 8)])
    return F.svg()

def fig_sph2():
    return fig_sphere('o', '22')

_order = [fig_hex, fig_sqpyr, lambda: fig_cone().svg(), fig_cube, lambda: fig_cyl().svg(), fig_gen, fig_sphere,
          fig_cubitos, fig_discos, fig_rectpyr, fig_cone2, fig_cyl2, fig_sph2, fig_box, fig_penta,
          fig_hemicone, fig_cylcone, net_box, net_cyl, net_cone, net_pyr, net_penta]
figs = []
for i_, fn in enumerate(_order):
    CUR[0] = i_ + 1; figs.append(fn())

if __name__ == '__main__':
    p = pathlib.Path(__file__).with_name('apuntes.html')
    s = p.read_text()
    blocks = list(re.finditer(r'<svg class="sk".*?</svg>', s, flags=re.S))
    assert len(blocks) == len(figs), (len(blocks), len(figs))
    out, last = [], 0
    for m, svg in zip(blocks, figs):
        out.append(s[last:m.start()]); out.append(svg); last = m.end()
    out.append(s[last:])
    p.write_text(''.join(out))
    print('ok', len(figs))

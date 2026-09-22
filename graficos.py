# -*- coding: utf-8 -*-
"""Gráficos SVG en línea (sin dependencias). Colores por variables CSS del informe."""
import math
from html import escape


def _g(x, dec=2):
    x = float(x)
    if abs(x - round(x)) < 1e-9:
        return f"{int(round(x)):,}".replace(",", " ")
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",").rstrip("0").rstrip(",")


def _ticks(lo, hi, n=5):
    if hi == lo:
        hi = lo + 1
    span = hi - lo
    paso = 10 ** math.floor(math.log10(span / n))
    for k in (1, 2, 2.5, 5, 10):
        if span / (paso * k) <= n:
            paso *= k
            break
    ini = math.floor(lo / paso) * paso
    t, v = [], ini
    while v <= hi + paso * 1e-9:
        if v >= lo - paso * 1e-9:
            t.append(v)
        v += paso
    return t


def linea(pts, x_base, z_base, banda, banda_txt, titulo, xlabel, ylabel, extra, uid):
    """pts: [(x, z|None)] ordenados. banda: (lo, hi) o None. extra: x de puntos de quiebre."""
    W, H, ml, mr, mt, mb = 640, 320, 66, 20, 18, 54
    xs = [float(p[0]) for p in pts]
    zs = [float(p[1]) for p in pts if p[1] is not None]
    xmin, xmax = min(xs), max(xs)
    zmin, zmax = min(zs), max(zs)
    pad = (zmax - zmin) * 0.12 or abs(zmax) * 0.05 or 1
    ymin, ymax = zmin - pad, zmax + pad
    X = lambda v: ml + (float(v) - xmin) / (xmax - xmin) * (W - ml - mr)
    Y = lambda v: mt + (1 - (float(v) - ymin) / (ymax - ymin)) * (H - mt - mb)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{escape(titulo)}" class="chart lin">']
    o.append(f'<defs><pattern id="h{uid}" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             f'<line x1="0" y1="0" x2="0" y2="7" class="hatch"/></pattern></defs>')
    for v in _ticks(ymin, ymax):
        o.append(f'<line x1="{ml}" x2="{W-mr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>'
                 f'<text x="{ml-8}" y="{Y(v)+4:.1f}" class="tick" text-anchor="end">{_g(v)}</text>')
    for v in _ticks(xmin, xmax, 6):
        o.append(f'<text x="{X(v):.1f}" y="{H-mb+18}" class="tick" text-anchor="middle">{_g(v)}</text>'
                 f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{H-mb}" y2="{H-mb+4}" class="axis"/>')
    o.append(f'<line x1="{ml}" x2="{W-mr}" y1="{H-mb}" y2="{H-mb}" class="axis"/>')
    # banda de validez
    if banda:
        lo = xmin if banda[0] is None else max(xmin, float(banda[0]))
        hi = xmax if banda[1] is None else min(xmax, float(banda[1]))
        if hi > lo:
            o.append(f'<rect x="{X(lo):.1f}" y="{mt}" width="{X(hi)-X(lo):.1f}" height="{H-mt-mb}" class="banda"/>')
            o.append(f'<text x="{X(lo)+6:.1f}" y="{mt+13}" class="nota">{escape(banda_txt)}</text>')
    # zonas infactibles
    i = 0
    while i < len(pts):
        if pts[i][1] is None:
            j = i
            while j + 1 < len(pts) and pts[j + 1][1] is None:
                j += 1
            a = xmin if i == 0 else float(pts[i][0])
            b = xmax if j == len(pts) - 1 else float(pts[j + 1][0])
            if i == 0:
                a = xmin
            o.append(f'<rect x="{X(a):.1f}" y="{mt}" width="{X(b)-X(a):.1f}" height="{H-mt-mb}" fill="url(#h{uid})" class="infz"/>')
            o.append(f'<text x="{(X(a)+X(b))/2:.1f}" y="{mt+(H-mt-mb)/2:.1f}" class="crit" text-anchor="middle">✕ Infactible</text>')
            i = j + 1
        else:
            i += 1
    # trazo
    seg = []
    for k, (x, z) in enumerate(pts):
        if z is None:
            if len(seg) > 1:
                o.append('<polyline points="' + " ".join(seg) + '" class="serie"/>')
            seg = []
        else:
            seg.append(f"{X(x):.1f},{Y(z):.1f}")
    if len(seg) > 1:
        o.append('<polyline points="' + " ".join(seg) + '" class="serie"/>')
    extra_f = {round(float(e), 6) for e in extra}
    for x, z in pts:
        if z is not None and round(float(x), 6) in extra_f:
            o.append(f'<circle cx="{X(x):.1f}" cy="{Y(z):.1f}" r="4" class="quiebre"/>')
    # base
    o.append(f'<circle cx="{X(x_base):.1f}" cy="{Y(z_base):.1f}" r="6.5" class="base"/>'
             f'<text x="{X(x_base):.1f}" y="{Y(z_base)-12:.1f}" class="etq" text-anchor="middle">Base</text>')
    for x, z in pts:
        if z is not None:
            tip = f"{xlabel}: {_g(x)} · {ylabel}: {_g(z)}"
            o.append(f'<circle cx="{X(x):.1f}" cy="{Y(z):.1f}" r="9" class="hit" data-tip="{escape(tip)}"/>')
    o.append(f'<text x="{(ml+W-mr)/2:.1f}" y="{H-8}" class="eje" text-anchor="middle">{escape(xlabel)}</text>')
    o.append(f'<text transform="translate(16 {(mt+H-mb)/2:.1f}) rotate(-90)" class="eje" text-anchor="middle">{escape(ylabel)}</text>')
    o.append('</svg>')
    return "".join(o)


def barras_delta(filas, unidad, sentido_bueno):
    """filas: [(id, nombre, delta|None, pct|None)]; sentido_bueno: 'baja' (min) o 'sube' (max)."""
    rh, ml, mr, mt = 30, 250, 96, 10
    W = 760
    H = mt + rh * len(filas) + 34
    mx = max([abs(float(f[2])) for f in filas if f[2] is not None] + [1])
    cx = ml + (W - ml - mr) / 2
    esc = (W - ml - mr) / 2 / mx
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Variación del objetivo por escenario" class="chart">']
    o.append(f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{mt}" y2="{H-30}" class="axis"/>')
    for k, (eid, nombre, d, pct) in enumerate(filas):
        y = mt + k * rh
        o.append(f'<text x="{ml-10}" y="{y+rh/2+4:.1f}" class="etq" text-anchor="end"><tspan class="idt">{escape(eid)}</tspan>  {escape(nombre[:34])}</text>')
        if d is None:
            o.append(f'<text x="{cx+8:.1f}" y="{y+rh/2+4:.1f}" class="crit">✕ Infactible</text>')
            continue
        d = float(d)
        bueno = (d < 0) if sentido_bueno == "baja" else (d > 0)
        w = abs(d) * esc
        x0 = cx if d >= 0 else cx - w
        cls = "fav" if bueno else "adv"
        if d == 0:
            o.append(f'<text x="{cx+8:.1f}" y="{y+rh/2+4:.1f}" class="etq">sin cambio</text>')
            continue
        tip = f"{eid} · {nombre}: {'+' if d>0 else ''}{_g(d)} {unidad} ({'+' if d>0 else ''}{_g(pct,1)} %)"
        o.append(f'<rect x="{x0:.1f}" y="{y+6}" width="{max(w,2):.1f}" height="{rh-12}" rx="3" class="{cls} hit-bar" data-tip="{escape(tip)}"/>')
        tx = cx + w + 6 if d > 0 else cx + 8
        anc = "start"
        o.append(f'<text x="{tx:.1f}" y="{y+rh/2+4:.1f}" class="val" text-anchor="{anc}">{"+" if d>0 else ""}{_g(d)} ({"+" if d>0 else ""}{_g(pct,1)} %)</text>')
    ly = H - 12
    o.append(f'<rect x="{ml}" y="{ly-9}" width="10" height="10" rx="2" class="fav"/><text x="{ml+15}" y="{ly}" class="nota">Favorable</text>'
             f'<rect x="{ml+90}" y="{ly-9}" width="10" height="10" rx="2" class="adv"/><text x="{ml+105}" y="{ly}" class="nota">Desfavorable</text>'
             f'<text x="{W-mr}" y="{ly}" class="nota" text-anchor="end">Δ del objetivo vs. base ({escape(unidad)})</text>')
    o.append('</svg>')
    return "".join(o)


def mapa_riesgo(riesgos):
    """riesgos: [(id, prob 1-5, impacto 1-5)] → matriz 5×5."""
    cw, ch, ml, mt = 96, 62, 92, 12
    W, H = ml + cw * 5 + 12, mt + ch * 5 + 44
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Matriz de riesgos probabilidad por impacto" class="chart mapa">']
    def nivel(e):
        return 3 if e >= 15 else 2 if e >= 10 else 1 if e >= 5 else 0
    for p in range(5, 0, -1):
        for i in range(1, 6):
            x, y = ml + (i - 1) * cw, mt + (5 - p) * ch
            e = p * i
            o.append(f'<rect x="{x+1}" y="{y+1}" width="{cw-2}" height="{ch-2}" rx="4" class="n{nivel(e)}"/>')
            o.append(f'<text x="{x+cw-8}" y="{y+ch-8}" class="celda" text-anchor="end">{e}</text>')
    celdas = {}
    for rid, p, i in riesgos:
        celdas.setdefault((p, i), []).append(rid)
    for (p, i), ids in celdas.items():
        x, y = ml + (i - 1) * cw, mt + (5 - p) * ch
        for k, rid in enumerate(ids):
            px = x + 10 + (k % 2) * 40
            py = y + 10 + (k // 2) * 22
            o.append(f'<rect x="{px}" y="{py}" width="36" height="19" rx="9.5" class="pill"/>'
                     f'<text x="{px+18}" y="{py+13.5}" class="pilltxt" text-anchor="middle">{escape(rid)}</text>')
    for p in range(1, 6):
        o.append(f'<text x="{ml-10}" y="{mt+(5-p)*ch+ch/2+4}" class="tick" text-anchor="end">{p}</text>')
    for i in range(1, 6):
        o.append(f'<text x="{ml+(i-1)*cw+cw/2}" y="{mt+5*ch+18}" class="tick" text-anchor="middle">{i}</text>')
    o.append(f'<text x="{ml+cw*2.5}" y="{H-6}" class="eje" text-anchor="middle">Impacto →</text>')
    o.append(f'<text transform="translate(14 {mt+ch*2.5}) rotate(-90)" class="eje" text-anchor="middle">Probabilidad →</text>')
    o.append('</svg>')
    return "".join(o)


def barra_rango(lo, hi, act, w=170, h=16):
    """Mini gráfico de rango: segmento [lo, hi] y marca del valor actual. None = sin límite (flecha)."""
    a, lo_f, hi_f = float(act), None if lo is None else float(lo), None if hi is None else float(hi)
    ancho = max((hi_f if hi_f is not None else a) - (lo_f if lo_f is not None else a), abs(a) * 0.2, 1)
    emin = (lo_f if lo_f is not None else a - ancho * 0.6) - ancho * 0.08
    emax = (hi_f if hi_f is not None else a + ancho * 0.6) + ancho * 0.08
    X = lambda v: 4 + (v - emin) / (emax - emin) * (w - 8)
    x1 = X(lo_f) if lo_f is not None else 4
    x2 = X(hi_f) if hi_f is not None else w - 4
    o = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" class="rango" aria-hidden="true">',
         f'<line x1="4" x2="{w-4}" y1="{h/2}" y2="{h/2}" class="axis"/>',
         f'<line x1="{x1:.1f}" x2="{x2:.1f}" y1="{h/2}" y2="{h/2}" class="seg"/>']
    if lo_f is None:
        o.append(f'<path d="M{x1+5:.1f} {h/2-4} L{x1:.1f} {h/2} L{x1+5:.1f} {h/2+4}" class="flecha"/>')
    else:
        o.append(f'<line x1="{x1:.1f}" x2="{x1:.1f}" y1="{h/2-5}" y2="{h/2+5}" class="tope"/>')
    if hi_f is None:
        o.append(f'<path d="M{x2-5:.1f} {h/2-4} L{x2:.1f} {h/2} L{x2-5:.1f} {h/2+4}" class="flecha"/>')
    else:
        o.append(f'<line x1="{x2:.1f}" x2="{x2:.1f}" y1="{h/2-5}" y2="{h/2+5}" class="tope"/>')
    o.append(f'<circle cx="{X(a):.1f}" cy="{h/2}" r="4.5" class="base"/></svg>')
    return "".join(o)

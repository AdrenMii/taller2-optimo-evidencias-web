# -*- coding: utf-8 -*-
"""Motor de Programación Lineal: Simplex de Dos Fases con aritmética exacta (Fraction),
registro de cada tabla, precios sombra, costos reducidos y rangos de optimalidad."""
from fractions import Fraction as F
from copy import deepcopy

MAX_ITER = 200


class Restriccion:
    def __init__(self, clave, nombre, a, tipo, b, unidad="", auxiliar=False):
        self.clave, self.nombre, self.tipo, self.unidad = clave, nombre, tipo, unidad
        self.a = [F(v) for v in a]
        self.b = F(b)
        self.auxiliar = auxiliar   # True: restricción técnica (p. ej. cota 0/1), sin lectura de negocio directa


class Modelo:
    def __init__(self, clave, nombre, sentido, vars_, c, restricciones, unidad_z="", vars_desc=None):
        self.clave, self.nombre, self.sentido = clave, nombre, sentido
        self.vars = list(vars_)
        self.vars_desc = vars_desc or list(vars_)
        self.c = [F(v) for v in c]
        self.restr = restricciones
        self.unidad_z = unidad_z

    def copia(self):
        return deepcopy(self)

    def variar(self, b=None, c=None, agregar=None, a=None):
        """b: {clave: nuevo_rhs}; c: {var: nuevo_costo}; a: {(clave, var): nuevo_coef}; agregar: [Restriccion]."""
        m = self.copia()
        for r in m.restr:
            if b and r.clave in b:
                r.b = F(b[r.clave])
        for v, val in (c or {}).items():
            m.c[m.vars.index(v)] = F(val)
        for (k, v), val in (a or {}).items():
            r = next(r for r in m.restr if r.clave == k)
            r.a[m.vars.index(v)] = F(val)
        m.restr += list(agregar or [])
        return m


def fnum(x, dec=2):
    """Texto decimal sin ceros sobrantes."""
    x = F(x)
    if x.denominator == 1:
        return f"{int(x):,}".replace(",", " ") if abs(x) >= 10000 else str(int(x))
    s = f"{float(x):.{dec}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def ffrac(x):
    x = F(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def _inversa(M):
    n = len(M)
    A = [list(f) + [F(int(i == j)) for j in range(n)] for i, f in enumerate(M)]
    for i in range(n):
        p = next(k for k in range(i, n) if A[k][i] != 0)
        A[i], A[p] = A[p], A[i]
        pv = A[i][i]
        A[i] = [v / pv for v in A[i]]
        for k in range(n):
            if k != i and A[k][i] != 0:
                fac = A[k][i]
                A[k] = [x - fac * y for x, y in zip(A[k], A[i])]
    return [f[n:] for f in A]


def _forma_estandar(m):
    """Devuelve columnas, nombres, tipos de columna y base inicial."""
    n, mm = len(m.vars), len(m.restr)
    nombres = list(m.vars)
    tipo_col = ["orig"] * n
    cols = [[m.restr[i].a[j] for i in range(mm)] for j in range(n)]
    base = [None] * mm
    for i, r in enumerate(m.restr):
        def nueva(nombre, tipo, coef):
            col = [F(0)] * mm
            col[i] = F(coef)
            cols.append(col)
            nombres.append(nombre)
            tipo_col.append(tipo)
            return len(cols) - 1
        if r.tipo == "<=":
            base[i] = nueva(f"s{i+1}", "holgura", 1)
        elif r.tipo == ">=":
            nueva(f"e{i+1}", "exceso", -1)
            base[i] = nueva(f"a{i+1}", "artificial", 1)
        else:
            base[i] = nueva(f"a{i+1}", "artificial", 1)
    return cols, nombres, tipo_col, base


class Resultado:
    pass


def resolver(m):
    for r in m.restr:
        assert r.b >= 0, "El lado derecho debe ser >= 0"
    res = Resultado()
    res.modelo = m
    res.tablas = []
    cols, nombres, tipo_col, base = _forma_estandar(m)
    mm, nt = len(m.restr), len(cols)
    T = [[cols[j][i] for j in range(nt)] + [m.restr[i].b] for i in range(mm)]
    signo = 1 if m.sentido == "max" else -1
    activas = list(range(nt))            # columnas vigentes (fase 2 quita las artificiales)
    hay_art = any(t == "artificial" for t in tipo_col)

    def fila0(cvec, act):
        row = []
        for j in act:
            row.append(sum(cvec[base[i]] * T[i][j] for i in range(mm)) - cvec[j])
        row.append(sum(cvec[base[i]] * T[i][-1] for i in range(mm)))
        return row

    def vista(fase, it, cvec, act, decision=None):
        z0 = fila0(cvec, act)
        d = dict(fase=fase, iter=it, cols=[nombres[j] for j in act],
                 base=[nombres[b] for b in base],
                 filas=[[T[i][j] for j in act] + [T[i][-1]] for i in range(mm)],
                 z=z0, entra=None, sale=None, razones=None, pivote=None, optima=False)
        if decision:
            d.update(decision)
        res.tablas.append(d)
        return d

    def iterar(fase, cvec, act):
        it = 0
        while True:
            z0 = fila0(cvec, act)
            neg = [(z0[k], act[k]) for k in range(len(act)) if z0[k] < 0]
            if not neg:
                vista(fase, it, cvec, act).update(optima=True)
                return "optimo"
            # criterio de Dantzig; empates: menor índice
            col = min(neg, key=lambda t: (t[0], t[1]))[1]
            razones = [(T[i][-1] / T[i][col]) if T[i][col] > 0 else None for i in range(mm)]
            val = [r for r in razones if r is not None]
            if not val:
                vista(fase, it, cvec, act)
                return "no_acotado"
            rmin = min(val)
            fila = min(i for i in range(mm) if razones[i] is not None and razones[i] == rmin)
            vista(fase, it, cvec, act, dict(entra=nombres[col], sale=nombres[base[fila]],
                                            razones=razones, pivote=(fila, act.index(col)), col_entra=col))
            pv = T[fila][col]
            T[fila] = [v / pv for v in T[fila]]
            for i in range(mm):
                if i != fila and T[i][col] != 0:
                    f = T[i][col]
                    T[i] = [x - f * y for x, y in zip(T[i], T[fila])]
            base[fila] = col
            it += 1
            if it > MAX_ITER:
                return "ciclo"

    if hay_art:
        c1 = [F(-1) if t == "artificial" else F(0) for t in tipo_col]
        est = iterar(1, c1, activas)
        w = sum(T[i][-1] for i in range(mm) if tipo_col[base[i]] == "artificial")
        res.w_fase1 = w
        if w != 0:
            res.estado = "infactible"
            return res
        # expulsar artificiales degeneradas de la base
        for i in range(mm):
            if tipo_col[base[i]] == "artificial":
                j = next((j for j in range(nt) if tipo_col[j] != "artificial" and T[i][j] != 0), None)
                if j is not None:
                    pv = T[i][j]
                    T[i] = [v / pv for v in T[i]]
                    for k in range(mm):
                        if k != i and T[k][j] != 0:
                            f = T[k][j]
                            T[k] = [x - f * y for x, y in zip(T[k], T[i])]
                    base[i] = j
        activas = [j for j in range(nt) if tipo_col[j] != "artificial"]
    else:
        res.w_fase1 = None

    cm = [signo * v for v in m.c] + [F(0)] * (nt - len(m.vars))   # forma de maximización
    est = iterar(2, cm, activas)
    if est != "optimo":
        res.estado = est
        return res

    res.estado = "optimo"
    res.nombres, res.tipo_col = nombres, tipo_col
    # ---- solución
    x = [F(0)] * len(m.vars)
    for i in range(mm):
        if base[i] < len(m.vars):
            x[base[i]] = T[i][-1]
    res.x = x
    res.z = sum(c * v for c, v in zip(m.c, x))
    res.uso = [sum(r.a[j] * x[j] for j in range(len(x))) for r in m.restr]
    res.holgura = [(r.b - u) if r.tipo == "<=" else (u - r.b) if r.tipo == ">=" else F(0)
                   for r, u in zip(m.restr, res.uso)]

    # ---- dualidad y sensibilidad (a partir de la base final)
    B = [[cols[base[k]][i] for k in range(mm)] for i in range(mm)]
    Binv = _inversa(B)
    c_orig = list(m.c) + [F(0)] * (nt - len(m.vars))
    cB = [c_orig[base[k]] for k in range(mm)]
    y = [sum(cB[k] * Binv[k][i] for k in range(mm)) for i in range(mm)]
    res.precios_sombra = y
    xB = [T[k][-1] for k in range(mm)]
    res.degenerado = any(v == 0 for v in xB)

    noB = [j for j in range(nt) if tipo_col[j] != "artificial" and j not in base]
    res.costos_reducidos = []
    for j in range(len(m.vars)):
        res.costos_reducidos.append(c_orig[j] - sum(y[i] * cols[j][i] for i in range(mm)))

    # rango de costos (variables originales), en unidades del costo original
    alpha = {}
    for k in range(mm):
        alpha[k] = {j: sum(Binv[k][i] * cols[j][i] for i in range(mm)) for j in range(nt)}
    dm = {j: cm[j] - sum(cm[base[k]] * alpha[k][j] for k in range(mm)) for j in noB}
    rangos_c = []
    for j in range(len(m.vars)):
        if j in base:
            k = base.index(j)
            lo, hi = None, None
            for jn in noB:
                a = alpha[k][jn]
                if a > 0:
                    v = dm[jn] / a
                    lo = v if lo is None else max(lo, v)
                elif a < 0:
                    v = dm[jn] / a
                    hi = v if hi is None else min(hi, v)
            if m.sentido == "max":
                l = None if lo is None else m.c[j] + lo
                h = None if hi is None else m.c[j] + hi
            else:
                l = None if hi is None else m.c[j] - hi
                h = None if lo is None else m.c[j] - lo
            rangos_c.append(dict(basica=True, lo=l, hi=h))
        else:
            d = dm[j]
            if m.sentido == "max":
                rangos_c.append(dict(basica=False, lo=None, hi=m.c[j] - d))
            else:
                rangos_c.append(dict(basica=False, lo=m.c[j] + d, hi=None))
    res.rangos_costo = rangos_c

    # rango del lado derecho
    rangos_b = []
    for i, r in enumerate(m.restr):
        lo, hi = None, None
        for k in range(mm):
            bk = Binv[k][i]
            if bk > 0:
                v = -xB[k] / bk
                lo = v if lo is None else max(lo, v)
            elif bk < 0:
                v = -xB[k] / bk
                hi = v if hi is None else min(hi, v)
        rangos_b.append(dict(lo=None if lo is None else r.b + lo,
                             hi=None if hi is None else r.b + hi))
    res.rangos_b = rangos_b
    res.base_final = [nombres[b] for b in base]
    return res


def verificar_scipy(res):
    """Contrasta óptimo y precios sombra con HiGHS (scipy). Devuelve (ok, detalle)."""
    try:
        import numpy as np
        from scipy.optimize import linprog
    except ImportError:
        return None, "scipy no disponible"
    m = res.modelo
    s = 1 if m.sentido == "min" else -1
    c = [float(v) * s for v in m.c]
    Aub, bub, Aeq, beq, signos = [], [], [], [], []
    for r in m.restr:
        fila = [float(v) for v in r.a]
        if r.tipo == "<=":
            Aub.append(fila); bub.append(float(r.b)); signos.append(("ub", 1))
        elif r.tipo == ">=":
            Aub.append([-v for v in fila]); bub.append(-float(r.b)); signos.append(("ub", -1))
        else:
            Aeq.append(fila); beq.append(float(r.b)); signos.append(("eq", 1))
    o = linprog(c, A_ub=Aub or None, b_ub=bub or None, A_eq=Aeq or None, b_eq=beq or None,
                bounds=[(0, None)] * len(c), method="highs")
    if o.status != 0:
        return (res.estado == "infactible" and o.status == 2), dict(estado=f"HiGHS estado {o.status}")
    z = o.fun * s
    ok_z = abs(z - float(res.z)) < 1e-6
    iu = ie = 0
    y = []
    for kind, sg in signos:
        if kind == "ub":
            y.append(o.ineqlin.marginals[iu] * sg * s); iu += 1
        else:
            y.append(o.eqlin.marginals[ie] * s); ie += 1
    ok_y = all(abs(a - float(b)) < 1e-6 for a, b in zip(y, res.precios_sombra))
    alt = False
    if not ok_y and res.degenerado and _dual_valido(res):
        ok_y = alt = True    # solución degenerada: duales alternativos, mismo valor óptimo
    return ok_z and ok_y, dict(z=z, y=y, ok_z=ok_z, ok_y=ok_y, alt=alt)


def _dual_valido(res):
    m = res.modelo
    w = sum(r.b * y for r, y in zip(m.restr, res.precios_sombra))
    if w != res.z:
        return False
    for r, y in zip(m.restr, res.precios_sombra):
        if r.tipo != "=" and ((y < 0) if (m.sentido == "min") == (r.tipo == ">=") else (y > 0)):
            return False
    return all((d >= 0) if m.sentido == "min" else (d <= 0) for d in res.costos_reducidos)


def barrido_b(m, clave, valores):
    salida = []
    for v in valores:
        r = resolver(m.variar(b={clave: v}))
        salida.append((v, r.z if r.estado == "optimo" else None, r.estado))
    return salida


def barrido_c(m, var, valores):
    salida = []
    for v in valores:
        r = resolver(m.variar(c={var: v}))
        salida.append((v, r.z if r.estado == "optimo" else None, r.estado))
    return salida


def umbral_factibilidad(m, clave, tope=64, iteraciones=40):
    """Menor valor del lado derecho de `clave` que hace factible el modelo (se busca hacia arriba)."""
    r = next(r for r in m.restr if r.clave == clave)
    lo = r.b
    hi = lo if lo > 0 else F(1)
    for _ in range(tope):
        hi *= 2
        if resolver(m.variar(b={clave: hi})).estado == "optimo":
            break
    else:
        return None
    for _ in range(iteraciones):
        mid = (lo + hi) / 2
        if resolver(m.variar(b={clave: mid})).estado == "optimo":
            hi = mid
        else:
            lo = mid
    return hi.limit_denominator(1000)


class ResultadoBinario:
    pass


def resolver_binario(m, limite=22, top=6):
    """Enumera las 2^n asignaciones 0/1 de m.vars (n <= limite) y devuelve la mejor factible exacta.
    Sirve para problemas de selección (mochila): resultado exacto, sin aproximar."""
    n = len(m.vars)
    assert n <= limite, f"Demasiadas variables para enumerar por fuerza bruta ({n} > {limite})"
    factibles = []
    for mask in range(1 << n):
        x = [F(1) if mask & (1 << i) else F(0) for i in range(n)]
        ok = True
        for r in m.restr:
            lhs = sum(a * xx for a, xx in zip(r.a, x))
            if r.tipo == "<=" and lhs > r.b:
                ok = False
            elif r.tipo == ">=" and lhs < r.b:
                ok = False
            elif r.tipo == "=" and lhs != r.b:
                ok = False
            if not ok:
                break
        if ok:
            z = sum(c * xx for c, xx in zip(m.c, x))
            factibles.append((z, x, mask))
    res = ResultadoBinario()
    res.modelo = m
    if not factibles:
        res.estado = "infactible"
        return res
    factibles.sort(key=lambda t: t[0], reverse=(m.sentido == "max"))
    res.estado = "optimo"
    res.z, res.x, res.mask = factibles[0]
    res.top = factibles[:top]
    res.n_factibles = len(factibles)
    res.n_total = 1 << n
    return res

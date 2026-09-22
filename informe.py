# -*- coding: utf-8 -*-
"""Genera Informe_Taller2.html: modelo, solución base, escenarios, precios sombra,
sensibilidad, riesgos y recomendación (todas las tablas del Simplex, sin omitir iteraciones)."""
import sys, os, re, json, hashlib, platform, datetime, webbrowser
from fractions import Fraction as F
from html import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from motor import resolver, verificar_scipy, umbral_factibilidad, ffrac, resolver_binario, planes_alternos
from modelos import MODELOS, CONFIG, REFERENCIAS, INTEGRANTES, FUENTE_PDF, FUENTE_DOCX
import graficos as G

g = G._g
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Informe_Taller2.html")
_contador = {"t": 0, "f": 0, "g": 0}


# ------------------------------------------------------------------ utilidades de formato
def num(x, dec=2):
    x = F(x)
    if x.denominator == 1:
        return g(x)
    return f'<span class="d">{g(x, dec)}</span><span class="f">{ffrac(x)}</span>'


def sg(x, dec=2):
    x = F(x)
    return ("+" if x > 0 else "") + g(x, dec)


def sub(n):
    return re.sub(r"([a-z])(\d+)", r"\1<sub>\2</sub>", n)


def expr(coefs, vars_):
    t = []
    for c, v in zip(coefs, vars_):
        if c == 0:
            continue
        c = F(c)
        pref = "" if c == 1 else ("−" if c == -1 else g(c))
        t.append(f"{pref}{sub(v)}")
    return " + ".join(t).replace("+ −", "− ") or "0"


def th(cols, cls=""):
    return "<tr>" + "".join(f"<th class='{cls}'>{c}</th>" for c in cols) + "</tr>"


def tabla(cabecera, filas, titulo=None, clase="", nota=None, numerada=True):
    """Devuelve <figure> con tabla y botón de copia."""
    if titulo and numerada:
        _contador["t"] += 1
        cap = f"<figcaption><b>Tabla {_contador['t']}.</b> {titulo}</figcaption>"
    elif titulo:
        cap = f"<figcaption>{titulo}</figcaption>"
    else:
        cap = ""
    h = "<thead>" + th(cabecera) + "</thead>"
    b = "<tbody>" + "".join("<tr>" + "".join(f if f.startswith("<td") else f"<td>{f}</td>" for f in fila) + "</tr>"
                            for fila in filas) + "</tbody>"
    n = f"<p class='nota-t'>{nota}</p>" if nota else ""
    return (f"<figure class='tbl {clase}'>{cap}<div class='scroll'><table>{h}{b}</table></div>{n}"
            f"<button class='copiar' type='button' title='Copiar como texto tabulado (pega en Word/Excel/PowerPoint)'>Copiar</button></figure>")


def td(v, cls=""):
    return f"<td class='{cls}'>{v}</td>"


def chip(txt, tipo):
    icono = {"ok": "✓", "mal": "✕", "aviso": "!", "neutro": "·"}[tipo]
    return f"<span class='chip {tipo}'><i>{icono}</i>{txt}</span>"


# ------------------------------------------------------------------ análisis por modelo
def analizar(m, cfg):
    base = resolver(m)
    assert base.estado == "optimo", "El modelo base debe tener óptimo"
    ver = verificar_scipy(base)
    esc = []
    for e in cfg["escenarios"]:
        me = m.variar(**e["var"])
        r = resolver(me)
        um = None
        if r.estado != "optimo" and e.get("umbral"):
            um = umbral_factibilidad(me, e["umbral"])
        esc.append(dict(cfg=e, modelo=me, res=r, umbral=um, verif=verificar_scipy(r)))
    barr = []
    from motor import barrido_b, barrido_c
    for bcfg in cfg["barridos"]:
        vals = set()
        v = F(str(bcfg["desde"]))
        while v <= F(str(bcfg["hasta"])):
            vals.add(v)
            v += F(str(bcfg["paso"]))
        vals |= {F(x) for x in bcfg["extra"]}
        vals = sorted(vals)
        pts = barrido_b(m, bcfg["clave"], vals) if bcfg["tipo"] == "b" else barrido_c(m, bcfg["clave"], vals)
        barr.append(dict(cfg=bcfg, pts=[(a, z) for a, z, _ in pts]))
    return dict(m=m, cfg=cfg, base=base, ver=ver, esc=esc, barr=barr)


def _nombre_restr(m, clave):
    return next(r.nombre for r in m.restr if r.clave == clave)


def obj_de(m):
    return getattr(m, "obj", "costo" if m.sentido == "min" else "ingreso")


def peor_si_sube(m):
    return getattr(m, "peor_si_sube", m.sentido == "min")


def adverso(m, z, z0):
    """Desvío adverso del objetivo respecto a la base (positivo = empeora)."""
    return (z - z0) if peor_si_sube(m) else (z0 - z)


def idx(m, clave):
    return next(i for i, r in enumerate(m.restr) if r.clave == clave)


# ------------------------------------------------------------------ secciones
def s_modelo(A, k):
    m, cfg, r = A["m"], A["cfg"], A["base"]
    sentido = "Minimizar" if m.sentido == "min" else "Maximizar"
    zu = m.unidad_z
    td_ = cfg["tabla_datos"]
    t_datos = tabla(td_["cols"], [[str(c) for c in f] for f in td_["filas"]], "Datos de entrada tomados del enunciado del Taller")
    dominio_lbl = "0 ≤ xⱼ ≤ 1 (real: 0 ó 1)" if cfg.get("binario") else "≥ 0"
    t_vars = tabla(["Variable", "Significado", "Dominio"],
                   [[sub(v), d, dominio_lbl] for v, d in zip(m.vars, m.vars_desc)], "Variables de decisión")
    fo = f"<div class='math'>{sentido} &nbsp;Z = {expr(m.c, m.vars)} <span class='u'>[{zu}]</span></div>"
    filas = []
    tipo_txt = {"<=": "≤", ">=": "≥", "=": "="}
    for i, rs in enumerate(m.restr):
        filas.append([f"R{i+1}", rs.nombre, f"<span class='mono'>{expr(rs.a, m.vars)} {tipo_txt[rs.tipo]} {g(rs.b)}</span>",
                      g(rs.b), rs.unidad])
    t_res = tabla(["#", "Restricción", "Expresión", "Lado derecho", "Unidad"], filas, "Restricciones")
    # forma estándar
    est = []
    for i, rs in enumerate(m.restr):
        if rs.tipo == "<=":
            est.append([f"R{i+1}", "≤", f"+ s<sub>{i+1}</sub> (holgura)", "s<sub>%d</sub>" % (i + 1)])
        elif rs.tipo == ">=":
            est.append([f"R{i+1}", "≥", f"− e<sub>{i+1}</sub> (exceso) + a<sub>{i+1}</sub> (artificial)", "a<sub>%d</sub>" % (i + 1)])
        else:
            est.append([f"R{i+1}", "=", f"+ a<sub>{i+1}</sub> (artificial)", "a<sub>%d</sub>" % (i + 1)])
    t_est = tabla(["Restricción", "Tipo", "Variable agregada", "Base inicial"], est, "Forma estándar y base inicial",
                  nota="Con variables artificiales se aplica el Simplex de Dos Fases (Fase 1: minimizar la suma de artificiales; "
                       "Fase 2: optimizar la función objetivo real).")
    # trazabilidad de datos
    h = hashlib.sha256(json.dumps(dict(c=[str(v) for v in m.c], r=[(x.clave, [str(a) for a in x.a], x.tipo, str(x.b)) for x in m.restr]),
                                   sort_keys=True).encode()).hexdigest()[:12]
    A["hash"] = h
    filas_t = [[f"c<sub>{j+1}</sub>", g(m.c[j]), cfg["fuente"].split(" · ")[0]] for j in range(len(m.vars))]
    filas_t += [[f"b<sub>{i+1}</sub> · {rs.nombre}", f"{tipo_txt[rs.tipo]} {g(rs.b)} {rs.unidad}", cfg["fuente"].split(" · ")[0]]
                for i, rs in enumerate(m.restr)]
    t_tr = tabla(["Parámetro", "Valor", "Fuente"], filas_t, f"Trazabilidad de parámetros (hash SHA-256 del modelo: <span class='mono'>{h}</span>)")
    return f"""<section id="{k}-modelo"><h2><span>1</span>Modelo estandarizado</h2>
<p class="lead">{cfg['contexto']}</p>
<div class="grid2"><div>{t_datos}</div><div>{t_vars}</div></div>
<h3>Función objetivo</h3>{fo}
<h3>Restricciones</h3>{t_res}
<div class="math sm">Sujeto a R1…R{len(m.restr)} &nbsp;y&nbsp; {", ".join(sub(v) for v in m.vars)} {"∈ {0, 1}" if cfg.get("binario") else "≥ 0"}</div>
<div class="grid2"><div>{t_est}</div><div>{t_tr}</div></div></section>"""


def html_simplex(t, m, fase_txt):
    _contador["f"] += 1
    n = _contador["f"]
    cols = t["cols"]
    pv = t["pivote"]
    esta_opt = t["optima"]
    cab = ["Base"] + [sub(c) for c in cols] + ["LD"] + (["Razón"] if t["razones"] else [])
    hh = "<tr>" + "".join(
        f"<th class='{'ent' if (t['entra'] and i - 1 == pv[1]) else ''}'>{c}</th>" for i, c in enumerate(cab)) + "</tr>"
    filas = []
    for i, (b, fila) in enumerate(zip(t["base"], t["filas"])):
        cel = [f"<th class='fila {'sal' if pv and i == pv[0] else ''}'>{sub(b)}</th>"]
        for j, v in enumerate(fila):
            cls = "piv" if pv and (i, j) == pv else ""
            cel.append(f"<td class='{cls}'>{num(v)}</td>")
        if t["razones"]:
            rz = t["razones"][i]
            cel.append(f"<td class='razon {'min' if pv and i == pv[0] else ''}'>{num(rz) if rz is not None else '—'}</td>")
        filas.append("<tr>" + "".join(cel) + "</tr>")
    z = t["z"]
    etq_z = "Zj − Cj"
    if t["fase"] == 1:
        etq_z = "Zj − Cj (Fase 1)"
    cel = [f"<th class='fila z'>{etq_z}</th>"] + [f"<td class='z'>{num(v)}</td>" for v in z]
    if t["razones"]:
        cel.append("<td class='z'></td>")
    filas.append("<tr>" + "".join(cel) + "</tr>")
    if esta_opt:
        estado = chip("Óptima: todos los Zj − Cj ≥ 0", "ok")
    elif t["entra"]:
        k_ent = t["cols"].index(t["entra"])
        rz = t["razones"][pv[0]]
        estado = (f"<span class='dec'>Entra <b>{sub(t['entra'])}</b> (Zj − Cj = {num(z[k_ent])}, el más negativo)</span>"
                  f"<span class='dec'>Sale <b>{sub(t['sale'])}</b> (razón mínima = {num(rz)})</span>"
                  f"<span class='dec'>Pivote = {num(t['filas'][pv[0]][pv[1]])}</span>")
    else:
        estado = chip("No acotado", "mal")
    nota_min = ""
    if m.sentido == "min" and t["fase"] == 2:
        nota_min = " · La fila Zj − Cj trabaja con Z′ = −Z (forma de maximización); Z = −(LD de esa fila)."
    if t["fase"] == 1:
        nota_min = " · Fase 1: LD de la fila Zj − Cj = −(suma de artificiales)."
    return (f"<figure class='tbl simplex'><figcaption><b>Tabla S{n}.</b> {fase_txt} · iteración {t['iter']}"
            f"<span class='sub'>{nota_min.lstrip(' ·')}</span></figcaption>"
            f"<div class='scroll'><table><thead>{hh}</thead><tbody>{''.join(filas)}</tbody></table></div>"
            f"<div class='decision'>{estado}</div>"
            f"<button class='copiar' type='button'>Copiar</button></figure>")


def todas_las_tablas(res, m):
    out = []
    for t in res.tablas:
        out.append(html_simplex(t, m, "Fase 1 — factibilidad" if t["fase"] == 1 else ("Fase 2 — optimalidad" if res.w_fase1 is not None else "Simplex — optimalidad")))
    return "".join(out)


def uso_recursos(A, res=None, m=None):
    r = res or A["base"]
    m = m or A["m"]
    filas = []
    for i, rs in enumerate(m.restr):
        h = r.holgura[i]
        if rs.tipo == "=":
            est = chip("Igualdad cumplida", "neutro")
        elif h == 0:
            est = chip("Activa (agotada)" if rs.tipo == "<=" else "Activa (en el mínimo)", "aviso")
        else:
            est = chip(f"Holgura {g(h)}", "ok")
        filas.append([rs.nombre, {"<=": "≤", ">=": "≥", "=": "="}[rs.tipo], g(rs.b), g(r.uso[i]), g(h) if rs.tipo != "=" else "—", est])
    return tabla(["Restricción", "Tipo", "Disponible / exigido", "Uso en el óptimo", "Holgura", "Estado"], filas, "Uso de recursos en la solución óptima")


def s_base(A, k):
    m, r, ver = A["m"], A["base"], A["ver"]
    zu = m.unidad_z
    sol = tabla(["Variable", "Significado", "Valor óptimo", "Estado en la base"],
                [[sub(v), d, num(x), chip("Básica", "ok") if x > 0 else chip("No básica", "neutro")]
                 for v, d, x in zip(m.vars, m.vars_desc, r.x)], "Solución óptima")
    n_it = sum(1 for t in r.tablas if not t["optima"])
    fases = "Dos Fases" if r.w_fase1 is not None else "una fase"
    kpi = (f"<div class='kpis'><div class='kpi'><small>Valor óptimo Z*</small><b>{g(r.z)}</b><span>{zu}</span></div>"
           f"<div class='kpi'><small>Plan</small><b class='sm'>({', '.join(g(x) for x in r.x)})</b><span>{', '.join(sub(v) for v in m.vars)}</span></div>"
           f"<div class='kpi'><small>Iteraciones</small><b>{n_it}</b><span>Simplex de {fases}</span></div>"
           f"<div class='kpi'><small>Base final</small><b class='sm'>{', '.join(sub(b) for b in r.base_final)}</b><span>{'no degenerada' if not r.degenerado else 'degenerada'}</span></div></div>")
    ok, det = ver
    comp = tabla(["Magnitud", "Simplex propio (exacto)", "SciPy · HiGHS", "Coincide"],
                 [["Valor óptimo Z*", g(r.z), g(det["z"]), chip("Sí", "ok") if det["ok_z"] else chip("No", "mal")]] +
                 [[f"Precio sombra R{i+1} · {rs.nombre}", num(y), g(round(det["y"][i], 9)), chip("Sí", "ok") if abs(float(y) - det["y"][i]) < 1e-6 else chip("No", "mal")]
                  for i, (rs, y) in enumerate(zip(m.restr, r.precios_sombra))],
                 "Evidencia del solver: verificación cruzada con SciPy (HiGHS)")
    nota_bin = (f"<p class='muted'><b>Nota.</b> Como xⱼ debe ser 0 ó 1, esta tabla es la relajación lineal continua; "
                "el óptimo entero exacto (el plan realizable) está en la subsección «Óptimo entero exacto» más abajo.</p>") if A["cfg"].get("binario") else ""
    return f"""<section id="{k}-base"><h2><span>2</span>Solución base</h2>{kpi}{nota_bin}
<div class="grid2"><div>{sol}</div><div>{uso_recursos(A)}</div></div>
<h3>Tablas del método Simplex</h3>
<p class="muted">Cada iteración se muestra completa: columna que entra (encabezado resaltado), fila que sale y elemento pivote. El interruptor «Fracciones» del encabezado muestra los valores exactos.</p>
{todas_las_tablas(r, m)}
<h3>Evidencia del solver</h3>{comp}
<p class="muted">El resultado del Simplex programado coincide con HiGHS (Huangfu &amp; Hall, 2018), el solver de SciPy (Virtanen et al., 2020).</p>
{bloque_alternos(A)}{bloque_verificacion(A)}{bloque_entero(A)}</section>"""


def bloque_alternos(A):
    m, r = A["m"], A["base"]
    alt = [m.vars[j] for j in range(len(m.vars)) if m.vars[j] not in r.base_final and r.costos_reducidos[j] == 0]
    if not alt:
        return ""
    txt = ("<p class='muted'><b>Óptimos alternativos.</b> " + ", ".join(sub(a) for a in alt) +
           f" tiene costo reducido 0 fuera de la base: existen otros planes con el mismo valor óptimo ({g(r.z)}). "
           "El de la tabla final es uno de ellos; cualquier plan factible con ese valor también es óptimo.</p>")
    planes = planes_alternos(m)
    if not planes:
        return txt
    filas = [[sub(v), ", ".join(f"{sub(vv)} = {g(x)}" for vv, x in zip(m.vars, xs)), g(z)] for v, xs, z in planes]
    t = tabla(["Variable que entra", "Plan alterno", "Valor (igual al óptimo)"], filas,
              "Otros planes óptimos calculados (mismo valor, distinta asignación)",
              nota="Cada uno se obtuvo forzando a entrar a la variable indicada (sesgo infinitesimal en su coeficiente) y resolviendo de nuevo; "
                   "se conservan solo los que dan exactamente el mismo valor óptimo con el modelo original.")
    return txt + t


def bloque_entero(A):
    """Para modelos 0/1 (mochila): resuelve el óptimo entero exacto por enumeración y lo compara con la relajación lineal."""
    cfg, m, r = A["cfg"], A["m"], A["base"]
    if not cfg.get("binario"):
        return ""
    rb = resolver_binario(m)
    icap = idx(m, "CAP") if any(rs.clave == "CAP" for rs in m.restr) else 0
    peso = sum(m.restr[icap].a[j] * rb.x[j] for j in range(len(m.vars)))
    sel = ", ".join(str(j + 1) for j in range(len(m.vars)) if rb.x[j] == 1) or "ninguno"
    gap = r.z - rb.z
    pct = float(gap / rb.z * 100) if rb.z else 0
    filas = []
    for z, x, mask in rb.top:
        items = ", ".join(str(j + 1) for j in range(len(m.vars)) if x[j] == 1) or "—"
        pw = sum(m.restr[icap].a[j] * x[j] for j in range(len(m.vars)))
        filas.append([items, g(z), f"{g(pw)} / {g(m.restr[icap].b)}", chip("Óptimo entero", "ok") if z == rb.z else "—"])
    t = tabla(["Artículos incluidos", "Valor", "Peso usado / capacidad", ""], filas,
              f"Mejores combinaciones factibles (enumeración exacta: {rb.n_factibles} de {rb.n_total} combinaciones cumplen la capacidad)")
    return (f"<h3>Óptimo entero exacto (0/1)</h3>"
            f"<p class='muted'>La solución óptima de arriba es la <b>relajación lineal</b> (0 ≤ xⱼ ≤ 1): da <b>{g(r.z)} {m.unidad_z}</b>, "
            f"una cota superior, no un plan realizable (no se puede llevar el 86 % de un artículo). Por tratarse de solo "
            f"{len(m.vars)} artículos (2<sup>{len(m.vars)}</sup> = {rb.n_total} combinaciones), se calculó también el óptimo entero "
            f"exacto por enumeración completa.</p>"
            f"<p class='lead'><b>Selección recomendada:</b> artículos {sel} — valor exacto <b>{g(rb.z)} {m.unidad_z}</b>, "
            f"peso {g(peso)} de {g(m.restr[icap].b)} lb. Brecha con la relajación: {g(gap)} ({g(pct,1)} %).</p>{t}")


def bloque_verificacion(A):
    v = A["cfg"].get("verificar")
    if not v:
        return ""
    m = A["m"]
    x = [F(a) for a in v["x"]]
    u = [F(a) for a in v["u"]]
    tt = {"<=": "≤", ">=": "≥", "=": "="}
    filas = []
    for i, rs in enumerate(m.restr):
        lhs = sum(a * xx for a, xx in zip(rs.a, x))
        ok = lhs >= rs.b if rs.tipo == ">=" else lhs <= rs.b if rs.tipo == "<=" else lhs == rs.b
        filas.append([f"R{i+1} · {rs.nombre}", g(lhs), f"{tt[rs.tipo]} {g(rs.b)}", chip("Cumple", "ok") if ok else chip("No cumple", "mal")])
    z = sum(c * xx for c, xx in zip(m.c, x))
    t1 = tabla(["Restricción", "Valor con la solución", "Exigencia", "Estado"], filas,
               f"{v['titulo']}: factibilidad de ({', '.join(g(a) for a in x)}), valor {g(z)}")
    filas2 = []
    for j, nm in enumerate(m.vars):
        sj = sum(rs.a[j] * uu for rs, uu in zip(m.restr, u))
        ok = sj <= m.c[j] if m.sentido == "min" else sj >= m.c[j]
        filas2.append([sub(nm), g(sj), f"{'≤' if m.sentido == 'min' else '≥'} {g(m.c[j])}", chip("Cumple", "ok") if ok else chip("No cumple", "mal")])
    w = sum(rs.b * uu for rs, uu in zip(m.restr, u))
    t2 = tabla(["Restricción dual", "Σ aᵢⱼuᵢ", "Debe ser", "Estado"], filas2,
               f"Certificado dual u = ({', '.join(g(a) for a in u)}): valor W = Σ bᵢuᵢ = {g(w)}",
               nota=f"{v['nota']} Resultado: {chip('Z = W = ' + g(z), 'ok') if z == w else chip('Z ≠ W', 'mal')}")
    return f"<h3>{v['titulo']}</h3><div class='grid2'><div>{t1}</div><div>{t2}</div></div>"


def s_escenarios(A, k):
    m, cfg, base = A["m"], A["cfg"], A["base"]
    zu = m.unidad_z
    obj = obj_de(m).capitalize()
    obj_col = obj + (" mínimo" if m.sentido == "min" else " máximo")
    # definición
    deff = []
    for e in A["esc"]:
        cambios = []
        tipos_det = set()
        for i, rs in enumerate(e["modelo"].restr):
            if i < len(m.restr):
                if rs.b != m.restr[i].b:
                    cambios.append(f"{rs.nombre}: {g(m.restr[i].b)} → {g(rs.b)} {rs.unidad}")
                    tipos_det.add("recurso")
                for j, v in enumerate(m.vars):
                    if rs.a[j] != m.restr[i].a[j]:
                        cambios.append(f"Coeficiente técnico de {sub(v)} en «{rs.nombre}»: {g(m.restr[i].a[j])} → {g(rs.a[j])} {rs.unidad}")
                        tipos_det.add("tecnico")
            else:
                cambios.append(f"Nueva restricción «{rs.nombre}» {'≤' if rs.tipo == '<=' else rs.tipo} {g(rs.b)} {rs.unidad}")
                tipos_det.add("estructural")
        for j, v in enumerate(m.vars):
            if e["modelo"].c[j] != m.c[j]:
                cambios.append(f"Coeficiente objetivo de {sub(v)}: {g(m.c[j])} → {g(e['modelo'].c[j])}")
                tipos_det.add("costo")
        if "estructural" in tipos_det:
            tipo = "Presupuesto (estructural)"
        elif len(tipos_det) > 1:
            tipo = "Combinada"
        elif tipos_det == {"costo"}:
            tipo = "Costo / precio"
        elif tipos_det == {"tecnico"}:
            tipo = "Parámetro técnico"
        else:
            tipo = "Recurso / demanda"
        deff.append([f"<b>{e['cfg']['id']}</b>{' ★' if e['cfg']['top'] else ''}", e["cfg"]["nombre"], "<br>".join(cambios), tipo])
    t_def = tabla(["ID", "Escenario", "Variación paramétrica", "Tipo"], deff, "Definición de escenarios",
                  nota="★ = escenarios sugeridos para las diapositivas (los demás quedan como anexo).")
    # comparativa
    extra_cab, extra_fn = _cols_extra(A)
    cab = ["ID", "Estado", f"{obj_col} ({zu})", "Δ", "Δ %"] + extra_cab + ["Plan óptimo", "¿Cambia el plan?"]
    z0 = base.z
    filas = []
    dat_barras = []
    filas.append(["<b>Base</b>", chip("Factible", "ok"), g(z0), "—", "—"] + extra_fn(base, m, None) + [", ".join(g(x) for x in base.x), "—"])
    for e in A["esc"]:
        r, me = e["res"], e["modelo"]
        if r.estado != "optimo":
            extra = f" · requiere {_nombre_restr(e['modelo'], e['cfg']['umbral']).lower()} ≥ {g(e['umbral'])}" if e["umbral"] else ""
            filas.append([f"<b>{e['cfg']['id']}</b>", chip("Infactible" + extra, "mal"), "—", "—", "—"] + ["—"] * len(extra_cab) + ["—", "—"])
            dat_barras.append((e["cfg"]["id"], e["cfg"]["nombre"], None, None))
            continue
        d = r.z - z0
        pct = float(d / z0 * 100)
        dat_barras.append((e["cfg"]["id"], e["cfg"]["nombre"], d, pct))
        filas.append([f"<b>{e['cfg']['id']}</b>{' ★' if e['cfg']['top'] else ''}", (chip("Factible", "ok") if not r.degenerado else chip("Factible · degenerado", "aviso")), g(r.z), sg(d), f"{sg(pct,1)} %"] +
                     extra_fn(r, me, e["cfg"]["id"]) + [", ".join(g(x) for x in r.x), "No" if r.x == base.x else "Sí"])
    deg = [e["cfg"]["id"] for e in A["esc"] if e["res"].estado == "optimo" and e["res"].degenerado]
    if deg and base.degenerado:
        nota_deg = ("La base es degenerada (una variable básica vale 0) desde la solución base y en todos los escenarios factibles; "
                    "el valor óptimo es único, pero los precios sombra pueden no serlo y HiGHS puede reportar otros duales equivalentes.")
    elif deg:
        nota_deg = (f"{', '.join(deg)}: solución degenerada (una variable básica vale 0, el escenario cae justo en el borde de un rango); "
                    "el valor óptimo es único pero los precios sombra pueden no serlo, y HiGHS puede reportar otros duales equivalentes.")
    else:
        nota_deg = None
    t_cmp = tabla(cab, filas, "Comparación de escenarios: costo, tiempo y servicio", "ancha cmp", nota=nota_deg)
    _contador["g"] += 1
    graf = G.barras_delta(dat_barras, zu, "baja" if peor_si_sube(m) else "sube")
    # precios sombra por escenario
    filas_y = [["<b>Base</b>"] + [num(y) for y in base.precios_sombra]]
    for e in A["esc"]:
        r = e["res"]
        filas_y.append([f"<b>{e['cfg']['id']}</b>"] + ([num(y) for y in r.precios_sombra] if r.estado == "optimo" else ["—"] * len(m.restr)))
    t_y = tabla(["ID"] + [f"y<sub>{i+1}</sub> · {rs.nombre}" for i, rs in enumerate(m.restr)], filas_y, "Precios sombra por escenario",
                nota="Cuando un recurso pasa de holgado a agotado (o viceversa) su precio sombra cambia: es la señal de que la estructura del problema cambió.")
    # detalle simplex por escenario
    det = []
    for e in A["esc"]:
        r, me = e["res"], e["modelo"]
        head = f"{e['cfg']['id']} · {e['cfg']['nombre']} — {e['cfg']['desc']}"
        if r.estado == "optimo":
            cuerpo = (f"<p>{chip('Factible', 'ok')} Z* = <b>{g(r.z)}</b> {zu} · plan ({', '.join(g(x) for x in r.x)})</p>"
                      f"{uso_recursos(A, r, me)}{todas_las_tablas(r, me)}")
        else:
            cuerpo = (f"<p>{chip('Infactible', 'mal')} La Fase 1 termina con la suma de artificiales = {g(r.w_fase1)} > 0: no existe plan que cumpla todas las restricciones."
                      + (f" Se restablece la factibilidad con «{_nombre_restr(me, e['cfg']['umbral']).lower()}» ≥ <b>{g(e['umbral'])}</b>." if e["umbral"] else "") + "</p>"
                      f"{todas_las_tablas(r, me)}")
        det.append(f"<details><summary>{head}</summary>{cuerpo}</details>")
    # conclusión rápida
    ok = [e for e in A["esc"] if e["res"].estado == "optimo"]
    inf = [e for e in A["esc"] if e["res"].estado != "optimo"]
    ver_ok = sum(1 for e in A["esc"] if e["verif"][0])
    resumen = (f"<p class='lead'>{len(ok)} de {len(A['esc'])} escenarios son factibles; {len(inf)} pierden la factibilidad "
               f"({', '.join(e['cfg']['id'] for e in inf)}). Los {len(A['esc'])} resultados coinciden con HiGHS en estado "
               f"y valor óptimo ({ver_ok}/{len(A['esc'])}).</p>")
    return f"""<section id="{k}-escenarios"><h2><span>3</span>Escenarios</h2>{resumen}
{t_def}{t_cmp}
<figure class="chartbox"><figcaption><b>Gráfico 1.</b> Impacto de cada escenario en el {obj.lower()} respecto a la base</figcaption>{graf}</figure>
{t_y}
<h3>Detalle completo de cada escenario</h3><p class="muted">Cada escenario se resolvió con el mismo método; despliega para ver todas sus tablas.</p>
{''.join(det)}</section>"""


def _fila_met(A, r, me):
    d = metricas(A, r, me)
    return [g(d["mo"][0]) + " / " + g(d["mo"][1]), g(d["mp"][0]) + " / " + g(d["mp"][1]), g(d["unid"]),
            g(d["clave"][0]) + " / " + g(d["clave"][1])]


def _cols_extra(A):
    """Columnas propias de cada ejercicio para la tabla comparativa → (cabeceras, función(r, me, eid))."""
    m = A["m"]
    if m.clave == "winco":
        def fn(r, me, eid):
            iMO, iMP, iD4 = idx(me, "MO"), idx(me, "MP"), idx(me, "D4")
            return [f"{g(r.uso[iMO])} / {g(me.restr[iMO].b)}", f"{g(r.uso[iMP])} / {g(me.restr[iMP].b)}",
                    g(sum(r.x)), f"{g(r.x[3])} / {g(me.restr[iD4].b)}"]
        return (["Tiempo · horas MO (uso / disp.)", "Materia prima (uso / disp.)", "Servicio · unidades entregadas", "Producto 4 (x₄ / mín.)"], fn)
    if m.clave == "mochila":
        def fn(r, me, eid):
            icap = idx(me, "CAP")
            peso = sum(me.restr[icap].a[j] * r.x[j] for j in range(len(me.vars)))
            rb = resolver_binario(me)
            if rb.estado != "optimo":
                return [f"{g(peso)} / {g(me.restr[icap].b)}", "—", "—", "—"]
            items = ", ".join(str(j + 1) for j in range(len(me.vars)) if rb.x[j] == 1) or "ninguno"
            gap = r.z - rb.z
            pct = float(gap / rb.z * 100) if rb.z else 0
            return [f"{g(peso)} / {g(me.restr[icap].b)}", items, g(rb.z), f"{g(gap)} ({g(pct,1)} %)"]
        return (["Peso usado / capacidad (relajación)", "Selección entera exacta", "Valor entero exacto", "Brecha relajación − entero"], fn)
    if m.clave == "farmatodo":
        n_periodos = len(m.vars)

        def fn(r, me, eid):
            return [g(sum(r.x)), g(8 * sum(r.x)), g(sum(r.holgura)), f"{n_periodos} / {n_periodos}"]
        return (["Costo · personal contratado (Σx)", "Tiempo · horas-persona (8 h × Σx)", "Servicio · exceso de cobertura (Σ)", "Periodos cubiertos"], fn)
    if m.clave == "plasticos":
        def fn(r, me, eid):
            iF1, iF2 = idx(me, "F1"), idx(me, "F2")
            dem_tot = sum(r.uso[i] for i, rs in enumerate(me.restr) if rs.clave.startswith("D"))
            return [f"{g(r.uso[iF1])} / {g(me.restr[iF1].b)}", f"{g(r.uso[iF2])} / {g(me.restr[iF2].b)}",
                    g(dem_tot), str(sum(1 for x in r.x if x > 0))]
        return (["Oferta F1 (uso / disp.)", "Oferta F2 (uso / disp.)", "Demanda total cubierta (cajas)", "Rutas activas"], fn)
    return ([], lambda r, me, eid: [])


def traduccion(r, i):
    m = r.modelo
    rs, y, h, rg = m.restr[i], r.precios_sombra[i], r.holgura[i], r.rangos_b[i]
    if getattr(rs, "auxiliar", False):
        return ("Restricción técnica de la formulación 0/1 (cota xⱼ ≤ 1): su precio sombra no tiene una lectura de negocio directa, "
                "solo mantiene la relajación lineal dentro de los límites 0/1.")
    obj = obj_de(m)
    zu = m.unidad_z
    lo = "sin límite inferior" if rg["lo"] is None else g(rg["lo"])
    hi = "sin límite superior" if rg["hi"] is None else g(rg["hi"])
    if rg["lo"] is None and rg["hi"] is None:
        vale = "sin límites"
    elif rg["hi"] is None:
        vale = f"por encima de {lo} {rs.unidad}"
    elif rg["lo"] is None:
        vale = f"por debajo de {hi} {rs.unidad}"
    elif rg["lo"] == rg["hi"]:
        vale = f"únicamente en el valor actual ({lo} {rs.unidad}): al ser un sistema balanceado, cualquier cambio aislado lo vuelve infactible"
    else:
        vale = f"entre {lo} y {hi} {rs.unidad}"
    if rs.tipo == ">=" and h > 0:
        return (f"<b>Cobertura con excedente.</b> Hay {g(h)} {rs.unidad} de más sobre lo exigido: la exigencia puede subir hasta {hi} "
                f"sin cambiar el {obj} (precio sombra 0).")
    if rs.tipo == "<=" and h > 0:
        return (f"<b>Recurso con holgura.</b> Sobran {g(h)} {rs.unidad}: más cantidad no mejora el {obj} (precio sombra 0). "
                f"Se puede reducir hasta {lo} {rs.unidad} sin afectar el plan.")
    if y == 0:
        return "Sin efecto marginal en el objetivo dentro del rango."
    sube = y > 0
    favorable = (not sube) if m.sentido == "min" else sube
    sujeto = f"Una unidad más de «{rs.nombre.lower()}»" if rs.tipo == "<=" else f"Exigir una unidad más en «{rs.nombre.lower()}»"
    return (f"{sujeto} {'sube' if sube else 'baja'} el {obj} en <b>{g(abs(y))} {zu}</b> "
            f"({'favorable' if favorable else 'desfavorable'}). Vale mientras esté {vale}.")


def s_sombra(A, k):
    m, r = A["m"], A["base"]
    zu = m.unidad_z
    filas = []
    for i, rs in enumerate(m.restr):
        y = r.precios_sombra[i]
        rg = r.rangos_b[i]
        filas.append([f"R{i+1} · {rs.nombre}", {"<=": "≤", ">=": "≥", "=": "="}[rs.tipo], g(rs.b), td(f"<b>{num(y)}</b>", "num"),
                      getattr(m, "unidad_sombra", f"{zu} / {rs.unidad}"), traduccion(r, i)])
    t_y = tabla(["Restricción", "Tipo", "Lado derecho", "Precio sombra", "Unidad", "Traducción para el decisor"], filas,
                "Precios sombra e interpretación operativa", "interp",
                nota="Signo: cambio del valor óptimo por cada unidad adicional del lado derecho de la restricción.")
    # dualidad
    signo = {("min", ">="): "≥ 0", ("min", "<="): "≤ 0", ("max", "<="): "≥ 0", ("max", ">="): "≤ 0"}
    filas_d = []
    for i, rs in enumerate(m.restr):
        h = r.holgura[i]
        filas_d.append([f"y<sub>{i+1}</sub> · {rs.nombre}", signo.get((m.sentido, rs.tipo), "libre"), num(r.precios_sombra[i]),
                        g(h) if rs.tipo != "=" else "0", chip("y·holgura = 0", "ok") if r.precios_sombra[i] * h == 0 else chip("no cumple", "mal")])
    w = sum(rs.b * y for rs, y in zip(m.restr, r.precios_sombra))
    t_d = tabla(["Variable dual", "Signo permitido", "Valor", "Holgura primal", "Holgura complementaria"], filas_d,
                "Dualidad: variables duales y holguras complementarias",
                nota=f"Dualidad fuerte: W = Σ bᵢyᵢ = {g(w)} = Z* = {g(r.z)} {chip('Coinciden', 'ok') if w == r.z else chip('No coinciden', 'mal')}")
    filas_v = [[sub(v), num(x), num(dj), chip("x·d = 0", "ok") if x * dj == 0 else chip("no cumple", "mal")]
               for v, x, dj in zip(m.vars, r.x, r.costos_reducidos)]
    t_v = tabla(["Variable", "Valor óptimo", "Costo reducido dⱼ = cⱼ − Σ aᵢⱼyᵢ", "Holgura complementaria"], filas_v,
                "Costos reducidos y holguras complementarias (restricciones duales)")
    return f"""<section id="{k}-sombra"><h2><span>4</span>Precios sombra</h2>{t_y}<h3>Dualidad</h3>
<div class="grid2"><div>{t_d}</div><div>{t_v}</div></div></section>"""


def s_sensibilidad(A, k):
    m, r = A["m"], A["base"]
    zu = m.unidad_z
    filas = []
    for j, v in enumerate(m.vars):
        rg = r.rangos_costo[j]
        lo, hi = rg["lo"], rg["hi"]
        lo_t = "−∞" if lo is None else num(lo)
        hi_t = "+∞" if hi is None else num(hi)
        if rg["basica"]:
            lec = f"Mientras {sub('c'+v[1:])} esté en [{lo_t}, {hi_t}] el plan óptimo no cambia (solo cambia Z)."
        else:
            lec = f"Variable no básica: entra al plan solo si su coeficiente {'baja de' if m.sentido == 'min' else 'sube de'} {lo_t if m.sentido == 'min' else hi_t}."
        filas.append([sub(v), num(m.c[j]), chip("Básica", "ok") if rg["basica"] else chip("No básica", "neutro"), num(r.costos_reducidos[j]),
                      lo_t, hi_t, G.barra_rango(lo, hi, m.c[j]), lec])
    t_c = tabla(["Variable", "c actual", "Estado", "Costo reducido", "Límite inferior", "Límite superior", "Rango de optimalidad", "Lectura"],
                filas, "Rangos de optimalidad de los coeficientes de la función objetivo", "ancha")
    filas_b = []
    for i, rs in enumerate(m.restr):
        rg = r.rangos_b[i]
        lo_t = "−∞" if rg["lo"] is None else num(rg["lo"])
        hi_t = "+∞" if rg["hi"] is None else num(rg["hi"])
        lectura_b = ("Restricción técnica (cota 0/1): sin lectura de negocio directa." if getattr(rs, "auxiliar", False)
                     else f"El precio sombra de {num(r.precios_sombra[i])} {zu}/u solo vale dentro de [{lo_t}, {hi_t}].")
        filas_b.append([f"R{i+1} · {rs.nombre}", num(rs.b), lo_t, hi_t, G.barra_rango(rg["lo"], rg["hi"], rs.b), td(f"<b>{num(r.precios_sombra[i])}</b>", "num"),
                        lectura_b])
    t_b = tabla(["Restricción", "b actual", "Mínimo", "Máximo", "Rango de validez", "Precio sombra", "Lectura"], filas_b,
                "Rangos de factibilidad del lado derecho (validez de los precios sombra)", "ancha")
    graficos = []
    for bi, b in enumerate(A["barr"]):
        bc = b["cfg"]
        if bc["tipo"] == "b":
            i = idx(m, bc["clave"])
            rg = r.rangos_b[i]
            xb, banda, btxt = m.restr[i].b, (rg["lo"], rg["hi"]), "Rango donde el precio sombra es válido"
        else:
            j = m.vars.index(bc["clave"])
            rg = r.rangos_costo[j]
            xb, banda, btxt = m.c[j], (rg["lo"], rg["hi"]), "Rango donde el plan óptimo no cambia"
        _contador["g"] += 1
        svg = G.linea(b["pts"], xb, r.z, banda, btxt, bc["titulo"], bc["x"], f"{obj_de(m).capitalize()} ({zu})",
                      bc["extra"], f"{k}{bi}")
        datos = tabla([bc["x"], "Valor óptimo Z*"], [[g(x), g(z) if z is not None else chip("Infactible", "mal")] for x, z in b["pts"]],
                      None, numerada=False)
        graficos.append(f"<figure class='chartbox'><figcaption><b>Gráfico {_contador['g']+1}.</b> {bc['titulo']}</figcaption>{svg}"
                        f"<details><summary>Ver datos del gráfico</summary>{datos}</details></figure>")
    return f"""<section id="{k}-sensibilidad"><h2><span>5</span>Análisis de sensibilidad</h2>
<p class="muted">Base {'no degenerada: los precios sombra y los rangos son únicos.' if not r.degenerado else 'degenerada: interpretar los rangos con cautela.'}
Verificado por reoptimización: dentro de cada rango el resultado no cambia; un poco fuera, sí.</p>
{t_c}{t_b}<h3>Curvas de sensibilidad</h3><div class="grid2 charts">{''.join(graficos)}</div></section>"""


# ------------------------------------------------------------------ riesgos y recomendación
def impacto(A, e):
    r, base = e["res"], A["base"]
    if r.estado != "optimo":
        return 5, "Infactible"
    adv = adverso(A["m"], r.z, base.z)
    pct = float(adv / abs(base.z) * 100)
    if pct == 0:
        return 1, "sin cambio en el objetivo"
    if pct < 0:
        return 1, f"{sg(pct, 1)} % (favorable)"
    return (4 if pct >= 10 else 3 if pct >= 5 else 2 if pct >= 2 else 1), f"{sg(pct,1)} % adverso"


def lista_riesgos(A):
    m, r, key = A["m"], A["base"], A["m"].clave
    E = {e["cfg"]["id"]: e for e in A["esc"]}
    z = lambda i: g(E[i]["res"].z)
    dz = lambda i: sg(E[i]["res"].z - r.z)
    um = lambda i: g(E[i]["umbral"])
    y = lambda c: g(abs(r.precios_sombra[idx(m, c)]))
    rb = lambda c: r.rangos_b[idx(m, c)]
    zu = m.unidad_z
    if key == "winco":
        R = [
            dict(id="R1", nombre="Recorte de materia prima", esc="E1", prob=4,
                 evid=f"Cada unidad vale {y('MP')} {zu} solo dentro de [{g(rb('MP')['lo'])}, {g(rb('MP')['hi'])}]. A 4 140 u (fuera del rango) el ingreso baja {dz('E1')} y el plan cambia.",
                 mit="Segundo proveedor y stock de seguridad; priorizar productos de menor consumo (productos 1 y 2) si el suministro cae.",
                 alerta=f"Materia prima < {g(rb('MP')['lo'])} u"),
            dict(id="R2", nombre="Recorte severo de mano de obra", esc="E2", prob=2,
                 evid=f"Bajo {um('E2')} h no existe plan factible; con −10 % (E3): {dz('E3')}.",
                 mit="Horas extra o turno adicional; subcontratar el producto 4 (mayor consumo de materia prima) o negociar reducir el total.",
                 alerta=f"Horas disponibles < {g(int(F(E['E2']['umbral']) * F(105, 100)))}"),
            dict(id="R3", nombre="Mayor demanda mínima del producto 4", esc="E5", prob=3,
                 evid=f"Cada unidad exigida del producto 4 resta {y('D4')} {zu} (válido hasta {g(rb('D4')['hi'])} u). A 500: {dz('E5')}.",
                 mit="Negociar el cupo con clientes o fijar un precio premium al excedente del producto 4.",
                 alerta=f"Solicitud de producto 4 > {g(int(rb('D4')['hi'] * F(95, 100)))} u"),
            dict(id="R4", nombre="Caída del precio del producto 4", esc="E6", prob=3,
                 evid=f"El plan no cambia (c₄ ≤ {g(r.rangos_costo[3]['hi'])}), pero el ingreso baja {dz('E6')} con −25 %.",
                 mit="Contratos de precio a plazo; diversificar hacia productos 2 y 3.", alerta="Precio del producto 4 < 7"),
            dict(id="R5", nombre="Estrés combinado", esc="E8", prob=2,
                 evid=f"Materia prima 4 300 + total 1 000 + mínimo P4 450: ingreso {z('E8')} ({dz('E8')}).",
                 mit="Reserva de contingencia y plan de contingencia por escenarios revisado trimestralmente.", alerta="Dos alertas activas a la vez"),
            dict(id="R6", nombre="Error o desactualización de datos", esc=None, prob=2, imp=4,
                 evid="Los coeficientes técnicos y precios vienen del enunciado (trazabilidad en §Trazabilidad).",
                 mit="Versionado con hash de datos, doble verificación (a mano + solver) y revisión por pares.", alerta="Hash de datos distinto al versionado"),
        ]
    elif key == "mochila":
        rbb = resolver_binario(m)
        rb2 = resolver_binario(E["E2"]["modelo"])
        rb6 = resolver_binario(E["E6"]["modelo"])
        rb7 = resolver_binario(E["E7"]["modelo"])
        rb8 = resolver_binario(E["E8"]["modelo"])
        gap_pct = lambda e_id, rbe: g(float((E[e_id]["res"].z - rbe.z) / rbe.z * 100), 1) if rbe.z else "0"
        R = [
            dict(id="R1", nombre="Menos capacidad de carga", esc="E2", prob=3,
                 evid=f"La relajación lineal cae de {g(r.z)} a {z('E2')} ({dz('E2')}); el óptimo entero real baja de {g(rbb.z)} a {g(rb2.z)} "
                      f"(brecha del {gap_pct('E2', rb2)} %) al reducir la capacidad de 60 a 50 lb.",
                 mit="Redistribuir peso entre más porteadores o dejar equipo de menor prioridad (artículos 1 y 4).",
                 alerta="Capacidad de carga confirmada < 55 lb"),
            dict(id="R2", nombre="El artículo 3 pesa más de lo previsto", esc="E6", prob=3,
                 evid=f"Si el artículo 3 pesa 45 lb en vez de 35, la selección entera óptima cambia de (2, 3) a ({', '.join(str(j+1) for j in range(5) if rb6.x[j]==1)}) "
                      f"y el valor exacto baja de {g(rbb.z)} a {g(rb6.z)}.",
                 mit="Pesar cada artículo antes de salir; llevar una báscula portátil.", alerta="Peso real del artículo 3 > 40 lb"),
            dict(id="R3", nombre="Brecha entre la relajación lineal y el entero", esc=None, prob=3, imp=3,
                 evid=f"En la base la relajación indica {g(r.z)} puntos pero el óptimo entero real es {g(rbb.z)} "
                      f"(brecha {g(float((r.z-rbb.z)/rbb.z*100),1)} %); en el escenario de menor capacidad (E2) la brecha llega a {gap_pct('E2', rb2)} %.",
                 mit="Reportar siempre el óptimo entero (enumeración exacta), nunca la relajación fraccionaria, como recomendación final.",
                 alerta="Brecha relajación-entero > 15 % en algún escenario"),
            dict(id="R4", nombre="Equipo de seguridad obligatorio reduce el valor", esc="E8", prob=2,
                 evid=f"Exigir el artículo 1 baja el óptimo entero de {g(rbb.z)} a {g(rb8.z)} "
                      f"({g(float((rb8.z-rbb.z)/rbb.z*100),1)} %).",
                 mit="Buscar un artículo de seguridad más liviano; evaluar si en verdad es indispensable.",
                 alerta="Peso del equipo obligatorio > 45 lb"),
            dict(id="R5", nombre="Estrés combinado de capacidad y peso", esc="E7", prob=2,
                 evid=f"Con 55 lb de capacidad y el artículo 2 a 30 lb, el óptimo entero cae a {g(rb7.z)}.",
                 mit="Plan de contingencia: definir de antemano qué artículo se sacrifica primero.", alerta="Dos condiciones adversas a la vez"),
            dict(id="R6", nombre="Error en el peso o valor de un artículo", esc=None, prob=2, imp=4,
                 evid="Los pesos y valores vienen del enunciado; un error los desplaza y puede cambiar la selección óptima completa.",
                 mit="Verificar peso y valor de cada artículo antes de empacar; versionar los datos.",
                 alerta="Desvío > 10 % en peso o valor de algún artículo"),
        ]
    elif key == "farmatodo":
        def rango(c):
            b = rb(c)
            return f"[{'0' if b['lo'] is None else g(b['lo'])}, {'sin tope' if b['hi'] is None else g(b['hi'])}]"
        R = [
            dict(id="R1", nombre="Refuerzo de la mañana", esc="E1", prob=4,
                 evid=f"Cada cajero más exigido en 07:00–10:59 cuesta {y('P2')} (válido en {rango('P2')}). De 20 a 24: {dz('E1')}.",
                 mit="Banco de suplentes y turnos de tiempo parcial en la mañana.", alerta="Demanda 07:00–11:00 > 22"),
            dict(id="R2", nombre="Refuerzo de la tarde", esc="E2", prob=4,
                 evid=f"Cada cajero más en 15:00–18:59 cuesta {y('P4')} (válido en {rango('P4')}). De 20 a 24: {dz('E2')}.",
                 mit="Turnos escalonados y horas extra en la tarde.", alerta="Demanda 15:00–19:00 > 22"),
            dict(id="R3", nombre="Evento nocturno especial", esc="E5", prob=2,
                 evid=f"Un evento que sube la demanda de 19:00–22:59 de 10 a 28 eleva el personal a {z('E5')} ({dz('E5')}).",
                 mit="Contratar personal temporal para eventos anunciados con antelación.", alerta="Demanda 19:00–23:00 > 22"),
            dict(id="R4", nombre="Recargo de trasnocho", esc="E7", prob=3,
                 evid=f"Con +50 % en los turnos de 03:00 y 23:00 el costo total sube a {z('E7')} ({dz('E7')}).",
                 mit="Presupuesto de horas nocturnas y rotación equitativa del trasnocho.", alerta="Recargo nocturno > 25 %"),
            dict(id="R5", nombre="Techo de personal insuficiente", esc="E8", prob=2,
                 evid=f"Con un techo de 44 cajeros no existe programación factible; el mínimo real es {um('E8')}.",
                 mit=f"Aprobar una plantilla ≥ {um('E8')} más una reserva de suplentes.", alerta=f"Plantilla aprobada < {um('E8')}"),
            dict(id="R6", nombre="Trasnocho más exigente", esc="E6", prob=2,
                 evid=f"Cada cajero más en 23:00–02:59 cuesta {y('P6')} (válido en {rango('P6')}). De 5 a 10: {dz('E6')}.",
                 mit="Rotación de trasnocho y bonificación por turno nocturno.", alerta="Demanda 23:00–03:00 > 8"),
            dict(id="R7", nombre="Demanda mal estimada", esc=None, prob=3, imp=4,
                 evid="Los mínimos por periodo vienen del enunciado; si la demanda real difiere, el plan pierde validez fuera de su rango.",
                 mit="Medir la demanda real por periodo y recalcular con el programa; versionar los datos.",
                 alerta="Desvío de demanda real > 10 % en un periodo"),
        ]
    elif key == "plasticos":
        R = [
            dict(id="R1", nombre="Crece el pedido del detallista 1", esc="E1", prob=3,
                 evid=f"Detallista 1 pide 100 cajas más (con 100 más de oferta en fábrica 1): el costo sube a {z('E1')} ({dz('E1')}).",
                 mit="Cláusula de flexibilidad de pedido con la fábrica y el detallista; inventario de seguridad.",
                 alerta="Pedido del detallista 1 > 1 050 cajas"),
            dict(id="R2", nombre="Crece el pedido del detallista 3", esc="E2", prob=3,
                 evid=f"Detallista 3 pide 200 cajas más (con 200 más en fábrica 2): el costo sube a {z('E2')} ({dz('E2')}).",
                 mit="Ampliar el turno de producción en fábrica 2 o subcontratar el excedente.", alerta="Pedido del detallista 3 > 600 cajas"),
            dict(id="R3", nombre="Alza del flete Fábrica 1 → Detallista 3", esc="E4", prob=3,
                 evid=f"Con el flete de 11 a 13 USD/caja el costo total sube a {z('E4')} ({dz('E4')}), sin cambiar las rutas usadas.",
                 mit="Contrato de flete a plazo fijo con el transportista de esa ruta.", alerta="Flete F1→D3 > 12,5 USD/caja"),
            dict(id="R4", nombre="Techo de costo insuficiente", esc="E8", prob=2,
                 evid=f"Un techo de 27 000 USD es infactible; el costo mínimo real es {um('E8')} USD.",
                 mit=f"Aprobar un presupuesto ≥ {um('E8')} USD más una reserva de contingencia.", alerta=f"Presupuesto aprobado < {um('E8')} USD"),
            dict(id="R5", nombre="Estrés combinado", esc="E7", prob=2,
                 evid=f"Alza de flete F1→D3 junto con el crecimiento del pedido del detallista 3: costo {z('E7')} ({dz('E7')}).",
                 mit="Reserva de contingencia y renegociación conjunta de fletes y pedidos.", alerta="Dos condiciones adversas a la vez"),
            dict(id="R6", nombre="Degeneración: rutas alternativas", esc=None, prob=3, imp=3,
                 evid="La oferta total (2 200 cajas) es exactamente igual a la demanda total (2 200 cajas): el sistema es degenerado y puede "
                      "haber varias combinaciones de rutas con el mismo costo mínimo.",
                 mit="Elegir entre las rutas alternativas según criterios logísticos (distancia, confiabilidad del transportista).",
                 alerta="Un nuevo cálculo entrega una distribución de rutas distinta con el mismo costo"),
            dict(id="R7", nombre="Error en costos o cantidades", esc=None, prob=2, imp=4,
                 evid="Los costos de flete y las cantidades de oferta/demanda vienen del enunciado; un error los desplaza.",
                 mit="Verificar cantidades y tarifas con cada fábrica y detallista; versionar los datos.",
                 alerta="Desvío > 10 % en algún costo o cantidad"),
        ]
    for x in R:
        if x["esc"]:
            x["imp"], x["imp_txt"] = impacto(A, E[x["esc"]])
        else:
            x["imp_txt"] = "No cuantificado (juicio del equipo)"
        x["exp"] = x["prob"] * x["imp"]
        x["nivel"] = "Crítico" if x["exp"] >= 15 else "Alto" if x["exp"] >= 10 else "Moderado" if x["exp"] >= 5 else "Bajo"
    return sorted(R, key=lambda x: -x["exp"])


def s_riesgos(A, k):
    R = lista_riesgos(A)
    A["riesgos"] = R
    mapa = G.mapa_riesgo([(x["id"], x["prob"], x["imp"]) for x in R])
    tipo = {"Crítico": "mal", "Alto": "aviso", "Moderado": "neutro", "Bajo": "ok"}
    filas = [[f"<b>{x['id']}</b>", x["nombre"], x["esc"] or "—", str(x["prob"]), f"{x['imp']}<br><span class='sub'>{x['imp_txt']}</span>",
              f"<b>{x['exp']}</b> " + chip(x["nivel"], tipo[x["nivel"]]), x["evid"], x["mit"], x["alerta"]] for x in R]
    t = tabla(["ID", "Riesgo", "Escenario", "P", "I", "Exposición", "Evidencia cuantitativa", "Estrategia de mitigación", "Indicador de alerta"],
              filas, "Matriz de riesgos y estrategias de mitigación (ordenada por exposición)", "ancha",
              nota="Impacto (1–5) calculado a partir del escenario: infactible = 5; pérdida del objetivo ≥ 10 % = 4; ≥ 5 % = 3; ≥ 2 % = 2; menor = 1. "
                   "La probabilidad (1–5) es un supuesto de juicio del equipo y es editable en <span class='mono'>informe.py</span>. Exposición = P × I.")
    leyenda = ("<div class='leyenda'><span><i class='n0'></i>Bajo (&lt; 5)</span><span><i class='n1'></i>Moderado (5–9)</span>"
               "<span><i class='n2'></i>Alto (10–14)</span><span><i class='n3'></i>Crítico (≥ 15)</span></div>")
    return f"""<section id="{k}-riesgos"><h2><span>6</span>Matriz de riesgos</h2>
<figure class="chartbox mapaf"><figcaption><b>Gráfico.</b> Mapa de calor de riesgos (probabilidad × impacto)</figcaption>{mapa}{leyenda}</figure>{t}</section>"""


def s_reco(A, k):
    m, r = A["m"], A["base"]
    zu = m.unidad_z
    obj = obj_de(m)
    E = {e["cfg"]["id"]: e for e in A["esc"]}
    R = A.get("riesgos") or lista_riesgos(A)
    top = [x for x in R if x["nivel"] in ("Crítico", "Alto")]
    ok = [e for e in A["esc"] if e["res"].estado == "optimo"]
    adv = lambda e: adverso(m, e["res"].z, r.z)
    peor = max(ok, key=adv)
    infact = "; ".join("«" + e["cfg"]["nombre"].lower() + "»" for e in A["esc"] if e["res"].estado != "optimo")
    cierre_inf = f"y ante {infact} el problema pierde factibilidad. " if infact else ""
    riesgos_li = (f"<li><b>Riesgos prioritarios:</b> {', '.join(x['id'] + ' ' + x['nombre'].lower() for x in top[:3])}. "
                  f"Vigilar sus indicadores de alerta (§6) y mantener listas las mitigaciones.</li>") if top else ""
    reserva_li = ""
    if adv(peor) > 0:
        reserva_li = (f"<li><b>Reserva.</b> El peor desvío adverso factible evaluado ({peor['cfg']['id']} · {peor['cfg']['nombre'].lower()}) "
                      f"empeora el {obj} en {g(adv(peor))} {zu} ({g(float(adv(peor) / abs(r.z) * 100), 1)} %); dimensionar la contingencia en ese orden.</li>")

    if m.clave == "mochila":
        rbb = resolver_binario(m)
        sel = ", ".join(str(j + 1) for j in range(len(m.vars)) if rbb.x[j] == 1) or "ninguno"
        icap = idx(m, "CAP")
        peso_usado = sum(m.restr[icap].a[j] * rbb.x[j] for j in range(len(m.vars)))
        gap = r.z - rbb.z
        pts = [f"<li><b>Decisión (óptimo entero, no la relajación).</b> Llevar los artículos <b>{sel}</b>: valor exacto "
               f"<b>{g(rbb.z)} {zu}</b>, peso {g(peso_usado)} de {g(m.restr[icap].b)} lb. La relajación lineal muestra {g(r.z)} "
               f"(brecha de {g(gap)}, {g(float(gap / rbb.z * 100), 1)} %): es una cota, no un plan realizable.</li>",
               f"<li><b>Recurso crítico: capacidad de carga.</b> {traduccion(r, icap)}</li>",
               riesgos_li]
        arg = (f"«La mejor selección posible es llevar los artículos {sel}, con un valor de {g(rbb.z)} puntos y {g(peso_usado)} de las "
               f"{g(m.restr[icap].b)} libras disponibles. La relajación lineal sugiere {g(r.z)}, pero esa cifra no es alcanzable porque los "
               f"artículos no se pueden fraccionar; el valor real y verificado por enumeración exacta es {g(rbb.z)}. Recomendamos llevar "
               f"exactamente esa combinación y confirmar el peso real de cada artículo antes de salir.»")
    elif m.clave == "farmatodo":
        crit_i = [i for i in range(len(m.restr)) if r.precios_sombra[i] != 0]
        pts = [f"<li><b>Decisión.</b> Programar {g(r.z)} cajeros: {', '.join(f'{sub(v)} = {g(x)}' for v, x in zip(m.vars, r.x))}.</li>"]
        for i in crit_i:
            pts.append(f"<li><b>Periodo crítico: {m.restr[i].nombre.lower()}.</b> {traduccion(r, i)}</li>")
        libres = [i for i, rs in enumerate(m.restr) if rs.tipo == ">=" and r.holgura[i] > 0]
        for i in libres[:2]:
            pts.append(f"<li><b>Excedente en {m.restr[i].nombre.lower()}.</b> {traduccion(r, i)}</li>")
        pts += [riesgos_li, reserva_li]
        bl = ", ".join(m.restr[i].nombre.replace("Periodo ", "") for i in crit_i)
        arg = (f"«Farmatodo necesita como mínimo {g(r.z)} cajeros. Mandan los periodos {bl}: cada cajero más exigido allí obliga a contratar "
               f"uno más, mientras la demanda se mantenga en su rango de validez; en los demás periodos hay excedente de cobertura. "
               f"{cierre_inf.capitalize()}Recomendamos fijar la plantilla en al menos {g(r.z)}, mantener una reserva de suplentes y vigilar "
               f"los indicadores de alerta.»")
    elif m.clave == "plasticos":
        rutas = [(m.vars_desc[j], r.x[j]) for j in range(len(m.vars)) if r.x[j] > 0]
        plan_txt = "; ".join(f"{n}: {g(x)} cajas" for n, x in rutas)
        crit_i = max(range(len(m.restr)), key=lambda i: abs(r.precios_sombra[i]))
        pts = [f"<li><b>Decisión.</b> Enviar {plan_txt}, con un costo total de <b>{g(r.z)} {zu}</b>.</li>",
               f"<li><b>Restricción más valiosa: {m.restr[crit_i].nombre.lower()}.</b> {traduccion(r, crit_i)}</li>",
               "<li><b>Sistema balanceado.</b> La oferta total (2 200 cajas) es exactamente igual a la demanda total (2 200 cajas): toda "
               "ampliación de un pedido exige ampliar también el inventario en la misma cantidad, o el modelo se vuelve infactible.</li>"]
        if bloque_alternos(A):
            pts.append("<li><b>Rutas alternativas.</b> Existe otra combinación de rutas con el mismo costo mínimo (ver «Óptimos alternativos» "
                       "en §2); puede elegirse por criterios logísticos.</li>")
        pts += [riesgos_li, reserva_li]
        arg = (f"«El plan de envío óptimo cuesta {g(r.z)} USD: {plan_txt}. La restricción que más pesa es {m.restr[crit_i].nombre.lower()}, "
               f"con un valor marginal de {g(abs(r.precios_sombra[crit_i]))} USD por caja. Como la oferta y la demanda están exactamente "
               f"balanceadas, cualquier cambio en un pedido debe acompañarse de un cambio equivalente en el inventario. {cierre_inf.capitalize()}"
               f"Recomendamos fijar este plan, negociar fletes en las rutas críticas y vigilar los indicadores de alerta.»")
    else:  # winco
        plan = ", ".join(f"{sub(v)} = {g(x)}" for v, x in zip(m.vars, r.x))
        pts = [f"<li><b>Decisión.</b> Adoptar el plan base ({plan}) con {obj} óptimo de <b>{g(r.z)} {zu}</b>, verificado con dos métodos independientes.</li>"]
        for i, rs in enumerate(m.restr):
            y = r.precios_sombra[i]
            if y != 0 and rs.tipo == "<=":
                pts.append(f"<li><b>Recurso crítico: {rs.nombre.lower()}.</b> {traduccion(r, i)} Es donde conviene asegurar suministro o negociar capacidad adicional.</li>")
            elif rs.tipo == "<=" and r.holgura[i] > 0:
                pts.append(f"<li><b>No invertir en {rs.nombre.lower()}.</b> {traduccion(r, i)}</li>")
        for i, rs in enumerate(m.restr):
            if rs.tipo in (">=", "=") and r.precios_sombra[i] != 0:
                pts.append(f"<li><b>Compromiso «{rs.nombre.lower()}».</b> {traduccion(r, i)}</li>")
        pts += [riesgos_li, reserva_li]
        rc = next(i for i, rs in enumerate(m.restr) if rs.tipo == "<=" and r.precios_sombra[i] != 0)
        rs_c = m.restr[rc]
        verbo = "aporta" if r.precios_sombra[rc] > 0 else "resta"
        arg = (f"«El plan óptimo produce ({', '.join(g(x) for x in r.x)}) con un {obj} de {g(r.z)} {zu}. El recurso que manda es la "
               f"{rs_c.nombre.lower()}: cada unidad {verbo} {g(abs(r.precios_sombra[rc]))} {zu}, "
               f"pero solo dentro de {g(r.rangos_b[rc]['lo'])}–{g(r.rangos_b[rc]['hi'])} unidades. Fuera de ese margen el plan debe recalcularse, "
               f"{cierre_inf}Recomendamos asegurar ese recurso, mantener una reserva y vigilar los indicadores de alerta.»")
    return f"""<section id="{k}-recomendacion"><h2><span>7</span>Recomendación final</h2>
<ul class="reco">{''.join(pts)}</ul><h3>Argumento breve para el público institucional</h3><blockquote>{arg}</blockquote></section>"""


def s_resumen(A, k):
    m, r, cfg = A["m"], A["base"], A["cfg"]
    zu = m.unidad_z
    obj = obj_de(m)
    ok, det = A["ver"]
    nfact = sum(1 for e in A["esc"] if e["res"].estado == "optimo")
    cand = [i for i, rs in enumerate(m.restr) if not getattr(rs, "auxiliar", False)]
    crit = max(cand, key=lambda i: abs(r.precios_sombra[i]))
    etq_crit = "Periodo más valioso" if m.clave == "farmatodo" else "Restricción más valiosa" if m.clave == "plasticos" else "Recurso más valioso"
    kpi = (f"<div class='kpis'><div class='kpi'><small>{obj.capitalize()} óptimo</small><b>{g(r.z)}</b><span>{zu}</span></div>"
           f"<div class='kpi'><small>{etq_crit}</small><b class='sm'>{m.restr[crit].nombre}</b><span>precio sombra {g(r.precios_sombra[crit])} {zu}/u</span></div>"
           f"<div class='kpi'><small>Escenarios factibles</small><b>{nfact} / {len(A['esc'])}</b><span>{len(A['esc']) - nfact} pierden factibilidad</span></div>"
           f"<div class='kpi'><small>Verificación con solver</small><b>{'✓' if ok else '✕'}</b><span>SciPy · HiGHS</span></div></div>")
    guia = [("1", "Portada y objetivo", "Título, integrantes, objetivo del estudio", "#top"),
            ("2", "Contexto y datos", "Datos de entrada y trazabilidad", f"#{k}-modelo"),
            ("3", "Modelo", "Función objetivo y restricciones", f"#{k}-modelo"),
            ("4", "Solución base", "Plan óptimo y uso de recursos", f"#{k}-base"),
            ("5", "Evidencia del solver", "Tablas Simplex y verificación HiGHS", f"#{k}-base"),
            ("6", "Escenarios (≥ 3)", "Definición y tabla comparativa costo / tiempo / servicio", f"#{k}-escenarios"),
            ("7", "Impacto de escenarios", "Gráfico de variación y factibilidad", f"#{k}-escenarios"),
            ("8", "Precios sombra", "Interpretación para decisores no técnicos", f"#{k}-sombra"),
            ("9", "Sensibilidad", "Rangos de optimalidad y de factibilidad + curvas", f"#{k}-sensibilidad"),
            ("10", "Matriz de riesgos", "Mapa de calor y mitigación", f"#{k}-riesgos"),
            ("11", "Recomendación final", "Decisión, reserva y argumento breve", f"#{k}-recomendacion"),
            ("12", "Referencias APA 7", "Con DOI o URL", "#referencias")]
    t_g = tabla(["Diap.", "Contenido", "Qué incluir", "Ir a"], [[a, b, c, f"<a href='{d}'>ver</a>"] for a, b, c, d in guia],
                "Guía sugerida de diapositivas (12 en total; el enunciado exige entre 10 y 14)", numerada=False)
    return f"""<section id="{k}-resumen"><h2><span>0</span>Ejercicio {cfg["ejercicio"]} · {m.nombre}</h2>
<p class="lead">Objetivo: {cfg['objetivo_txt']}.</p>{kpi}<details><summary>Guía de diapositivas</summary>{t_g}</details></section>"""


def s_traza(modelos_A):
    hoy = datetime.date.today().isoformat()
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        import scipy, numpy
        libs = f"SciPy {scipy.__version__} · NumPy {numpy.__version__}"
    except ImportError:
        libs = "SciPy no disponible"
    hashes = " · ".join(f"{A['m'].nombre}: <span class='mono'>{A['hash']}</span>" for A in modelos_A)
    ver = tabla(["Versión", "Fecha", "Cambio", "Responsable"], [
        ["v0.1", "2026-08", f"Winco resuelto a mano en el Taller 1 ({FUENTE_DOCX})", "Equipo"],
        ["v0.2", "2026-09", "Simplex de Dos Fases programado en Python y verificado tabla por tabla", "Equipo"],
        ["v1.0", hoy, "Estandarización del modelo, solución base y verificación con SciPy/HiGHS", "Equipo"],
        ["v1.1", hoy, "Escenarios paramétricos, precios sombra, rangos de sensibilidad y curvas", "Equipo"],
        ["v1.2", hoy, "Matriz de riesgos, recomendación y trazabilidad; generación automática del informe", "Equipo"],
        ["v2.0", hoy, "Corrección de enunciado: se reemplazan Renault/Biblioteca/Dual por Mochila, Farmatodo y Plásticos "
                      "(ejercicios correctos del Taller, grupo 603N)", "Equipo"],
    ], "Registro de versiones")
    rep = tabla(["Elemento", "Detalle"], [
        ["Generado", ahora], ["Hash de datos (SHA-256, 12 caracteres)", hashes],
        ["Entorno", f"Python {platform.python_version()} · {libs}"],
        ["Aritmética", "Exacta (fracciones): sin errores de redondeo en tablas, precios sombra ni rangos"],
        ["Reproducir", "Ejecutar <span class='mono'>Ejecutar informe.bat</span> o <span class='mono'>python informe.py</span> en la carpeta del Taller 2"],
        ["Verificación", "Cada escenario se contrasta con HiGHS (estado, valor óptimo y precios sombra)"],
    ], "Reproducibilidad", numerada=False)
    refs = "".join(f"<p class='ref'>{r}</p>" for r in REFERENCIAS)
    return f"""<section id="trazabilidad"><h2><span>8</span>Trazabilidad y versiones</h2><div class="grid2"><div>{ver}</div><div>{rep}</div></div></section>
<section id="referencias"><h2><span>9</span>Referencias (APA 7)</h2>{refs}
<p class="muted">Los enlaces de Google Drive provienen del enunciado de la actividad; los DOI corresponden a la documentación del solver empleado. Los cinco enlaces respondieron correctamente (HTTP 200/302) el 2026-09-21.</p></section>"""


# ------------------------------------------------------------------ página
CSS = r"""
:root{--bg:#ffffff;--surface:#ffffff;--ink:#141414;--ink2:#55555a;--muted:#8b8b90;--line:#ebebee;--axis:#cfcfd4;--accent:#2a78d6;--wash:rgba(42,120,214,.07);--adv:#e34948;--crit:#c22f2f;--ok:#006300;--warn:#8a5a00;--hi:rgba(42,120,214,.13);--n0:#dbe9fb;--n1:#9dc2f1;--n2:#3987e5;--n3:#184f95;--celda-on:#fff;--btn-bg:#141414;--btn-fg:#fff;--shadow:0 6px 20px rgba(0,0,0,.18);--radius:10px}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1b1c1f;--surface:#222327;--ink:#d6d6d2;--ink2:#a4a4a2;--muted:#797a7d;--line:#2d2e33;--axis:#3c3d43;--accent:#6b9ee0;--wash:rgba(107,158,224,.10);--adv:#d47272;--crit:#e58a8a;--ok:#78b978;--warn:#d9ac5a;--hi:rgba(107,158,224,.18);--n0:#2a2f37;--n1:#34506f;--n2:#3f6fa8;--n3:#4a82c4;--celda-on:#eee;--btn-bg:#e6e6e2;--btn-fg:#1b1c1f;--shadow:0 6px 20px rgba(0,0,0,.45)}}
:root[data-theme="dark"]{--bg:#1b1c1f;--surface:#222327;--ink:#d6d6d2;--ink2:#a4a4a2;--muted:#797a7d;--line:#2d2e33;--axis:#3c3d43;--accent:#6b9ee0;--wash:rgba(107,158,224,.10);--adv:#d47272;--crit:#e58a8a;--ok:#78b978;--warn:#d9ac5a;--hi:rgba(107,158,224,.18);--n0:#2a2f37;--n1:#34506f;--n2:#3f6fa8;--n3:#4a82c4;--celda-on:#eee;--btn-bg:#e6e6e2;--btn-fg:#1b1c1f;--shadow:0 6px 20px rgba(0,0,0,.45)}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:64px}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
main{max-width:1180px;margin:0 auto;padding:0 20px 80px}
header.top{max-width:1180px;margin:0 auto;padding:44px 20px 20px}
.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
h1{font-size:34px;line-height:1.15;margin:8px 0 6px;font-weight:650;letter-spacing:-.02em}
.sub-h{color:var(--ink2);margin:0 0 18px}
.team{display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--ink2);font-size:13px;margin:0 0 4px}
.controls{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--line)}
.controls .in{max-width:1180px;margin:0 auto;padding:10px 20px;display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:3px;background:var(--surface)}
.seg button{border:0;background:none;color:var(--ink2);font:inherit;font-size:13px;padding:5px 14px;border-radius:999px;cursor:pointer}
.seg button.on{background:var(--ink);color:var(--bg)}
.tog{font:inherit;font-size:13px;color:var(--ink2);background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:5px 12px;cursor:pointer}
.tog:hover{border-color:var(--axis)}.tog.on{color:var(--ink);border-color:var(--accent)}
.spacer{flex:1}
nav.sec{display:flex;gap:2px 4px;flex-wrap:wrap;margin:18px 0 8px;font-size:13px}
nav.sec a{color:var(--ink2);padding:4px 10px;border-radius:6px}nav.sec a:hover{background:var(--wash);text-decoration:none;color:var(--ink)}
section{margin-top:56px}
h2{font-size:22px;margin:0 0 14px;font-weight:650;letter-spacing:-.01em;display:flex;align-items:center;gap:12px}
h2 span{font-size:12px;font-weight:600;color:var(--muted);border:1px solid var(--line);border-radius:999px;min-width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center}
h3{font-size:15px;margin:28px 0 10px;font-weight:650;color:var(--ink)}
.lead{color:var(--ink2);font-size:16px;max-width:820px;margin:0 0 18px}.muted{color:var(--muted);font-size:13px;margin:6px 0 14px;max-width:820px}
.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 28px}.grid2.charts{gap:24px 28px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
figure{margin:0 0 22px;position:relative}
figcaption{font-size:13px;color:var(--ink2);margin:0 0 8px;padding-right:64px}figcaption b{color:var(--ink)}figcaption .sub{display:block;color:var(--muted);font-size:12px}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:last-child td,tbody tr:last-child th{border-bottom:0}
thead th{font-weight:600;color:var(--muted);font-size:11.5px;letter-spacing:.03em;text-transform:none;background:transparent;white-space:normal;border-bottom:1px solid var(--axis)}
td{color:var(--ink)}td.num{text-align:right}
.simplex table{text-align:right}.simplex th,.simplex td{text-align:right;padding:7px 12px;white-space:nowrap}
.simplex thead th:first-child,.simplex th.fila{text-align:left}
.simplex th.fila{font-weight:600;color:var(--ink);background:transparent}
.simplex th.ent{color:var(--accent);box-shadow:inset 0 -2px 0 var(--accent)}
.simplex th.sal,.simplex tr:has(th.sal) td{background:var(--wash)}
.simplex td.piv{background:var(--hi);font-weight:700;box-shadow:inset 0 0 0 1.5px var(--accent);border-radius:4px}
.simplex td.z,.simplex th.z{border-top:1px solid var(--axis);font-weight:600}
.simplex td.razon{color:var(--muted)}.simplex td.razon.min{color:var(--accent);font-weight:700}
.decision{display:flex;flex-wrap:wrap;gap:6px 8px;margin-top:8px;font-size:12.5px}
.dec{border:1px solid var(--line);border-radius:999px;padding:3px 11px;color:var(--ink2);background:var(--surface)}.dec b{color:var(--ink)}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:12px;padding:1px 9px;border-radius:999px;border:1px solid var(--line);white-space:nowrap;background:var(--surface)}
.chip i{font-style:normal;font-weight:700}.chip.ok{color:var(--ok)}.chip.mal{color:var(--crit);border-color:color-mix(in srgb,var(--crit) 40%,var(--line))}
.chip.aviso{color:var(--warn)}.chip.neutro{color:var(--ink2)}
.copiar{position:absolute;top:-4px;right:0;font:inherit;font-size:12px;color:var(--muted);background:none;border:1px solid var(--line);border-radius:6px;padding:2px 9px;cursor:pointer}
.copiar:hover{color:var(--ink);border-color:var(--axis)}
.math{font-family:ui-serif,Georgia,"Cambria Math",serif;font-size:19px;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px 20px;margin:0 0 14px;overflow-x:auto}
.math.sm{font-size:15px}.math .u{font-family:system-ui;font-size:12px;color:var(--muted)}
.mono{font-family:ui-monospace,Consolas,monospace;font-size:12.5px}
sub{font-size:.72em;line-height:0}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:0 0 26px}
@media(max-width:900px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;display:flex;flex-direction:column;gap:2px}
.kpi small{color:var(--muted);font-size:12px}.kpi b{font-size:28px;font-weight:650;letter-spacing:-.02em;line-height:1.2}.kpi b.sm{font-size:17px;line-height:1.35;padding:5px 0}
.kpi span{color:var(--ink2);font-size:12.5px}
details{border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);margin:0 0 10px}
summary{cursor:pointer;padding:11px 16px;font-size:14px;color:var(--ink);list-style:none;display:flex;align-items:center;gap:8px}
summary::before{content:"›";color:var(--muted);transition:transform .15s;display:inline-block}details[open]>summary::before{transform:rotate(90deg)}
details>*:not(summary){margin-left:16px;margin-right:16px}details>summary+*{margin-top:4px}details[open]{padding-bottom:6px}
.chartbox{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px 16px 10px}
.chartbox figcaption{padding-right:0}
.chartbox details{border:0;margin:6px 0 0;background:none}.chartbox details summary{padding:6px 0;font-size:12.5px;color:var(--muted)}
.chart{width:100%;height:auto;display:block;font-family:inherit}
.chart .grid{stroke:var(--line)}.chart .axis{stroke:var(--axis)}.chart .tick{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.chart .eje{fill:var(--ink2);font-size:12px}.chart .nota{fill:var(--muted);font-size:11px}.chart .etq{fill:var(--ink2);font-size:12px}.chart .idt{font-weight:700;fill:var(--ink)}
.chart .val{fill:var(--ink);font-size:11.5px;font-variant-numeric:tabular-nums}
.chart .serie{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.chart .quiebre{fill:var(--surface);stroke:var(--accent);stroke-width:2}
.chart .base{fill:var(--surface);stroke:var(--accent);stroke-width:2.5}
.chart .banda{fill:var(--wash)}.chart .hatch{stroke:var(--crit);stroke-width:1.2;opacity:.35}.chart .infz{opacity:1}
.chart .crit{fill:var(--crit);font-size:12px;font-weight:600}
.chart .hit{fill:transparent;cursor:crosshair}.chart .hit:hover{fill:var(--hi)}
.chart .fav{fill:var(--accent)}.chart .adv{fill:var(--adv)}.chart .hit-bar:hover{opacity:.8}
.chart.lin .tick{font-size:12.5px}.chart.lin .eje{font-size:13px}.chart.lin .nota{font-size:12px}.chart.lin .etq{font-size:13px}.chart.lin .crit{font-size:13px}
.chart .celda{fill:var(--ink2);font-size:10.5px}.chart .n2+.celda,.chart .n3+.celda{fill:var(--celda-on)}.chart .n0{fill:var(--n0)}.chart .n1{fill:var(--n1)}.chart .n2{fill:var(--n2)}.chart .n3{fill:var(--n3)}
.chart .pill{fill:var(--surface);stroke:var(--axis)}.chart .pilltxt{fill:var(--ink);font-size:11.5px;font-weight:700}
.rango{display:block;min-width:170px}.rango .seg{stroke:var(--accent);stroke-width:3;stroke-linecap:round}.rango .tope{stroke:var(--accent);stroke-width:2}
.rango .flecha{fill:none;stroke:var(--accent);stroke-width:2}.rango .base{fill:var(--surface);stroke:var(--ink);stroke-width:2}
.mapaf{max-width:640px}.leyenda{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--ink2);margin-top:6px}
.leyenda i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.leyenda .n0{background:var(--n0)}.leyenda .n1{background:var(--n1)}.leyenda .n2{background:var(--n2)}.leyenda .n3{background:var(--n3)}
td .sub{color:var(--muted);font-size:12px}.nota-t{font-size:12px;color:var(--muted);margin:6px 2px 0}
.reco{padding-left:18px;max-width:900px}.reco li{margin:0 0 10px;color:var(--ink2)}.reco b{color:var(--ink)}
blockquote{margin:0;padding:16px 22px;border-left:3px solid var(--accent);background:var(--wash);border-radius:0 var(--radius) var(--radius) 0;max-width:900px;color:var(--ink);font-size:15.5px}
.ref{margin:0 0 10px;padding-left:2em;text-indent:-2em;color:var(--ink2);font-size:14px;word-break:break-word}
.cmp td{white-space:nowrap}.interp td:last-child{min-width:320px}.ancha td,.ancha th{padding:8px 10px}
#tema{position:fixed;right:22px;bottom:22px;z-index:40;width:46px;height:46px;border-radius:50%;border:0;background:var(--btn-bg);color:var(--btn-fg);
display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:var(--shadow);transition:transform .15s}
#tema:hover{transform:scale(1.07)}#tema:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
#tema .ico-sol{display:none}:root[data-theme="dark"] #tema .ico-sol{display:block}:root[data-theme="dark"] #tema .ico-luna{display:none}
#tip{position:fixed;pointer-events:none;z-index:50;background:var(--ink);color:var(--bg);font-size:12px;padding:5px 9px;border-radius:6px;display:none;max-width:320px}
body:not(.frac) .f{display:none}body.frac .d{display:none}
.modelo{display:none}.modelo.on{display:block}
.ej-sel{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin:8px 0 0}
.ej-card{text-align:left;font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;cursor:pointer;display:flex;flex-direction:column;gap:3px;transition:border-color .15s,box-shadow .15s}
.ej-card:hover{border-color:var(--axis)}.ej-card.on{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.ej-card b{font-size:20px;font-weight:650;letter-spacing:-.01em}.ej-n{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.ej-card.on .ej-n{color:var(--accent)}.ej-d{color:var(--ink2);font-size:14px}.ej-r{color:var(--muted);font-size:12.5px;margin-top:6px}
footer{max-width:1180px;margin:0 auto;padding:30px 20px;color:var(--muted);font-size:12px;border-top:1px solid var(--line)}
@media print{.controls,nav.sec,.copiar,#tema{display:none!important}body{background:#fff}details{border:0}details>*{display:block}
.scroll{overflow:visible}section{break-inside:avoid-page}figure{break-inside:avoid}}
"""

JS = r"""
(function(){
const $=(s,c=document)=>c.querySelector(s),$$=(s,c=document)=>[...c.querySelectorAll(s)];
const st={get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
const KEYS=$$('.modelo').map(m=>m.id.slice(2));
function modelo(k){$$('.modelo').forEach(m=>m.classList.toggle('on',m.id==='m-'+k));$$('.seg button,.ej-card').forEach(b=>b.classList.toggle('on',b.dataset.k===k));st.set('modelo',k);}
function irA(hash){const h=(hash||'').replace('#','');if(!h)return false;
 const ej=h.match(/^ejercicio-(\d+)$/);if(ej){const b=$('.ej-card[data-ej="'+ej[1]+'"]');if(b){modelo(b.dataset.k);return true}}
 const el=document.getElementById(h);const m=el&&el.closest('.modelo');if(m){modelo(m.id.slice(2));el.scrollIntoView();return true}return false}
$$('.seg button,.ej-card').forEach(b=>b.onclick=()=>{modelo(b.dataset.k);history.replaceState(null,'','#ejercicio-'+b.dataset.ej);
 const m=$('#m-'+b.dataset.k);const y=(b.classList.contains('ej-card')?m.getBoundingClientRect().top+scrollY-64:0);scrollTo({top:Math.max(0,y)})});
modelo(st.get('modelo')&&KEYS.includes(st.get('modelo'))?st.get('modelo'):KEYS[0]);
irA(location.hash);addEventListener('hashchange',()=>irA(location.hash));
const fr=$('#frac');fr.onclick=()=>{document.body.classList.toggle('frac');fr.classList.toggle('on');st.set('frac',document.body.classList.contains('frac')?'1':'0')};
if(st.get('frac')==='1'){document.body.classList.add('frac');fr.classList.add('on')}
const R=document.documentElement,sys=()=>matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';
R.dataset.theme=st.get('tema')||sys();
$('#tema').onclick=()=>{R.dataset.theme=R.dataset.theme==='dark'?'light':'dark';st.set('tema',R.dataset.theme)};
$('#imprimir').onclick=()=>{$$('details').forEach(d=>d.open=true);print()};
$$('.copiar').forEach(b=>b.onclick=()=>{const t=$('table',b.parentElement);if(!t)return;
 const txt=$$('tr',t).map(r=>$$('th,td',r).map(c=>c.innerText.replace(/\s+/g,' ').trim()).join('\t')).join('\n');
 const ok=()=>{b.textContent='Copiado';setTimeout(()=>b.textContent='Copiar',1200)};
 (navigator.clipboard?navigator.clipboard.writeText(txt).then(ok):Promise.reject()).catch(()=>{const a=document.createElement('textarea');a.value=txt;document.body.appendChild(a);a.select();try{document.execCommand('copy');ok()}catch(e){}a.remove()})});
const tip=$('#tip');document.addEventListener('mousemove',e=>{const t=e.target.closest&&e.target.closest('[data-tip]');
 if(t){tip.textContent=t.dataset.tip;tip.style.display='block';tip.style.left=Math.min(e.clientX+14,innerWidth-330)+'px';tip.style.top=(e.clientY+16)+'px'}else tip.style.display='none'});
})();
"""


def pagina(modelos_A):
    botones = "".join(f"<button type='button' data-k='{A['m'].clave}' data-ej='{A['cfg']['ejercicio']}'>{A['cfg']['etiqueta']}</button>" for A in modelos_A)
    tarjetas = "".join(
        f"<button type='button' class='ej-card' data-k='{A['m'].clave}' data-ej='{A['cfg']['ejercicio']}'>"
        f"<span class='ej-n'>Ejercicio {A['cfg']['ejercicio']}</span><b>{A['m'].nombre}</b>"
        f"<span class='ej-d'>{A['cfg']['objetivo_txt'][:1].upper() + A['cfg']['objetivo_txt'][1:]}</span>"
        f"<span class='ej-r'>Óptimo Z* = {g(A['base'].z)} {A['m'].unidad_z} · {len(A['esc'])} escenarios</span></button>"
        for A in modelos_A)
    cuerpos = []
    for A in modelos_A:
        k = A["m"].clave
        _contador["t"] = 0
        _contador["f"] = 0
        _contador["g"] = 0
        partes = [s_resumen(A, k), s_modelo(A, k), s_base(A, k), s_escenarios(A, k), s_sombra(A, k), s_sensibilidad(A, k), s_riesgos(A, k)]
        partes.append(s_reco(A, k))
        nav = (f"<nav class='sec'><a href='#{k}-resumen'>Resumen</a><a href='#{k}-modelo'>Modelo</a><a href='#{k}-base'>Solución base</a>"
               f"<a href='#{k}-escenarios'>Escenarios</a><a href='#{k}-sombra'>Precios sombra</a><a href='#{k}-sensibilidad'>Sensibilidad</a>"
               f"<a href='#{k}-riesgos'>Riesgos</a><a href='#{k}-recomendacion'>Recomendación</a><a href='#trazabilidad'>Trazabilidad</a>"
               f"<a href='#referencias'>Referencias</a></nav>")
        cuerpos.append(f"<div class='modelo' id='m-{k}'>{nav}{''.join(partes)}</div>")
    traza = s_traza(modelos_A)
    equipo = "".join(f"<span>{n}</span>" for n in INTEGRANTES)
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Óptimo con Evidencias</title><style>{CSS}</style></head><body>
<header class="top" id="top"><div class="eyebrow">R1-A2-S6 · Investigación de Operaciones I · Taller 2</div>
<h1>Óptimo con Evidencias</h1><p class="sub-h">Optimización lineal, escenarios, dualidad y sensibilidad</p>
<div class="team">{equipo}</div>
<div class="team">Facultad de Ingeniería · Ingeniería de Sistemas y Computación · Universidad de Cundinamarca, Extensión Chía · {datetime.date.today().strftime('%m/%Y')}</div></header>
<div class="controls"><div class="in"><div class="seg">{botones}</div><span class="spacer"></span>
<button class="tog" id="frac" type="button" title="Alternar entre decimales y fracciones exactas">Fracciones</button>
<button class="tog" id="imprimir" type="button">Imprimir / PDF</button></div></div>
<main><div class="ej-sel" role="tablist" aria-label="Seleccionar ejercicio">{tarjetas}</div>{''.join(cuerpos)}{traza}</main>
<footer>Informe generado automáticamente por informe.py · Simplex de Dos Fases con aritmética exacta · verificado con SciPy/HiGHS.</footer>
<button id="tema" type="button" aria-label="Cambiar entre tema claro y oscuro" title="Cambiar tema">
<svg class="ico-luna" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
<svg class="ico-sol" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></button>
<div id="tip"></div><script>{JS}</script></body></html>"""


def main():
    modelos_A = [analizar(m, CONFIG[m.clave]) for m in MODELOS]
    html = pagina(modelos_A)
    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write(html)
    n_ver = sum(1 for A in modelos_A for e in A["esc"] if e["verif"][0])
    n_tot = sum(len(A["esc"]) for A in modelos_A)
    print(f"Informe generado: {SALIDA}")
    print(f"Escenarios verificados con HiGHS: {n_ver}/{n_tot}")
    if "--no-abrir" not in sys.argv:
        webbrowser.open("file:///" + SALIDA.replace("\\", "/"))


if __name__ == "__main__":
    main()

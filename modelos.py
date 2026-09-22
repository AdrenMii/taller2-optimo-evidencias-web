# -*- coding: utf-8 -*-
"""Datos estandarizados de los modelos, escenarios y barridos paramétricos.
Ejercicios del enunciado correcto (TALLER MODELOS DE PROG LINEAL.pdf, grupo 603N):
1) Winco, 2) Mochila del excursionista, 3) Farmatodo (cajeros), 4) Fabricante de plásticos."""
from fractions import Fraction as F
from motor import Modelo, Restriccion as R

FUENTE_PDF = "TALLER MODELOS DE PROG LINEAL.pdf"
FUENTE_DOCX = "Informe_Taller1_Modelos_de_Programacion_Lineal-Grupo7.docx"

# ---------------------------------------------------------------- Ejercicio 1: Winco (maximización de ingreso)
WINCO = Modelo(
    "winco", "Winco", "max",
    ["x1", "x2", "x3", "x4"], [4, 6, 7, 8],
    [
        R("MP", "Materia prima", [2, 3, 4, 7], "<=", 4600, "unidades de materia prima"),
        R("MO", "Mano de obra", [3, 4, 5, 6], "<=", 5000, "horas"),
        R("TOT", "Producción total exacta", [1, 1, 1, 1], "=", 950, "unidades"),
        R("D4", "Demanda mínima producto 4", [0, 0, 0, 1], ">=", 400, "unidades"),
    ],
    unidad_z="USD",
    vars_desc=["Unidades producto 1", "Unidades producto 2", "Unidades producto 3", "Unidades producto 4"],
)
WINCO.obj = "ingreso"

# ---------------------------------------------------------------- Ejercicio 2: Mochila del excursionista (0/1)
PESO = [52, 23, 35, 15, 7]
VALOR = [100, 60, 70, 15, 15]
MOCHILA = Modelo(
    "mochila", "Mochila del excursionista", "max",
    [f"x{i+1}" for i in range(5)], VALOR,
    [R("CAP", "Capacidad de carga", PESO, "<=", 60, "libras")] +
    [R(f"U{i+1}", f"Límite del artículo {i+1} (0/1)", [1 if j == i else 0 for j in range(5)], "<=", 1, "unidad", auxiliar=True)
     for i in range(5)],
    unidad_z="puntos de valor",
    vars_desc=[f"Se lleva el artículo {i+1} ({PESO[i]} lb, valor {VALOR[i]})" for i in range(5)],
)
MOCHILA.obj = "valor"
MOCHILA.binario = True   # variables 0/1: además del Simplex (relajación lineal) se resuelve exacto por enumeración

# ---------------------------------------------------------------- Ejercicio 3: Farmatodo (mínimo de cajeros)
PERIODOS = ["03:00–06:59", "07:00–10:59", "11:00–14:59", "15:00–18:59", "19:00–22:59", "23:00–02:59"]
INICIOS_F = ["03:00", "07:00", "11:00", "15:00", "19:00", "23:00"]
DEM_FAR = [7, 20, 14, 20, 10, 5]


def _cobertura_farmatodo():
    rs = []
    for j in range(6):
        a = [0] * 6
        a[j] += 1          # cajero que inicia en este periodo
        a[j - 1] += 1      # cajero que inició en el periodo anterior (cíclico: el 1 sigue al 6)
        rs.append(R(f"P{j+1}", f"Periodo {PERIODOS[j]}", a, ">=", DEM_FAR[j], "cajeros"))
    return rs


FARMATODO = Modelo(
    "farmatodo", "Farmatodo", "min", [f"x{i}" for i in range(1, 7)], [1] * 6, _cobertura_farmatodo(),
    unidad_z="cajero(s)", vars_desc=[f"Cajeros que inician turno a las {h}" for h in INICIOS_F],
)
FARMATODO.obj = "personal"

# ---------------------------------------------------------------- Ejercicio 4: Fabricante de plásticos (transporte)
COSTOS_PL = [14, 13, 11, 13, 13, 12]   # x11,x12,x13,x21,x22,x23
PLASTICOS = Modelo(
    "plasticos", "Fabricante de plásticos", "min",
    ["x11", "x12", "x13", "x21", "x22", "x23"], COSTOS_PL,
    [
        R("F1", "Oferta fábrica 1", [1, 1, 1, 0, 0, 0], "<=", 1200, "cajas"),
        R("F2", "Oferta fábrica 2", [0, 0, 0, 1, 1, 1], "<=", 1000, "cajas"),
        R("D1", "Demanda detallista 1", [1, 0, 0, 1, 0, 0], ">=", 1000, "cajas"),
        R("D2", "Demanda detallista 2", [0, 1, 0, 0, 1, 0], ">=", 700, "cajas"),
        R("D3", "Demanda detallista 3", [0, 0, 1, 0, 0, 1], ">=", 500, "cajas"),
    ],
    unidad_z="USD",
    vars_desc=["Cajas de Fábrica 1 a Detallista 1", "Cajas de Fábrica 1 a Detallista 2", "Cajas de Fábrica 1 a Detallista 3",
               "Cajas de Fábrica 2 a Detallista 1", "Cajas de Fábrica 2 a Detallista 2", "Cajas de Fábrica 2 a Detallista 3"],
)
PLASTICOS.obj = "costo"

MODELOS = [WINCO, MOCHILA, FARMATODO, PLASTICOS]   # orden por número de ejercicio del taller

CONFIG = {
    "winco": dict(
        etiqueta="Ejercicio 1 · Winco", ejercicio=1,
        objetivo_txt="maximizar el ingreso por ventas de 950 unidades",
        contexto=("Winco vende 4 productos; dispone de 4 600 unidades de materia prima y 5 000 horas de mano de obra, "
                  "debe producir exactamente 950 unidades y al menos 400 del producto 4."),
        fuente=f"{FUENTE_PDF}, ejercicio 1, Tabla 1 · {FUENTE_DOCX}, Figura 1",
        tabla_datos=dict(cols=["Producto", "Precio (USD)", "Materia prima (u)", "Mano de obra (h)"],
                         filas=[["Producto 1", 4, 2, 3], ["Producto 2", 6, 3, 4], ["Producto 3", 7, 4, 5], ["Producto 4", 8, 7, 6]]),
        escenarios=[
            dict(id="E1", nombre="Recorte de materia prima", desc="Materia prima 4 600 → 4 140 (−10 %)",
                 var=dict(b={"MP": 4140}), top=True, umbral=None),
            dict(id="E2", nombre="Recorte severo de mano de obra", desc="Mano de obra 5 000 → 4 000 (−20 %)",
                 var=dict(b={"MO": 4000}), top=True, umbral="MO"),
            dict(id="E3", nombre="Menos horas de mano de obra", desc="Mano de obra 5 000 → 4 500 (−10 %)",
                 var=dict(b={"MO": 4500}), top=False, umbral=None),
            dict(id="E4", nombre="Pedido mayor", desc="Producción total 950 → 1 000",
                 var=dict(b={"TOT": 1000}), top=True, umbral=None),
            dict(id="E5", nombre="Mayor demanda del producto 4", desc="Mínimo producto 4: 400 → 500",
                 var=dict(b={"D4": 500}), top=False, umbral=None),
            dict(id="E6", nombre="Caída del precio del producto 4", desc="Precio producto 4: 8 → 6 (−25 %)",
                 var=dict(c={"x4": 6}), top=False, umbral=None),
            dict(id="E7", nombre="Mejora del precio del producto 1", desc="Precio producto 1: 4 → 6 (+50 %)",
                 var=dict(c={"x1": 6}), top=False, umbral=None),
            dict(id="E8", nombre="Estrés combinado", desc="Materia prima 4 300 + total 1 000 + mínimo producto 4 = 450",
                 var=dict(b={"MP": 4300, "TOT": 1000, "D4": 450}), top=True, umbral=None),
        ],
        barridos=[
            dict(tipo="b", clave="MP", extra=[4450, 4850], desde=4100, hasta=5100, paso=50,
                 titulo="Ingreso máximo vs. materia prima disponible", x="Materia prima disponible (u)"),
            dict(tipo="b", clave="TOT", extra=[850, 1000], desde=800, hasta=1100, paso=10,
                 titulo="Ingreso máximo vs. producción total exigida", x="Unidades a producir"),
            dict(tipo="b", clave="D4", extra=[275, F(875, 2)], desde=200, hasta=600, paso=10,
                 titulo="Ingreso máximo vs. mínimo del producto 4", x="Unidades mínimas del producto 4"),
            dict(tipo="c", clave="x4", extra=[10], desde=4, hasta=12, paso=0.5,
                 titulo="Ingreso máximo vs. precio del producto 4", x="Precio producto 4 (USD)"),
        ],
    ),
    "mochila": dict(
        etiqueta="Ejercicio 2 · Mochila", ejercicio=2,
        objetivo_txt="maximizar el valor total transportado sin exceder 60 libras de carga",
        contexto=("Un excursionista tiene 5 artículos (pesos 52, 23, 35, 15 y 7 libras; valores 100, 60, 70, 15 y 15) y puede "
                  "cargar como máximo 60 libras. xⱼ = 1 si se lleva el artículo j, 0 si no. Es un problema de selección 0/1 "
                  "(mochila binaria), no continuo: se resuelve la relajación lineal con Simplex y, además, el óptimo entero "
                  "exacto por enumeración (solo 2⁵ = 32 combinaciones)."),
        fuente=f"{FUENTE_PDF}, ejercicio 2",
        tabla_datos=dict(cols=["Artículo", "Peso (lb)", "Valor"],
                         filas=[[f"Artículo {i+1}", PESO[i], VALOR[i]] for i in range(5)]),
        binario=dict(pesos=PESO, valores=VALOR, capacidad=60),
        escenarios=[
            dict(id="E1", nombre="Más capacidad de carga", desc="Capacidad 60 → 70 lb (+17 %)",
                 var=dict(b={"CAP": 70}), top=True, umbral=None),
            dict(id="E2", nombre="Menos capacidad de carga", desc="Capacidad 60 → 50 lb (−17 %)",
                 var=dict(b={"CAP": 50}), top=True, umbral=None),
            dict(id="E3", nombre="Capacidad muy reducida", desc="Capacidad 60 → 30 lb (−50 %)",
                 var=dict(b={"CAP": 30}), top=False, umbral=None),
            dict(id="E4", nombre="Artículo 4 más valioso", desc="Valor del artículo 4: 15 → 40",
                 var=dict(c={"x4": 40}), top=False, umbral=None),
            dict(id="E5", nombre="Artículo 1 más liviano", desc="Peso del artículo 1: 52 → 40 lb",
                 var=dict(a={("CAP", "x1"): 40}), top=False, umbral=None),
            dict(id="E6", nombre="Artículo 3 más pesado", desc="Peso del artículo 3: 35 → 45 lb",
                 var=dict(a={("CAP", "x3"): 45}), top=True, umbral=None),
            dict(id="E7", nombre="Estrés combinado", desc="Capacidad 55 lb + peso del artículo 2: 23 → 30 lb",
                 var=dict(b={"CAP": 55}, a={("CAP", "x2"): 30}), top=False, umbral=None),
            dict(id="E8", nombre="Equipo de seguridad obligatorio", desc="Se exige llevar el artículo 1 (x1 = 1)",
                 var=dict(agregar=[R("OBL", "Artículo 1 obligatorio", [1, 0, 0, 0, 0], ">=", 1, "unidad")]),
                 top=True, umbral=None),
        ],
        barridos=[
            dict(tipo="b", clave="CAP", extra=[58, 60], desde=20, hasta=80, paso=5,
                 titulo="Valor de la relajación lineal vs. capacidad de carga", x="Capacidad de carga (lb)"),
            dict(tipo="c", clave="x4", extra=[15], desde=0, hasta=60, paso=5,
                 titulo="Valor de la relajación lineal vs. valor del artículo 4", x="Valor del artículo 4"),
        ],
    ),
    "farmatodo": dict(
        etiqueta="Ejercicio 3 · Farmatodo", ejercicio=3,
        objetivo_txt="minimizar el número total de cajeros que cubren las 24 horas",
        contexto=("Una tienda Farmatodo abre las 24 horas y exige un mínimo de cajeros por periodo de 4 horas (7, 20, 14, 20, "
                  "10 y 5, en periodos de 3 a 7, 7 a 11, 11 a 15, 15 a 19, 19 a 23 y 23 a 3). Cada cajero trabaja 8 horas "
                  "consecutivas empezando al inicio de un periodo; el periodo 1 sigue inmediatamente al periodo 6 (ciclo de 24 h)."),
        fuente=f"{FUENTE_PDF}, ejercicio 3",
        tabla_datos=dict(cols=["Periodo", "Horas del día", "Mínimo de cajeros"],
                         filas=[[f"Periodo {j+1}", PERIODOS[j], DEM_FAR[j]] for j in range(6)]),
        escenarios=[
            dict(id="E1", nombre="Refuerzo de la mañana", desc="Periodo 2 (07:00–10:59): 20 → 24",
                 var=dict(b={"P2": 24}), top=True, umbral=None),
            dict(id="E2", nombre="Refuerzo de la tarde", desc="Periodo 4 (15:00–18:59): 20 → 24",
                 var=dict(b={"P4": 24}), top=True, umbral=None),
            dict(id="E3", nombre="Madrugada sin efecto", desc="Periodo 1 (03:00–06:59): 7 → 12",
                 var=dict(b={"P1": 12}), top=False, umbral=None),
            dict(id="E4", nombre="Mediodía sin presión", desc="Periodo 3 (11:00–14:59): 14 → 18 (sin efecto: lo absorbe el excedente de otros periodos)",
                 var=dict(b={"P3": 18}), top=False, umbral=None),
            dict(id="E5", nombre="Noche mucho más exigente", desc="Periodo 5 (19:00–22:59): 10 → 28 (evento especial)",
                 var=dict(b={"P5": 28}), top=True, umbral=None),
            dict(id="E6", nombre="Trasnocho más exigente", desc="Periodo 6 (23:00–02:59): 5 → 10",
                 var=dict(b={"P6": 10}), top=True, umbral=None),
            dict(id="E7", nombre="Recargo de trasnocho", desc="Costo de los turnos de 03:00 y 23:00: 1 → 1,5 (+50 %)",
                 var=dict(c={"x1": F(3, 2), "x6": F(3, 2)}), top=True, umbral=None),
            dict(id="E8", nombre="Techo de personal", desc="Plantilla total ≤ 44 cajeros (uno menos que el óptimo)",
                 var=dict(agregar=[R("PL", "Techo de personal", [1] * 6, "<=", 44, "cajeros")]),
                 top=True, umbral="PL"),
        ],
        barridos=[
            dict(tipo="b", clave="P4", extra=[20, 24], desde=14, hasta=30, paso=1,
                 titulo="Personal mínimo vs. demanda del periodo 4 (15:00–18:59)", x="Demanda mínima periodo 4"),
            dict(tipo="b", clave="P2", extra=[20, 24], desde=14, hasta=30, paso=1,
                 titulo="Personal mínimo vs. demanda del periodo 2 (07:00–10:59)", x="Demanda mínima periodo 2"),
            dict(tipo="b", clave="P6", extra=[5, 10], desde=3, hasta=16, paso=F(1, 2),
                 titulo="Personal mínimo vs. demanda del periodo 6 (23:00–02:59)", x="Demanda mínima periodo 6"),
            dict(tipo="c", clave="x1", extra=[1], desde=F(1, 2), hasta=2, paso=F(1, 10),
                 titulo="Personal mínimo vs. costo del turno de las 03:00", x="Costo unitario del turno de 03:00"),
        ],
    ),
    "plasticos": dict(
        etiqueta="Ejercicio 4 · Plásticos", ejercicio=4,
        objetivo_txt="minimizar el costo total de envío que satisface toda la demanda",
        contexto=("Un fabricante de plásticos tiene 1 200 cajas en la fábrica 1 y 1 000 en la fábrica 2 (oferta total 2 200), "
                  "y tres detallistas piden 1 000, 700 y 500 cajas (demanda total 2 200): es un problema de transporte "
                  "balanceado (oferta = demanda), por lo que toda restricción se cumple en el límite y el sistema es degenerado "
                  "(hay una restricción redundante: 5 ecuaciones para 2 + 3 − 1 = 4 grados de libertad)."),
        fuente=f"{FUENTE_PDF}, ejercicio 4",
        tabla_datos=dict(cols=["Ruta", "Costo unitario (USD/caja)"],
                         filas=[["Fábrica 1 → Detallista 1", 14], ["Fábrica 1 → Detallista 2", 13], ["Fábrica 1 → Detallista 3", 11],
                               ["Fábrica 2 → Detallista 1", 13], ["Fábrica 2 → Detallista 2", 13], ["Fábrica 2 → Detallista 3", 12]]),
        escenarios=[
            dict(id="E1", nombre="Crece el pedido del detallista 1", desc="Detallista 1: 1 000 → 1 100 y fábrica 1: 1 200 → 1 300 cajas",
                 var=dict(b={"D1": 1100, "F1": 1300}), top=True, umbral=None),
            dict(id="E2", nombre="Crece el pedido del detallista 3", desc="Detallista 3: 500 → 700 y fábrica 2: 1 000 → 1 200 cajas",
                 var=dict(b={"D3": 700, "F2": 1200}), top=True, umbral=None),
            dict(id="E3", nombre="Recomposición del inventario", desc="Fábrica 1: 1 200 → 1 000 y fábrica 2: 1 000 → 1 200 cajas",
                 var=dict(b={"F1": 1000, "F2": 1200}), top=False, umbral=None),
            dict(id="E4", nombre="Alza del flete Fábrica 1 → Detallista 3", desc="Costo de la ruta F1→D3: 11 → 13 USD/caja",
                 var=dict(c={"x13": 13}), top=True, umbral=None),
            dict(id="E5", nombre="Baja del flete Fábrica 2 → Detallista 1", desc="Costo de la ruta F2→D1: 13 → 10 USD/caja",
                 var=dict(c={"x21": 10}), top=False, umbral=None),
            dict(id="E6", nombre="Baja del flete Fábrica 1 → Detallista 1", desc="Costo de la ruta F1→D1: 14 → 12 USD/caja",
                 var=dict(c={"x11": 12}), top=False, umbral=None),
            dict(id="E7", nombre="Estrés combinado", desc="Flete F1→D3 a 13 + detallista 3 a 700 (fábrica 2 a 1 200)",
                 var=dict(c={"x13": 13}, b={"D3": 700, "F2": 1200}), top=True, umbral=None),
            dict(id="E8", nombre="Techo de costo", desc="Costo total ≤ 27 000 USD (por debajo del óptimo)",
                 var=dict(agregar=[R("PRE", "Techo de costo", COSTOS_PL, "<=", 27000, "USD")]),
                 top=True, umbral="PRE"),
        ],
        barridos=[
            dict(tipo="c", clave="x13", extra=[11], desde=8, hasta=16, paso=F(1, 2),
                 titulo="Costo mínimo vs. flete Fábrica 1 → Detallista 3", x="Costo de la ruta F1→D3 (USD/caja)"),
            dict(tipo="c", clave="x21", extra=[13], desde=6, hasta=16, paso=F(1, 2),
                 titulo="Costo mínimo vs. flete Fábrica 2 → Detallista 1", x="Costo de la ruta F2→D1 (USD/caja)"),
            dict(tipo="c", clave="x11", extra=[14], desde=10, hasta=18, paso=F(1, 2),
                 titulo="Costo mínimo vs. flete Fábrica 1 → Detallista 1", x="Costo de la ruta F1→D1 (USD/caja)"),
        ],
    ),
}

REFERENCIAS = [
    "Carro Paz, R. (2014). <i>Investigación de operaciones en administración</i> (1.ª ed.). Universidad Nacional de Mar del Plata. "
    "<a href='https://nulan.mdp.edu.ar/id/eprint/2180/1/carro.2014.pdf'>https://nulan.mdp.edu.ar/id/eprint/2180/1/carro.2014.pdf</a>",
    "Hillier, F. S., &amp; Lieberman, G. J. (2010). <i>Introducción a la investigación de operaciones</i> (9.ª ed.). McGraw-Hill. "
    "<a href='https://drive.google.com/file/d/0B9eK8K2tCH-CY2tZRXlVWEtMTU0/view?resourcekey=0-Y2VSl8G-YsrcnYqfvXRb0g'>"
    "https://drive.google.com/file/d/0B9eK8K2tCH-CY2tZRXlVWEtMTU0/view</a>",
    "Huangfu, Q., &amp; Hall, J. A. J. (2018). Parallelizing the dual revised simplex method. <i>Mathematical Programming Computation, 10</i>(1), 119–142. "
    "<a href='https://doi.org/10.1007/s12532-017-0130-5'>https://doi.org/10.1007/s12532-017-0130-5</a>",
    "Taha, H. A. (2017). <i>Investigación de operaciones</i>. "
    "<a href='https://drive.google.com/file/d/1rkLbdsF7xdbPYHtVkuexKd51WhmQKyA8/view'>https://drive.google.com/file/d/1rkLbdsF7xdbPYHtVkuexKd51WhmQKyA8/view</a>",
    "Virtanen, P., Gommers, R., Oliphant, T. E., Haberland, M., Reddy, T., Cournapeau, D., … SciPy 1.0 Contributors. (2020). "
    "SciPy 1.0: Fundamental algorithms for scientific computing in Python. <i>Nature Methods, 17</i>(3), 261–272. "
    "<a href='https://doi.org/10.1038/s41592-019-0686-2'>https://doi.org/10.1038/s41592-019-0686-2</a>",
]

INTEGRANTES = [
    "Kevin Alexander Contreras", "Wilder Stiven Ortiz", "David Estiven Sanchez", "Duvan Lozano Romero",
    "Henry Alejandro Ortega", "Cristhian Stiven Aza (Tarde)", "Luis German de la Rosa (Tarde)",
]

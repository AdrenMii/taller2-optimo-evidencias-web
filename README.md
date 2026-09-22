# Óptimo con Evidencias · Taller 2

Informe interactivo de optimización lineal (R1-A2-S6): modelo, solución base (Simplex de Dos Fases, todas las tablas),
escenarios, precios sombra, sensibilidad, matriz de riesgos y recomendación, para los 4 ejercicios del taller:
1) Winco, 2) Mochila del excursionista, 3) Farmatodo, 4) Fabricante de plásticos.

Página: https://adrenmii.github.io/taller2-optimo-evidencias-web/

## Ejecutar
```
pip install scipy numpy
python informe.py
```
Genera `index.html` (informe completo) y lo abre en el navegador (`--no-abrir` para solo generarlo). En Windows: `Ejecutar informe.bat`.

## Archivos
- `motor.py`: Simplex de Dos Fases con fracciones exactas, precios sombra, rangos de sensibilidad y enumeración entera 0/1.
- `modelos.py`: datos de los modelos, escenarios y barridos (aquí se editan los parámetros).
- `graficos.py`: gráficos SVG.
- `informe.py`: genera `index.html` (probabilidades de riesgo editables en `lista_riesgos`).

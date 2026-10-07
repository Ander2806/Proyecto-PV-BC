```markdown
# Optimización de Ubicación y Dimensionamiento de PV y BC en Redes IEEE 33/69 Barras

Este proyecto implementa algoritmos metaheurísticos (PSO, WOA, híbridos y GA) para la optimización de la ubicación y el dimensionamiento de **Paneles Fotovoltaicos (PV)** y **Bancos de Condensadores (BC)** en redes de distribución IEEE de 33 y 69 barras, considerando perfiles horarios de demanda, generación solar y precios de energía.

---

## Estructura del Proyecto

- **core/**  
  Núcleo del sistema  
  - `parameters.py` → Clases de parámetros (SystemParameters, OptimizationParameters)  
  - `data_loader.py` → Carga de datos de red desde CSV/JSON  
  - `system_cache.py` → Precálculo de estructuras estáticas (BIBC, demandas horarias)  
  - `power_flow.py` → Flujo de potencia Backward/Forward Sweep optimizado  
  - `objective.py` → Función objetivo con penalizaciones  
  - `lsi.py` → Análisis de sensibilidad LSI para candidatos  

- **algorithms/**  
  Algoritmos de optimización  
  - `_utils.py` → Funciones compartidas (bounds, seed population)  
  - `pso.py` → Particle Swarm Optimization  
  - `woa.py` → Whale Optimization Algorithm  
  - `woa_pso.py` → Híbrido WOA → PSO  
  - `pso_woa.py` → Híbrido PSO → WOA  
  - `ga.py` → Algoritmo Genético (SBX + mutación polinomial)  

- **analysis/**  
  Análisis posterior a la optimización  
  - `loaders.py` → Carga de resultados y estado de BC desde Excel  
  - `economics.py` → Evaluación económica (payback, VPN, ROI)  
  - `emissions.py` → Análisis de emisiones contaminantes  
  - `plots/` → Funciones de visualización  
    - `demand_profiles.py`  
    - `voltage_profiles.py`  
    - `losses.py`  
    - `capacitor_status.py`  

- **utils/**  
  Utilidades generales  
  - `io_excel.py` → Guardado de resultados en Excel (13 hojas)  
  - `summary.py` → Resúmenes y costos detallados  

- **data/**  
  Datos de entrada  
  - `networks/` → Redes eléctricas  
    - `ieee33/` (line_data.csv, bus_data.csv, bus_categories.json)  
    - `ieee69/` (line_data.csv, bus_data.csv, bus_categories.json)  
  - `profiles/` → Perfiles horarios (demand_curves.csv, energy_prices.csv)  
  - `parameters/` → optimization_parameters.json  

- **outputs/**  
  Resultados generados (se crea automáticamente)  
  - `optimizacion/<Algoritmo>/<Sistema>/` → Archivos de ejecución y resumen  
  - `analisis/` → Gráficos y tablas de análisis  

- **notebooks/**  
  Cuadernos de trabajo  
  - `00_analisis_inicial.ipynb` → Figuras iniciales (demanda, tarifas, PV)  
  - `01_optimizacion.ipynb` → Ejecutar optimizaciones  
  - `02_analisis_solucion_especifica.ipynb` → Análisis de la mejor solución  
  - `03_comparacion_algoritmos.ipynb` → Comparación entre algoritmos  

- **requirements.txt** → Dependencias de Python  
- **README.md** → Este documento  

---

## Nombres internos y de visualización

- **Internamente** (archivos, carpetas, claves de diccionarios) se usan los nombres **sin guion**: `PSOWOA` y `WOAPSO`.  
- **En pantalla** (gráficos, leyendas, tablas) se muestran como `PSO-WOA` y `WOA-PSO`.  

Esto se logra mediante el diccionario `ETIQUETAS_DISPLAY` en los notebooks de comparación.

---

## Instalación

1. Clonar o descargar el proyecto.  
2. Crear un entorno virtual (recomendado):  
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/macOS
   venv\Scripts\activate         # Windows
   ```  
3. Instalar dependencias:  
   ```bash
   pip install -r requirements.txt
   ```

---

## Uso mediante Notebooks

- Abrir Jupyter desde la raíz del proyecto:  
  ```bash
  jupyter notebook
  ```  
- Ejecutar los notebooks en `notebooks/` en el orden deseado:  
  1. `00_analisis_inicial.ipynb` – genera figuras de demanda, tarifas y curva PV.  
  2. `01_optimizacion.ipynb` – configura y ejecuta la optimización. Allí se selecciona el algoritmo y sistema.  
  3. `02_analisis_solucion_especifica.ipynb` – analiza en detalle la mejor solución de un algoritmo.  
  4. `03_comparacion_algoritmos.ipynb` – compara todos los algoritmos entre sí.  

---

## Resultados generados

- **Optimización**  
  Cada ejecución genera un archivo Excel con 13 hojas: demanda, voltajes, pérdidas, costos, estado de BC, resumen, etc.  

- **Análisis de una solución**  
  Gráficos de voltajes, pérdidas, estado de BC y tablas de evaluación económica y emisiones.  

- **Comparación de algoritmos**  
  Boxplots de función objetivo y tiempo, frecuencias de ubicaciones, curvas de convergencia y rankings.  

---

## Requisitos

Ver `requirements.txt` para la lista completa de dependencias.
```
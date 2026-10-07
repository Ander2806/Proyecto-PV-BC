import numpy as np
import pandas as pd
import os
from core.parameters import SystemParameters
from core.data_loader import SystemData
from core.system_cache import SystemCache
from core.power_flow import power_flow_hourly_optimized

def cargar_estado_bc_desde_excel(ruta_archivo, bc_barras_activas=None):
    """
    Carga el estado de los BC desde la hoja 'Estado_BC_Horario' de un archivo Excel.
    Las columnas deben ser de la forma 'BC_Barra_XX' donde XX es el número de barra.
    Retorna un diccionario {barra: array_estado_24h}.
    Si no se encuentran columnas con ese patrón, se asignan secuencialmente a las
    barras activas proporcionadas en bc_barras_activas.
    """
    estado_bc = {}

    # Leer hoja específica
    try:
        df = pd.read_excel(ruta_archivo, sheet_name='Estado_BC_Horario')
    except Exception as e:
        print(f"⚠ No se pudo leer 'Estado_BC_Horario': {e}")
        return estado_bc

    # Intentar parsear columnas 'BC_Barra_XX'
    columnas_parseadas = False
    for col in df.columns:
        if col == 'Hora':
            continue
        if 'BC_Barra' in col:
            try:
                barra = int(col.split('_')[-1])
                estado_bc[barra] = df[col].values.astype(int)
                columnas_parseadas = True
            except ValueError:
                print(f"Advertencia: no se pudo parsear barra de columna '{col}'")

    # Si no se parseó ninguna, asignar por orden a las barras activas
    if not columnas_parseadas and bc_barras_activas:
        print("No se encontraron columnas 'BC_Barra_XX'. Usando mapeo secuencial.")
        columnas_bc = [col for col in df.columns if col != 'Hora']
        for i, barra in enumerate(bc_barras_activas):
            if i < len(columnas_bc):
                estado_bc[barra] = df[columnas_bc[i]].values.astype(int)
            else:
                break

    return estado_bc


def cargar_y_calcular_resultados(
        capacidad_bc1, ubicacion_bc1, capacidad_bc2, ubicacion_bc2,
        capacidad_bc3, ubicacion_bc3, capacidad_bc4, ubicacion_bc4,
        capacidad_pv1, ubicacion_pv1, capacidad_pv2, ubicacion_pv2,
        capacidad_pv3, ubicacion_pv3, capacidad_pv4, ubicacion_pv4,
        ruta_excel_estado_bc, sistema='IEEE33'):
    """
    Carga los datos y ejecuta los flujos de potencia para 24 horas.
    Retorna un diccionario con todos los resultados.
    """
    sys_params = SystemParameters()
    system_data = SystemData(sistema)
    cache = SystemCache(sys_params, system_data)

    print("=" * 70)
    print(f"POST-PROCESAMIENTO - ANÁLISIS DE SOLUCIÓN - {sistema}")
    print("=" * 70)
    print(f"Número de barras: {system_data.nbus}")
    print(f"Número de líneas: {system_data.nline}")

    # Barras de BC activos
    bc_barras = [ubicacion_bc1, ubicacion_bc2, ubicacion_bc3, ubicacion_bc4]
    bc_caps = [capacidad_bc1, capacidad_bc2, capacidad_bc3, capacidad_bc4]
    bc_activos = [(barra, cap) for barra, cap in zip(bc_barras, bc_caps) if cap > 0]
    bc_barras_activas = [barra for barra, cap in bc_activos]

    # Cargar estado de BC
    print("\nCargando estado de BC desde Excel...")
    estado_bc_por_barra = cargar_estado_bc_desde_excel(ruta_excel_estado_bc, bc_barras_activas)
    if not estado_bc_por_barra:
        print("⚠ No se pudo cargar ningún estado de BC. Se asumirán todos apagados.")
    else:
        print(f"Estados de BC cargados para barras: {list(estado_bc_por_barra.keys())}")

    # Construir vector de solución (NC_max=4)
    NC_max = 4
    x_vector = np.zeros(NC_max * 4)

    # PV
    x_vector[0] = ubicacion_pv1
    x_vector[1] = ubicacion_pv2
    x_vector[2] = ubicacion_pv3
    x_vector[3] = ubicacion_pv4
    x_vector[4] = capacidad_pv1
    x_vector[5] = capacidad_pv2
    x_vector[6] = capacidad_pv3
    x_vector[7] = capacidad_pv4

    # BC
    x_vector[8] = ubicacion_bc1
    x_vector[9] = ubicacion_bc2
    x_vector[10] = ubicacion_bc3
    x_vector[11] = ubicacion_bc4
    x_vector[12] = capacidad_bc1
    x_vector[13] = capacidad_bc2
    x_vector[14] = capacidad_bc3
    x_vector[15] = capacidad_bc4

    print("\nConfiguración cargada:")
    print(f"  PV: Barras {[ubicacion_pv1, ubicacion_pv2, ubicacion_pv3, ubicacion_pv4]}")
    print(f"      Capacidades {[capacidad_pv1, capacidad_pv2, capacidad_pv3, capacidad_pv4]} kW")
    print(f"  BC: Barras {[ubicacion_bc1, ubicacion_bc2, ubicacion_bc3, ubicacion_bc4]}")
    print(f"      Capacidades {[capacidad_bc1, capacidad_bc2, capacidad_bc3, capacidad_bc4]} kVAR")

    # Ejecutar flujos de potencia
    print("\nEjecutando flujos de potencia horarios...")
    resultados_sin = []
    resultados_con = []

    for hora in range(24):
        # Sin compensación
        bc_dummy = np.zeros(NC_max)
        res_sin = power_flow_hourly_optimized(None, hora, bc_dummy, 0, cache,
                                              with_compensation=False, return_details=True)
        resultados_sin.append(res_sin)

        # Con compensación: construir bc_status usando el diccionario por barra
        bc_status = np.zeros(NC_max)
        for idx, (barra, cap) in enumerate(bc_activos):
            if barra in estado_bc_por_barra:
                bc_status[idx] = estado_bc_por_barra[barra][hora]
            else:
                bc_status[idx] = 0

        res_con = power_flow_hourly_optimized(x_vector, hora, bc_status, 0, cache,
                                              with_compensation=True, return_details=True)
        resultados_con.append(res_con)

    print("✓ Cálculos completados")

    # Preparar datos para las visualizaciones
    datos = {
        'system_data': system_data,
        'cache': cache,
        'resultados_sin': resultados_sin,
        'resultados_con': resultados_con,
        'estado_bc': estado_bc_por_barra,          # Diccionario {barra: array_estados}
        'bc_config': {
            'nombres': ['BC1', 'BC2', 'BC3', 'BC4'],
            'ubicaciones': [ubicacion_bc1, ubicacion_bc2, ubicacion_bc3, ubicacion_bc4],
            'capacidades': [capacidad_bc1, capacidad_bc2, capacidad_bc3, capacidad_bc4]
        },
        'pv_config': {
            'ubicaciones': [ubicacion_pv1, ubicacion_pv2, ubicacion_pv3, ubicacion_pv4],
            'capacidades': [capacidad_pv1, capacidad_pv2, capacidad_pv3, capacidad_pv4]
        }
    }
    return datos
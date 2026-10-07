import matplotlib.pyplot as plt
import numpy as np
import os

def plot_demand_stacked(datos_analisis, ruta_guardado=None):
    """
    Gráfico de demanda apilada por tipo y generación PV (un panel).
    """
    resultados_con = datos_analisis['resultados_con']
    horas = np.arange(24)

    dem_res = np.array([res['E_by_type']['residential'] for res in resultados_con])
    dem_com = np.array([res['E_by_type']['commercial'] for res in resultados_con])
    dem_ind = np.array([res['E_by_type']['industrial'] for res in resultados_con])
    gen_pv = np.array([res['Pt_DG_total'] for res in resultados_con])

    fig, ax = plt.subplots(figsize=(10, 5))
    ancho = 0.35
    despl = 0.2

    ax.bar(horas - despl, dem_res, ancho, label='Residential', color='blue', alpha=0.8)
    ax.bar(horas - despl, dem_com, ancho, bottom=dem_res, label='Commercial', color='green', alpha=0.8)
    ax.bar(horas - despl, dem_ind, ancho, bottom=dem_res + dem_com, label='Industrial', color='red', alpha=0.8)
    ax.bar(horas + despl, gen_pv, ancho, label='PV Generation', color='orange', alpha=0.8)

    ax.set_xlabel('Time (h)', fontsize=20)
    ax.set_ylabel('Power (kW)', fontsize=20)
    ax.legend(fontsize=16, loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    ax.tick_params(axis='both', labelsize=20)
    ax.set_xlim(-0.5, 23.5)
    ax.set_xticks(range(0, 24, 1))
    plt.tight_layout()

    if ruta_guardado:
        plt.savefig(ruta_guardado, dpi=600, bbox_inches='tight')
    plt.show()
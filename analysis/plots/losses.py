import matplotlib.pyplot as plt
import numpy as np

def plot_active_losses(datos_analisis, ruta_guardado=None):
    """
    Gráfico de barras comparando pérdidas activas sin y con compensación.
    """
    resultados_sin = datos_analisis['resultados_sin']
    resultados_con = datos_analisis['resultados_con']
    horas = np.arange(24)

    p_sin = [res['PTloss'] for res in resultados_sin]
    p_con = [res['PTloss'] for res in resultados_con]

    fig, ax = plt.subplots(figsize=(10, 5))
    ancho = 0.35
    pos1 = horas - ancho/2
    pos2 = horas + ancho/2

    ax.bar(pos1, p_sin, ancho, label='Without Compensation',
           color='#1f77b4', alpha=0.85, edgecolor='black', linewidth=0.7)
    ax.bar(pos2, p_con, ancho, label='With Compensation',
           color='#ff7f0e', alpha=0.85, edgecolor='black', linewidth=0.7)

    ax.set_xlabel('Time (h)', fontsize=20)
    ax.set_ylabel('Power Losses (kW)', fontsize=20)
    ax.legend(fontsize=16)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xlim(-0.5, 23.5)
    ax.set_xticks(range(0, 24, 1))
    ax.tick_params(axis='both', labelsize=20)
    plt.tight_layout()

    if ruta_guardado:
        plt.savefig(ruta_guardado, dpi=600, bbox_inches='tight')
    plt.show()
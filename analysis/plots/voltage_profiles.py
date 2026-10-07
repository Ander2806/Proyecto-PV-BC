import matplotlib.pyplot as plt
import numpy as np

def plot_voltage_profiles(datos_analisis, ruta_guardado=None, orientacion='horizontal'):
    """
    Gráfico de perfiles de voltaje sin y con compensación.
    orientacion: 'horizontal' (1x2) o 'vertical' (2x1)
    """
    system_data = datos_analisis['system_data']
    resultados_sin = datos_analisis['resultados_sin']
    resultados_con = datos_analisis['resultados_con']
    nbus = system_data.nbus
    colores = plt.cm.jet(np.linspace(0, 1, nbus))
    horas = np.arange(24)

    if orientacion == 'horizontal':
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    else:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))

    for i in range(nbus):
        voltajes = [np.abs(resultados_sin[h]['Vm'][i]) for h in range(24)]
        ax1.plot(horas, voltajes, color=colores[i], linewidth=1.5)
    ax1.set_title('a) Without Compensation', fontsize=20)
    ax1.set_xlabel('Time (h)', fontsize=20)
    ax1.set_ylabel('Voltage profile (p.u.)', fontsize=20)
    ax1.set_xlim(-0.5, 23.5)
    ax1.set_xticks(range(0, 24, 1))
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='both', labelsize=20)

    for i in range(nbus):
        voltajes = [np.abs(resultados_con[h]['Vm'][i]) for h in range(24)]
        ax2.plot(horas, voltajes, color=colores[i], linewidth=1.5)
    ax2.set_title('b) With Compensation', fontsize=20)
    ax2.set_xlabel('Time (h)', fontsize=20)
    ax2.set_ylabel('Voltage profile (p.u.)', fontsize=20)
    ax2.set_xlim(-0.5, 23.5)
    ax2.set_xticks(range(0, 24, 1))
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='both', labelsize=20)

    # Colorbar
    if orientacion == 'horizontal':
        plt.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.25, wspace=0.15)
        cbar_ax = fig.add_axes([0.15, 0.08, 0.7, 0.05])
        orientation = 'horizontal'
    else:
        plt.subplots_adjust(left=0.08, right=0.85, top=0.95, bottom=0.08, hspace=0.4)
        cbar_ax = fig.add_axes([0.88, 0.08, 0.03, 0.87])
        orientation = 'vertical'

    sm = plt.cm.ScalarMappable(cmap=plt.cm.jet, norm=plt.Normalize(vmin=0, vmax=nbus))
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cbar_ax, orientation=orientation)
    cbar.set_label('Bus Number', fontsize=20)
    etiquetas = list(range(1, nbus+1, max(1, nbus//20)))
    cbar.set_ticks(etiquetas)
    cbar.set_ticklabels([str(x) for x in etiquetas])
    cbar.ax.tick_params(labelsize=20)

    if ruta_guardado:
        plt.savefig(ruta_guardado, dpi=600, bbox_inches='tight')
    plt.show()
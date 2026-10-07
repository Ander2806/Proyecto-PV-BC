import matplotlib.pyplot as plt
import numpy as np
import os

def plot_capacitor_status(datos_analisis, ruta_guardado=None):
    """
    Gráfico tipo Gantt mostrando el estado ON/OFF de cada BC durante el día.
    Si ruta_guardado es proporcionada, guarda la figura en PNG y SVG.
    """
    estado_bc = datos_analisis['estado_bc']
    bc_config = datos_analisis['bc_config']

    nombres = bc_config['nombres']
    ubicaciones = bc_config['ubicaciones']
    capacidades = bc_config['capacidades']

    # Filtrar BC existentes (capacidad > 0)
    bc_existentes = []
    for i, nombre in enumerate(nombres):
        if capacidades[i] > 0 and nombre in estado_bc:
            bc_existentes.append({
                'nombre': nombre,
                'ubicacion': ubicaciones[i],
                'capacidad': capacidades[i],
                'estados': estado_bc[nombre]
            })

    if not bc_existentes:
        print("No hay bancos de condensadores para mostrar.")
        return

    bc_existentes.reverse()  # Para mostrar de abajo hacia arriba

    fig, ax = plt.subplots(figsize=(10, 5))

    for idx, bc in enumerate(bc_existentes):
        estados = bc['estados']
        for hora in range(24):
            color = 'green' if estados[hora] == 1 else 'red'
            ax.barh(idx, 1, left=hora, height=0.8,
                    color=color, edgecolor='black', linewidth=0.5)

    ax.set_yticks(range(len(bc_existentes)))
    ax.set_yticklabels([f"{bc['nombre']}\nBus {bc['ubicacion']}\n{bc['capacidad']:.0f} kVAR"
                        for bc in bc_existentes], fontsize=10)
    ax.set_xlabel('Time (h)', fontsize=20)
    ax.set_ylabel('')
    ax.set_title('Capacitor Bank Status (Green=ON, Red=OFF)', fontsize=20, pad=15)
    ax.set_xlim(-0.5, 24.5)
    ax.set_xticks(range(24))
    ax.grid(True, axis='x', alpha=0.3)
    ax.tick_params(axis='both', labelsize=20)
    plt.tight_layout()

    if ruta_guardado:
        # Guardar PNG
        plt.savefig(ruta_guardado, dpi=600, bbox_inches='tight')
        # Guardar SVG (reemplazar extensión)
        ruta_svg = os.path.splitext(ruta_guardado)[0] + '.svg'
        plt.savefig(ruta_svg, bbox_inches='tight')

    plt.show()
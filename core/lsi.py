import numpy as np

def calculate_lsi_base_case(cache):
    """
    Calcula los índices de sensibilidad LSI1 y LSI2 para el caso base
    (sin compensación) en la hora de máxima demanda (hora 20).
    Devuelve las mejores barras candidatas para PV (LSI1) y BC (LSI2).
    """
    print("\nCalculando LSI para caso base...")
    hora_pico = 20   # Hora de demanda máxima

    # Demanda en la hora pico
    dP = cache.demand_h[hora_pico, :, 0].copy()
    dQ = cache.demand_h[hora_pico, :, 1].copy()

    # Flujo de potencia base (sin compensación)
    P = dP / cache.sys_params.S_base
    Q = dQ / cache.sys_params.S_base
    Vm = np.ones(cache.nbus, dtype=complex)

    for _ in range(100):
        Ibus = (P - 1j * Q) / np.conj(Vm)
        Inode = cache.BIBC @ Ibus[1:]
        V_new = np.ones(cache.nbus, dtype=complex)
        V_new[cache.to_bus] = Vm[cache.from_bus] - cache.Z_line * Inode[cache.line_idx]
        if np.max(np.abs(V_new - Vm)) < 1e-5:
            Vm = V_new
            break
        Vm = V_new

    # Pérdidas en cada línea (kW)
    IL = (Vm[cache.from_bus] - Vm[cache.to_bus]) / cache.Z_line
    I2 = np.abs(IL) ** 2
    PLoss = cache.R * I2 * cache.sys_params.S_base

    # Resistencia de la última línea (para el cálculo simplificado)
    R_last = cache.R[-1] * cache.sys_params.Z_base  # en ohmios

    Pl_pu = PLoss / cache.sys_params.S_base          # pérdidas en p.u.
    Vm_abs = np.abs(Vm[1:])                          # voltajes de barras 2..N

    # Índices LSI1 y LSI2
    LSI1 = -2 * ((P[1:] + Pl_pu) ** 2 + (Q[1:] + Pl_pu) ** 2) * R_last / (Vm_abs ** 3)
    LSI2 = 2 * ((Q[1:] + Pl_pu) ** 2) * R_last / (Vm_abs ** 2)

    # Seleccionar las mejores barras (máximo 16)
    top_n = min(16, cache.nbus - 1)
    top_pv = (np.argsort(LSI1)[:top_n] + 2).astype(int)   # +2 porque excluimos slack
    top_bc = (np.argsort(LSI2)[::-1][:top_n] + 2).astype(int)

    print(f"  PV candidatos (LSI1): {top_pv}")
    print(f"  BC candidatos (LSI2): {top_bc}")
    return top_pv, top_bc
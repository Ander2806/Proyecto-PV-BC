import numpy as np

def power_flow_hourly_optimized(x_vector, hora, bc_status, PTloss_ref_hora, cache,
                                with_compensation=False, return_details=False):
    """
    Flujo de potencia Backward-Forward Sweep para una hora específica.
    Si with_compensation=True, aplica inyecciones de PV y BC según x_vector.
    Devuelve un diccionario con resultados (Vm, pérdidas, potencias, etc.).
    """
    # Copiar demanda horaria precalculada
    dP = cache.demand_h[hora, :, 0].copy()
    dQ = cache.demand_h[hora, :, 1].copy()

    Pt_Dem_total = cache.Pt_dem_h[hora]
    Qt_Dem_total = cache.Qt_dem_h[hora]

    Pt_DG_total = 0.0
    Qt_BC_total = 0.0
    E_PV_by_type = {'residential': 0.0, 'commercial': 0.0, 'industrial': 0.0}
    E_PV_by_bus = {}

    if with_compensation and x_vector is not None:
        NC_max = len(x_vector) // 4
        pv_bars   = np.round(x_vector[:NC_max]).astype(int)
        pv_sizes  = x_vector[NC_max:2*NC_max]
        bc_bars   = np.round(x_vector[2*NC_max:3*NC_max]).astype(int)
        bc_sizes  = x_vector[3*NC_max:]

        # --- Bancos de condensadores activos ---
        bc_mask = ((bc_sizes >= 150) & (bc_status == 1) &
                   (bc_bars >= 2) & (bc_bars <= cache.nbus))
        for i in np.where(bc_mask)[0]:
            dQ[bc_bars[i] - 1] -= bc_sizes[i]
            Qt_BC_total += bc_sizes[i]

        # --- Generación PV activa ---
        pv_factor = cache.pv_factor[hora]
        pv_mask = (pv_sizes >= 50) & (pv_bars >= 2) & (pv_bars <= cache.nbus)
        for i in np.where(pv_mask)[0]:
            pot_pv = pv_sizes[i] * pv_factor
            bus_idx = pv_bars[i]
            dP[bus_idx - 1] -= pot_pv
            Pt_DG_total += pot_pv
            E_PV_by_bus[bus_idx] = pot_pv
            if bus_idx in cache.system_data.bus_categories:
                E_PV_by_type[cache.system_data.bus_categories[bus_idx]] += pot_pv

    # Convertir a p.u.
    P = dP / cache.sys_params.S_base
    Q = dQ / cache.sys_params.S_base

    # --- Barrido iterativo ---
    Vm = np.ones(cache.nbus, dtype=complex)
    eps = 1e-5
    converged = False
    for _ in range(100):
        Ibus = (P - 1j * Q) / np.conj(Vm)
        Inode = cache.BIBC @ Ibus[1:]   # corrientes en ramas

        V_new = np.ones(cache.nbus, dtype=complex)
        V_new[cache.to_bus] = Vm[cache.from_bus] - cache.Z_line * Inode[cache.line_idx]

        if np.max(np.abs(V_new - Vm)) < eps:
            Vm = V_new
            converged = True
            break
        Vm = V_new

    # --- Cálculo de pérdidas (vectorizado) ---
    IL = (Vm[cache.from_bus] - Vm[cache.to_bus]) / cache.Z_line
    I2 = np.abs(IL) ** 2
    PLoss = cache.R * I2 * cache.sys_params.S_base
    QLoss = cache.X * I2 * cache.sys_params.S_base
    PTloss = np.sum(PLoss)
    QTloss = np.sum(QLoss)

    # --- Potencias en la subestación ---
    Pt_Grid = Pt_Dem_total - Pt_DG_total + PTloss
    Qt_Grid = Qt_Dem_total - Qt_BC_total + QTloss

    # --- Balance de potencia (debe ser ~0) ---
    balance_P_error = abs((Pt_Grid + Pt_DG_total - PTloss) - Pt_Dem_total)
    balance_Q_error = abs((Qt_Grid + Qt_BC_total - QTloss) - Qt_Dem_total)

    # --- Energía por tipo de consumidor (demanda + pérdidas asignadas) ---
    E_by_type = {}
    for tipo, idx in [('residential', 0), ('commercial', 1), ('industrial', 2)]:
        mask = (cache.bus_to_category_idx[1:] == idx)
        E_by_type[tipo] = np.sum(cache.demand_h[hora, 1:, 0][mask])
    total_demand = sum(E_by_type.values())
    Eloss_by_type = {t: PTloss * (E_by_type[t] / total_demand) if total_demand > 0 else 0.0
                     for t in E_by_type}

    result = {
        'Vm': Vm,
        'PTloss': PTloss,
        'QTloss': QTloss,
        'Pt_Grid': Pt_Grid,
        'Qt_Grid': Qt_Grid,
        'balance_P_error': balance_P_error,
        'balance_Q_error': balance_Q_error,
        'E_by_type': E_by_type,
        'Eloss_by_type': Eloss_by_type,
        'E_PV_by_type': E_PV_by_type,
        'E_PV_by_bus': E_PV_by_bus,
        'Pt_DG_total': Pt_DG_total,
        'Qt_BC_total': Qt_BC_total,
        'converged': converged
    }

    if return_details:
        result['PLoss'] = PLoss
        result['QLoss'] = QLoss
        result['bus_data_hora'] = np.column_stack([
            cache.system_data.bus_data_base[:, 0],
            dP, dQ,
            cache.system_data.bus_data_base[:, 3:]
        ])

    return result


def optimize_bc_hourly_fast(x_vector, hora, PTloss_ref_hora, NC_max, cache):
    """
    Determina el estado óptimo (ON/OFF) de los bancos de condensadores
    para una hora dada, de modo que se cumplan restricciones de voltaje
    y pérdidas sin exceder la referencia.
    Devuelve un vector binario de longitud NC_max.
    """
    bc_sizes_raw = x_vector[3*NC_max:]
    bc_mask = bc_sizes_raw >= 50
    if not np.any(bc_mask):
        return np.zeros(NC_max)

    # Inicialmente todos los BC activos
    best_status = np.zeros(NC_max)
    best_status[bc_mask] = 1

    # Evaluar con todos encendidos
    result = power_flow_hourly_optimized(x_vector, hora, best_status,
                                         PTloss_ref_hora, cache,
                                         with_compensation=True)
    Vm_abs = np.abs(result['Vm'])
    volt_ok = np.all((Vm_abs >= 0.93) & (Vm_abs <= 1.05))
    loss_ok = result['PTloss'] <= PTloss_ref_hora

    if volt_ok and loss_ok:
        return best_status

    # Si no cumple, apagar bancos en orden de mayor a menor tamaño
    bc_indices = np.where(bc_mask)[0]
    sorted_bc = sorted(bc_indices, key=lambda i: bc_sizes_raw[i], reverse=True)

    for bc_idx in sorted_bc:
        best_status[bc_idx] = 0
        result = power_flow_hourly_optimized(x_vector, hora, best_status,
                                             PTloss_ref_hora, cache,
                                             with_compensation=True)
        Vm_abs = np.abs(result['Vm'])
        if (np.all((Vm_abs >= 0.93) & (Vm_abs <= 1.05)) and
                result['PTloss'] <= PTloss_ref_hora):
            break

    return best_status
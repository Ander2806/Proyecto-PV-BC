import numpy as np
from core.power_flow import power_flow_hourly_optimized, optimize_bc_hourly_fast

def objective_function_optimized(x, NC_max, opt_params, PTloss_ref_hourly, cache):
    """
    Función objetivo completa: costo anual total (grid + inversión + O&M)
    con penalizaciones por violaciones de restricciones.
    """
    pv_bars_raw  = np.round(x[:NC_max]).astype(int)
    pv_sizes_raw = x[NC_max:2*NC_max]
    bc_bars_raw  = np.round(x[2*NC_max:3*NC_max]).astype(int)
    bc_sizes_raw = x[3*NC_max:]

    # Seleccionar solo elementos activos según umbrales
    pv_mask = pv_sizes_raw >= opt_params.umbral_pv
    bc_mask = bc_sizes_raw >= opt_params.umbral_bc
    pv_bars  = pv_bars_raw[pv_mask]
    pv_sizes = pv_sizes_raw[pv_mask]
    bc_bars  = bc_bars_raw[bc_mask]
    bc_sizes = bc_sizes_raw[bc_mask]

    # Validación de unicidad y límites
    if (len(pv_bars) != len(np.unique(pv_bars)) or
        len(bc_bars) != len(np.unique(bc_bars)) or
        np.any((pv_bars < 2) | (pv_bars > cache.nbus)) or
        np.any((bc_bars < 2) | (bc_bars > cache.nbus))):
        return 1e12

    C_Grid_anual = 0.0
    balance_errors = np.zeros(24)
    voltage_violations = 0.0
    loss_violations = 0.0
    Cost_DG_OM_anual_total = 0.0
    dg_capacity_violations = 0.0
    bc_capacity_violations = 0.0

    tipo_to_col = {'residential': 0, 'industrial': 1, 'commercial': 2}

    for hora in range(24):
        try:
            Pt_Dem_total_hora = cache.Pt_dem_h[hora]
            Qt_Dem_total_hora = cache.Qt_dem_h[hora]

            pv_factor = cache.pv_factor[hora]
            Pt_DG_total = float(np.sum(pv_sizes) * pv_factor)

            if Pt_DG_total > Pt_Dem_total_hora:
                dg_capacity_violations += (Pt_DG_total - Pt_Dem_total_hora) * 1e8

            # Estado óptimo de BCs para esta hora
            bc_status = optimize_bc_hourly_fast(x, hora, PTloss_ref_hourly[hora],
                                                NC_max, cache)
            Qt_BC_total = 0.0
            for i, s in enumerate(bc_sizes):
                if bc_status[bc_mask][i] == 1:
                    Qt_BC_total += s

            if Qt_BC_total > Qt_Dem_total_hora:
                bc_capacity_violations += (Qt_BC_total - Qt_Dem_total_hora) * 1e8

            # Flujo de potencia con compensación
            results = power_flow_hourly_optimized(x, hora, bc_status,
                                                  PTloss_ref_hourly[hora], cache,
                                                  with_compensation=True)
            if not results['converged']:
                return 1e12

            if results['PTloss'] > PTloss_ref_hourly[hora]:
                loss_violations += 1e6

            Vm_abs = np.abs(results['Vm'])
            voltage_violations += np.sum(np.maximum(0, Vm_abs - 1.05) ** 2) * 1e8
            voltage_violations += np.sum(np.maximum(0, 0.93 - Vm_abs) ** 2) * 1e8

            balance_errors[hora] = results['balance_P_error'] + results['balance_Q_error']

            E_by_type = results['E_by_type']
            E_PV_by_bus = results['E_PV_by_bus']
            Eloss_by_type = results['Eloss_by_type']

            # Costo de energía comprada por tipo
            for tipo in ['residential', 'industrial', 'commercial']:
                E_Grid_tipo = E_by_type[tipo] + Eloss_by_type[tipo]
                for bus_idx, e_pv in E_PV_by_bus.items():
                    if cache.system_data.bus_categories.get(bus_idx) == tipo:
                        E_Grid_tipo -= e_pv
                C_Grid_anual += E_Grid_tipo * cache.cost_energy_hourly[hora, tipo_to_col[tipo]]

            # Costo O&M de PV
            for s in pv_sizes:
                E_DG_i_h = (s / opt_params.LF) * pv_factor
                Cost_DG_OM_anual_total += E_DG_i_h * opt_params.cost_OM_DG

        except Exception:
            return 1e12

    C_Grid_anual *= 365
    Cost_DG_OM_anual_total *= 365

    # Costos de inversión anualizados
    C_DG = 0.0
    if len(pv_sizes) > 0:
        CAPEX_DG = np.sum((opt_params.DG_cost * pv_sizes * opt_params.G_r) / opt_params.LF)
        C_DG = CAPEX_DG / opt_params.tiempo_vida_DG + Cost_DG_OM_anual_total

    C_BC = 0.0
    if len(bc_sizes) > 0:
        CAPEX_BC = opt_params.Cost_BC_inst * len(bc_sizes) + opt_params.Cost_BC_cap * np.sum(bc_sizes)
        C_BC = CAPEX_BC / opt_params.tiempo_vida_BC + len(bc_sizes) * opt_params.cost_OM_BC

    Z_base = (C_Grid_anual + C_DG + C_BC) / 1e6   # en MUSD

    penalty = (loss_violations + voltage_violations +
               dg_capacity_violations + bc_capacity_violations) * Z_base

    if np.mean(balance_errors) > 0.01:
        penalty += Z_base * 1e6 * np.mean(balance_errors) ** 2

    Z = Z_base + penalty
    return Z if np.isfinite(Z) and Z > 0 else 1e12
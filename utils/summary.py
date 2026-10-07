import numpy as np
import os
import pandas as pd
from core.power_flow import power_flow_hourly_optimized, optimize_bc_hourly_fast

def calculate_detailed_costs(best_x, NC_max, opt_params, PTloss_ref_hourly, cache):
    """
    Calcula los costos detallados (grid, PV, BC, pérdidas) a partir de la mejor solución.
    Retorna un diccionario con todos los valores anualizados.
    """
    pv_bars_raw = np.round(best_x[:NC_max]).astype(int)
    pv_sizes_raw = best_x[NC_max:2*NC_max]
    bc_bars_raw = np.round(best_x[2*NC_max:3*NC_max]).astype(int)
    bc_sizes_raw = best_x[3*NC_max:]

    pv_mask = pv_sizes_raw >= opt_params.umbral_pv
    bc_mask = bc_sizes_raw >= opt_params.umbral_bc
    pv_sizes = pv_sizes_raw[pv_mask]
    bc_sizes = bc_sizes_raw[bc_mask]
    pv_bars = pv_bars_raw[pv_mask]

    C_Grid_anual = 0.0
    OM_DG_anual = 0.0
    E_PV_total = 0.0
    Perdidas_tot = 0.0
    E_Grid_tipo = {'residential': 0.0, 'commercial': 0.0, 'industrial': 0.0}
    tipo_to_col = {'residential': 0, 'industrial': 1, 'commercial': 2}
    cat_names = ['residential', 'commercial', 'industrial']

    for hora in range(24):
        bc_status = optimize_bc_hourly_fast(best_x, hora, PTloss_ref_hourly[hora], NC_max, cache)
        results = power_flow_hourly_optimized(best_x, hora, bc_status,
                                              PTloss_ref_hourly[hora], cache,
                                              with_compensation=True)

        Pt_total = cache.Pt_dem_h[hora]
        for ci, cat in enumerate(cat_names):
            E_dem = cache.demand_h[hora, 1:, 0][cache.bus_to_category_idx[1:] == ci].sum()
            E_loss = results['PTloss'] * (E_dem / Pt_total if Pt_total > 0 else 0)
            E_pv = results['E_PV_by_type'].get(cat, 0.0)
            E_neta = max(0.0, E_dem - E_pv) + E_loss
            C_Grid_anual += E_neta * cache.cost_energy_hourly[hora, tipo_to_col[cat]]
            E_Grid_tipo[cat] += E_neta

        Perdidas_tot += results['PTloss']
        pv_fac = cache.pv_factor[hora]
        for s in pv_sizes:
            OM_DG_anual += (s / opt_params.LF) * pv_fac * opt_params.cost_OM_DG
            E_PV_total += s * pv_fac

    C_Grid_anual *= 365
    OM_DG_anual *= 365
    E_PV_total *= 365
    Perdidas_tot *= 365
    for k in E_Grid_tipo:
        E_Grid_tipo[k] *= 365

    C_DG = CAPEX_DG = 0.0
    if len(pv_sizes) > 0:
        CAPEX_DG = np.sum((opt_params.DG_cost * pv_sizes * opt_params.G_r) / opt_params.LF)
        C_DG = CAPEX_DG / opt_params.tiempo_vida_DG + OM_DG_anual

    C_BC = CAPEX_BC = OM_BC = 0.0
    if len(bc_sizes) > 0:
        CAPEX_BC = opt_params.Cost_BC_inst * len(bc_sizes) + opt_params.Cost_BC_cap * np.sum(bc_sizes)
        OM_BC = len(bc_sizes) * opt_params.cost_OM_BC
        C_BC = CAPEX_BC / opt_params.tiempo_vida_BC + OM_BC

    return {
        'C_Grid_Anual_USD': C_Grid_anual,
        'Energia_Grid_Residential_Anual_kWh': E_Grid_tipo['residential'],
        'Energia_Grid_Commercial_Anual_kWh': E_Grid_tipo['commercial'],
        'Energia_Grid_Industrial_Anual_kWh': E_Grid_tipo['industrial'],
        'Energia_Grid_Total_Anual_kWh': sum(E_Grid_tipo.values()),
        'CAPEX_PV_USD': CAPEX_DG,
        'C_PV_Anual_USD': C_DG,
        'Cost_OyM_PV_Anual_USD': OM_DG_anual,
        'Energia_PV_Anual_kWh': E_PV_total,
        'CAPEX_BC_USD': CAPEX_BC,
        'C_BC_Anual_USD': C_BC,
        'Cost_OyM_BC_Anual_USD': OM_BC,
        'Perdidas_Energia_Anual_kWh': Perdidas_tot,
        'Costo_Total_Anual_USD': (C_Grid_anual + C_DG + C_BC) / 1e6
    }


def generate_summary(best_x, NC_max, opt_params, PTloss_ref_hourly, cache,
                     base_case_results, opt_result):
    """
    Genera un diccionario con el resumen de una ejecución: ubicaciones, capacidades,
    pérdidas, voltajes, costos, etc.
    """
    pv_bars_raw = np.round(best_x[:NC_max]).astype(int)
    pv_sizes_raw = best_x[NC_max:2*NC_max]
    bc_bars_raw = np.round(best_x[2*NC_max:3*NC_max]).astype(int)
    bc_sizes_raw = best_x[3*NC_max:]

    pv_mask = pv_sizes_raw >= opt_params.umbral_pv
    bc_mask = bc_sizes_raw >= opt_params.umbral_bc
    pv_bars = pv_bars_raw[pv_mask]
    pv_sizes = pv_sizes_raw[pv_mask]
    bc_bars = bc_bars_raw[bc_mask]
    bc_sizes = bc_sizes_raw[bc_mask]

    # Sin compensación
    PTl_sin = QTl_sin = E_sub = C_sub = C_perd = 0.0
    Vmin_sin = 1.0
    Vmax_sin = 0.0
    for hora in range(24):
        r = power_flow_hourly_optimized(None, hora, np.zeros(NC_max), 0, cache)
        PTl_sin += r['PTloss']
        QTl_sin += r['QTloss']
        Va = np.abs(r['Vm'][1:])
        Vmin_sin = min(Vmin_sin, np.min(Va))
        Vmax_sin = max(Vmax_sin, np.max(Va))
        E_total = cache.Pt_dem_h[hora]
        precio = np.mean(cache.cost_energy_hourly[hora])
        E_sub += E_total
        C_sub += E_total * precio
        C_perd += r['PTloss'] * precio

    E_perd_sin = PTl_sin * 365
    E_sub_anual = E_sub * 365
    C_sub *= 365 / 1e6
    C_perd *= 365 / 1e6

    # Con compensación
    PTl_con = QTl_con = E_PV_tot = 0.0
    Vmin_con = 1.0
    Vmax_con = 0.0
    for hora in range(24):
        bc_status = optimize_bc_hourly_fast(best_x, hora, PTloss_ref_hourly[hora], NC_max, cache)
        r = power_flow_hourly_optimized(best_x, hora, bc_status,
                                        PTloss_ref_hourly[hora], cache,
                                        with_compensation=True)
        PTl_con += r['PTloss']
        QTl_con += r['QTloss']
        Va = np.abs(r['Vm'][1:])
        Vmin_con = min(Vmin_con, np.min(Va))
        Vmax_con = max(Vmax_con, np.max(Va))
        pv_fac = cache.pv_factor[hora]
        for s in pv_sizes:
            E_PV_tot += s * pv_fac

    red_p = (PTl_sin - PTl_con) / PTl_sin * 100 if PTl_sin > 0 else 0
    red_e = (E_perd_sin - PTl_con * 365) / E_perd_sin * 100 if E_perd_sin > 0 else 0

    costos = calculate_detailed_costs(best_x, NC_max, opt_params, PTloss_ref_hourly, cache)

    return {
        'PV_Instalados': len(pv_bars),
        'Barras_PV': ' '.join(map(str, pv_bars)),
        'Capacidades_PV_kW': ' '.join([f'{x:.2f}' for x in pv_sizes]),
        'Capacidad_Total_PV_kW': float(np.sum(pv_sizes)),
        'BC_Instalados': len(bc_bars),
        'Barras_BC': ' '.join(map(str, bc_bars)),
        'Capacidades_BC_kVAR': ' '.join([f'{x:.2f}' for x in bc_sizes]),
        'Capacidad_Total_BC_kVAR': float(np.sum(bc_sizes)),
        'Funcion_Objetivo': opt_result['best_fitness'],
        'Perdida_Promedio_Sin_kW': PTl_sin / 24,
        'Perdida_Promedio_Con_kW': PTl_con / 24,
        'Perdida_Reactiva_Sin_kVAR': QTl_sin / 24,
        'Perdida_Reactiva_Con_kVAR': QTl_con / 24,
        'Energia_Perdidas_Sin_kWh_año': E_perd_sin,
        'Energia_Perdidas_Con_kWh_año': PTl_con * 365,
        'Energia_Subestacion_Sin_kWh_año': E_sub_anual,
        'Energia_Total_Red_Sin_kWh_año': E_sub_anual + E_perd_sin,
        'Energia_PV_kWh_año': E_PV_tot * 365,
        'Reduccion_Perdidas_Porcentaje': red_p,
        'Reduccion_Energia_Perdidas_Porcentaje': red_e,
        'Vmin_Sin_pu': Vmin_sin,
        'Vmax_Sin_pu': Vmax_sin,
        'Vmin_Con_pu': Vmin_con,
        'Vmax_Con_pu': Vmax_con,
        'Costo_Energia_Subestacion_Sin_M_USD_año': C_sub,
        'Costo_Perdidas_Sin_M_USD_año': C_perd,
        'Costo_Total_Red_Sin_M_USD_año': C_sub + C_perd,
        'Costo_Grid_Con_M_USD_año': costos['C_Grid_Anual_USD'] / 1e6,
        'CAPEX_PV_USD': costos['CAPEX_PV_USD'],
        'Costo_PV_Anual_M_USD': costos['C_PV_Anual_USD'] / 1e6,
        'Costo_OyM_PV_M_USD_año': costos['Cost_OyM_PV_Anual_USD'] / 1e6,
        'CAPEX_BC_USD': costos['CAPEX_BC_USD'],
        'Costo_BC_Anual_M_USD': costos['C_BC_Anual_USD'] / 1e6,
        'Costo_OyM_BC_M_USD_año': costos['Cost_OyM_BC_Anual_USD'] / 1e6,
        'Costo_Total_Con_M_USD_año': costos['Costo_Total_Anual_USD'],
        'Tiempo_Ejecucion_seg': opt_result['elapsed_time']
    }


def save_global_summary(all_executions, algorithm, system_type, output_dir):
    """
    Guarda un archivo Excel con el resumen de todas las ejecuciones de un algoritmo.
    all_executions: lista de diccionarios generados por generate_summary.
    """
    filename = os.path.join(os.path.abspath(output_dir), f'Resumen_{algorithm}_{system_type}.xlsx')
    summary_data = []
    for i, e in enumerate(all_executions):
        summary_data.append({
            'Ejecucion': i + 1,
            'BC_Instalados': e['BC_Instalados'],
            'Barras_BC': e['Barras_BC'],
            'Capacidades_BC_kVAR': e['Capacidades_BC_kVAR'],
            'PV_Instalados': e['PV_Instalados'],
            'Barras_PV': e['Barras_PV'],
            'Capacidades_PV_kW': e['Capacidades_PV_kW'],
            'Funcion_Objetivo': e['Funcion_Objetivo'],
            'Loss_Anual_Sin_kWh': e['Energia_Perdidas_Sin_kWh_año'],
            'Loss_Anual_Sin_kVARh': e['Perdida_Reactiva_Sin_kVAR'] * 24 * 365,
            'Cost_Loss_Sin_USD': e['Costo_Perdidas_Sin_M_USD_año'] * 1e6,
            'Cost_Grid_Sin_USD': e['Costo_Total_Red_Sin_M_USD_año'] * 1e6,
            'Min_Tension_Con_pu': e['Vmin_Con_pu'],
            'Max_Tension_Con_pu': e['Vmax_Con_pu'],
            'Loss_Anual_Con_kWh': e['Energia_Perdidas_Con_kWh_año'],
            'Loss_Anual_Con_kVARh': e['Perdida_Reactiva_Con_kVAR'] * 24 * 365,
            'Cost_Loss_Con_USD': (e['Energia_Perdidas_Con_kWh_año'] /
                                  max(e['Energia_Perdidas_Sin_kWh_año'], 1)) *
                                 e['Costo_Perdidas_Sin_M_USD_año'] * 1e6,
            'Cost_Grid_Con_USD': e['Costo_Grid_Con_M_USD_año'] * 1e6,
            'Energia_PV_kWh': e['Energia_PV_kWh_año'],
            'Cost_OyM_PV_USD': e['Costo_OyM_PV_M_USD_año'] * 1e6,
            'CAPEX_PV_USD': e['CAPEX_PV_USD'],
            'CAPEX_BC_USD': e['CAPEX_BC_USD'],
            'Cost_OyM_BC_USD': e['Costo_OyM_BC_M_USD_año'] * 1e6,
            'Costo_Total_Anual_USD': e['Costo_Total_Con_M_USD_año'] * 1e6,
            'Reduccion_Perdidas_Pct': e['Reduccion_Perdidas_Porcentaje'],
            'Tiempo_Ejecucion_seg': e['Tiempo_Ejecucion_seg']
        })
    pd.DataFrame(summary_data).to_excel(filename, index=False)
    print(f"\nResumen global guardado: {filename}")
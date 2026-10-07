import pandas as pd
import numpy as np
import os
from core.power_flow import power_flow_hourly_optimized, optimize_bc_hourly_fast

def save_results_to_excel(opt_result, best_x, NC_max, opt_params, PTloss_ref_hourly,
                          cache, base_case_results, filename):
    """
    Guarda los resultados completos de una ejecución de optimización en un archivo Excel
    con 13 hojas que cubren demanda, voltajes, pérdidas, costos, etc.
    """
    writer = pd.ExcelWriter(filename, engine='openpyxl')

    # ── HOJA 1: Demanda horaria ───────────────────────────────────────────
    dem_rows = []
    for hora in range(24):
        row = {'Hora': hora}
        total = 0.0
        for bus in range(1, cache.nbus + 1):
            val = cache.demand_h[hora, bus - 1, 0]
            row[f'Barra_{bus}_kW'] = val
            total += val
        row['Total_kW'] = total
        dem_rows.append(row)
    pd.DataFrame(dem_rows).to_excel(writer, sheet_name='Demanda_Horaria', index=False)

    # ── HOJA 2: Voltajes iniciales ────────────────────────────────────────
    vsin_rows = []
    for hora in range(24):
        r = power_flow_hourly_optimized(None, hora, np.zeros(NC_max), 0, cache)
        row = {'Hora': hora}
        for bus in range(1, cache.nbus + 1):
            row[f'Barra_{bus}_pu'] = np.abs(r['Vm'][bus - 1])
        vsin_rows.append(row)
    pd.DataFrame(vsin_rows).to_excel(writer, sheet_name='Voltajes_Iniciales', index=False)

    # ── HOJA 3: Pérdidas activas iniciales ───────────────────────────────
    psin_rows = []
    for hora in range(24):
        r = power_flow_hourly_optimized(None, hora, np.zeros(NC_max), 0, cache, return_details=True)
        row = {'Hora': hora}
        for k in range(cache.nline):
            row[f'Linea_{k+1}_kW'] = r['PLoss'][k]
        row['Total_kW'] = np.sum(r['PLoss'])
        psin_rows.append(row)
    pd.DataFrame(psin_rows).to_excel(writer, sheet_name='Perdidas_Activas_Iniciales', index=False)

    # ── HOJA 4: Pérdidas reactivas iniciales ─────────────────────────────
    qsin_rows = []
    for hora in range(24):
        r = power_flow_hourly_optimized(None, hora, np.zeros(NC_max), 0, cache, return_details=True)
        row = {'Hora': hora}
        for k in range(cache.nline):
            row[f'Linea_{k+1}_kVAR'] = r['QLoss'][k]
        row['Total_kVAR'] = np.sum(r['QLoss'])
        qsin_rows.append(row)
    pd.DataFrame(qsin_rows).to_excel(writer, sheet_name='Perdidas_Reactivas_Iniciales', index=False)

    # ── HOJA 5: Costos iniciales ──────────────────────────────────────────
    csin_rows = []
    for hora in range(24):
        r = power_flow_hourly_optimized(None, hora, np.zeros(NC_max), 0, cache)
        E_total = cache.Pt_dem_h[hora]
        precio = np.mean(cache.cost_energy_hourly[hora])
        csin_rows.append({'Hora': hora, 'Demanda_Total_kW': E_total,
                          'Perdidas_kW': r['PTloss'], 'Perdidas_kVAR': r['QTloss'],
                          'Costo_Energia_USD': E_total * precio,
                          'Costo_Perdidas_USD': r['PTloss'] * precio})
    pd.DataFrame(csin_rows).to_excel(writer, sheet_name='Costos_Iniciales', index=False)

    # ── HOJA 6: Todas las soluciones por iteración ────────────────────────
    iter_rows = [{'Iteracion': t + 1,
                  **{f'Individuo_{i+1}': f for i, f in enumerate(fa)}}
                 for t, fa in enumerate(opt_result['all_iterations'])]
    pd.DataFrame(iter_rows).to_excel(writer, sheet_name='Soluciones_Iteraciones', index=False)

    # ── HOJA 7: Estadísticas por iteración ───────────────────────────────
    stats_rows = []
    for t, fa in enumerate(opt_result['all_iterations']):
        valid = fa[fa < 1e12]
        stats_rows.append({'Iteracion': t + 1, 'Mejor': np.min(fa),
                           'Peor': np.max(valid) if len(valid) > 0 else np.nan,
                           'Promedio': np.mean(valid) if len(valid) > 0 else np.nan})
    pd.DataFrame(stats_rows).to_excel(writer, sheet_name='Estadisticas_Iteraciones', index=False)

    # ── HOJA 8: Voltajes finales ──────────────────────────────────────────
    vcon_rows = []
    for hora in range(24):
        bc_s = optimize_bc_hourly_fast(best_x, hora, PTloss_ref_hourly[hora], NC_max, cache)
        r = power_flow_hourly_optimized(best_x, hora, bc_s, PTloss_ref_hourly[hora],
                                        cache, with_compensation=True)
        row = {'Hora': hora}
        for bus in range(1, cache.nbus + 1):
            row[f'Barra_{bus}_pu'] = np.abs(r['Vm'][bus - 1])
        vcon_rows.append(row)
    pd.DataFrame(vcon_rows).to_excel(writer, sheet_name='Voltajes_Finales', index=False)

    # ── HOJA 9: Pérdidas activas finales ─────────────────────────────────
    pcon_rows = []
    for hora in range(24):
        bc_s = optimize_bc_hourly_fast(best_x, hora, PTloss_ref_hourly[hora], NC_max, cache)
        r = power_flow_hourly_optimized(best_x, hora, bc_s, PTloss_ref_hourly[hora],
                                        cache, with_compensation=True, return_details=True)
        row = {'Hora': hora}
        for k in range(cache.nline):
            row[f'Linea_{k+1}_kW'] = r['PLoss'][k]
        row['Total_kW'] = np.sum(r['PLoss'])
        pcon_rows.append(row)
    pd.DataFrame(pcon_rows).to_excel(writer, sheet_name='Perdidas_Activas_Finales', index=False)

    # ── HOJA 10: Pérdidas reactivas finales ──────────────────────────────
    qcon_rows = []
    for hora in range(24):
        bc_s = optimize_bc_hourly_fast(best_x, hora, PTloss_ref_hourly[hora], NC_max, cache)
        r = power_flow_hourly_optimized(best_x, hora, bc_s, PTloss_ref_hourly[hora],
                                        cache, with_compensation=True, return_details=True)
        row = {'Hora': hora}
        for k in range(cache.nline):
            row[f'Linea_{k+1}_kVAR'] = r['QLoss'][k]
        row['Total_kVAR'] = np.sum(r['QLoss'])
        qcon_rows.append(row)
    pd.DataFrame(qcon_rows).to_excel(writer, sheet_name='Perdidas_Reactivas_Finales', index=False)

    # ── HOJA 11: Estado de BC por hora ───────────────────────────────────
    bc_bars_raw = np.round(best_x[2*NC_max:3*NC_max]).astype(int)
    bc_sizes_raw = best_x[3*NC_max:]
    bc_mask = bc_sizes_raw >= opt_params.umbral_bc
    bc_bars_act = bc_bars_raw[bc_mask]
    bc_rows = []
    for hora in range(24):
        bc_s = optimize_bc_hourly_fast(best_x, hora, PTloss_ref_hourly[hora], NC_max, cache)
        row = {'Hora': hora}
        for ii, bar in enumerate(bc_bars_act):
            row[f'BC_Barra_{bar}'] = int(bc_s[np.where(bc_mask)[0][ii]])
        bc_rows.append(row)
    pd.DataFrame(bc_rows).to_excel(writer, sheet_name='Estado_BC_Horario', index=False)

    # ── HOJA 12: Costos detallados ────────────────────────────────────────
    from utils.summary import calculate_detailed_costs
    costos = calculate_detailed_costs(best_x, NC_max, opt_params, PTloss_ref_hourly, cache)
    pd.DataFrame([costos]).to_excel(writer, sheet_name='Costos_Detallados', index=False)

    # ── HOJA 13: Resumen completo ─────────────────────────────────────────
    from utils.summary import generate_summary
    resumen = generate_summary(best_x, NC_max, opt_params, PTloss_ref_hourly, cache,
                               base_case_results, opt_result)
    pd.DataFrame([resumen]).to_excel(writer, sheet_name='Resumen', index=False)

    writer.close()
    print(f"\nArchivo guardado: {filename}")
import numpy as np
from core.parameters import OptimizationParameters
from core.data_loader import SystemData
from core.system_cache import SystemCache
from core.power_flow import power_flow_hourly_optimized

def evaluacion_economica(datos_analisis, tasa_descuento=0.08, horizonte=20,
                         vida_util_pv=20, vida_util_bc=10):
    """
    Evaluación económica completa con tablas de ingresos, egresos e indicadores.
    Retorna un diccionario con todos los valores calculados.
    """
    resultados_sin = datos_analisis['resultados_sin']
    resultados_con = datos_analisis['resultados_con']
    pv_config = datos_analisis['pv_config']
    bc_config = datos_analisis['bc_config']
    system_data = datos_analisis['system_data']
    cache = datos_analisis['cache']
    opt_params = OptimizationParameters()

    # Acceder a los precios horarios desde el caché
    cost_energy_hourly = cache.cost_energy_hourly

    # CAPEX
    pv_sizes_activos = [cap for cap in pv_config['capacidades'] if cap >= 50]
    CAPEX_PV = 0
    if len(pv_sizes_activos) > 0:
        CAPEX_PV = np.sum([(opt_params.DG_cost * cap * opt_params.G_r) / opt_params.LF
                           for cap in pv_sizes_activos])

    bc_sizes_activos = [cap for cap in bc_config['capacidades'] if cap >= 150]
    CAPEX_BC = 0
    if len(bc_sizes_activos) > 0:
        CAPEX_BC = (opt_params.Cost_BC_inst * len(bc_sizes_activos) +
                    opt_params.Cost_BC_cap * np.sum(bc_sizes_activos))

    CAPEX_TOTAL = CAPEX_PV + CAPEX_BC

    tipo_to_col = {'residential': 0, 'industrial': 1, 'commercial': 2}

    # Costos base (sin proyecto)
    costo_grid_base = 0.0
    costo_perdidas_base = 0.0
    for hora in range(24):
        res = resultados_sin[hora]
        E_by_type = res['E_by_type']
        Eloss_by_type = res['Eloss_by_type']
        for tipo in ['residential', 'industrial', 'commercial']:
            E_dem = E_by_type[tipo]
            E_perd = Eloss_by_type[tipo]
            precio = cost_energy_hourly[hora, tipo_to_col[tipo]]
            costo_grid_base += (E_dem + E_perd) * precio
            costo_perdidas_base += E_perd * precio

    costo_grid_base_anual = costo_grid_base * 365
    costo_perdidas_base_anual = costo_perdidas_base * 365

    # Costos con proyecto
    costo_grid_proy = 0.0
    costo_perdidas_proy = 0.0
    for hora in range(24):
        res = resultados_con[hora]
        E_by_type = res['E_by_type']
        Eloss_by_type = res['Eloss_by_type']
        E_PV_by_bus = res['E_PV_by_bus']
        for tipo in ['residential', 'industrial', 'commercial']:
            E_dem = E_by_type[tipo]
            E_perd = Eloss_by_type[tipo]
            precio = cost_energy_hourly[hora, tipo_to_col[tipo]]
            E_pv_tipo = sum([pv for bus, pv in E_PV_by_bus.items()
                             if bus in system_data.bus_categories
                             and system_data.bus_categories[bus] == tipo])
            E_grid = max(0, E_dem + E_perd - E_pv_tipo)
            costo_grid_proy += E_grid * precio
            costo_perdidas_proy += E_perd * precio

    costo_grid_proy_anual = costo_grid_proy * 365
    costo_perdidas_proy_anual = costo_perdidas_proy * 365

    # O&M
    OM_PV = 0.0
    pv_factor = cache.pv_factor
    for hora in range(24):
        for cap in pv_sizes_activos:
            OM_PV += (cap / opt_params.LF) * pv_factor[hora] * opt_params.cost_OM_DG
    OM_PV *= 365
    OM_BC = len(bc_sizes_activos) * opt_params.cost_OM_BC

    # Beneficios
    ahorro_energia = costo_grid_base_anual - costo_grid_proy_anual
    ahorro_perdidas = costo_perdidas_base_anual - costo_perdidas_proy_anual
    total_ingresos = ahorro_energia + ahorro_perdidas
    total_egresos_oper = OM_PV + OM_BC
    flujo_neto_anual = total_ingresos - total_egresos_oper

    # Reemplazos y valor residual
    flujos_caja = []
    reemplazos_bc = []
    for año in range(1, horizonte + 1):
        flujo = flujo_neto_anual
        if año % vida_util_bc == 0 and año < horizonte:
            flujo -= CAPEX_BC
            reemplazos_bc.append(año)
        flujos_caja.append(flujo)

    # Valor residual
    valor_residual_pv = 0
    años_restantes_bc = horizonte % vida_util_bc
    if años_restantes_bc == 0:
        valor_residual_bc = 0
    else:
        valor_residual_bc = (vida_util_bc - años_restantes_bc) / vida_util_bc * CAPEX_BC
    valor_residual_total = valor_residual_pv + valor_residual_bc
    flujos_caja[-1] += valor_residual_total

    # Indicadores
    payback = CAPEX_TOTAL / flujo_neto_anual if flujo_neto_anual > 0 else np.inf
    suma_flujos = sum(flujos_caja)
    roi = (suma_flujos - CAPEX_TOTAL) / CAPEX_TOTAL * 100 if CAPEX_TOTAL > 0 else 0.0
    vpn = -CAPEX_TOTAL
    for t, flujo in enumerate(flujos_caja, start=1):
        vpn += flujo / ((1 + tasa_descuento) ** t)

    # Imprimir tablas
    print("\n" + "="*90)
    print("TABLA DE INGRESOS (AHORROS) ANUALES")
    print("="*90)
    print(f"Ahorro en compra de energía: ${ahorro_energia:,.2f}")
    print(f"Ahorro por reducción de pérdidas: ${ahorro_perdidas:,.2f}")
    print(f"TOTAL INGRESOS ANUALES: ${total_ingresos:,.2f}")
    print(f"Valor residual PV: ${valor_residual_pv:,.2f}")
    print(f"Valor residual BC: ${valor_residual_bc:,.2f}")

    print("\n" + "="*90)
    print("TABLA DE EGRESOS")
    print("="*90)
    print(f"CAPEX PV: ${CAPEX_PV:,.2f}")
    print(f"CAPEX BC: ${CAPEX_BC:,.2f}")
    print(f"O&M PV anual: ${OM_PV:,.2f}")
    print(f"O&M BC anual: ${OM_BC:,.2f}")
    print(f"Reemplazos BC en años: {reemplazos_bc}")

    print("\n" + "="*90)
    print("INDICADORES ECONÓMICOS")
    print("="*90)
    print(f"Payback: {payback:.2f} años")
    print(f"ROI: {roi:.2f}%")
    print(f"VPN: ${vpn:,.2f}")

    return {
        'ahorro_energia': ahorro_energia,
        'ahorro_perdidas': ahorro_perdidas,
        'total_ingresos': total_ingresos,
        'capex_pv': CAPEX_PV,
        'capex_bc': CAPEX_BC,
        'om_pv': OM_PV,
        'om_bc': OM_BC,
        'payback': payback,
        'roi': roi,
        'vpn': vpn,
        'valor_residual': valor_residual_total
    }
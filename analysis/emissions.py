import numpy as np

def analisis_emisiones(datos_analisis):
    """
    Calcula y muestra la reducción de emisiones contaminantes.
    Retorna un diccionario con los resultados.
    """
    resultados_sin = datos_analisis['resultados_sin']
    resultados_con = datos_analisis['resultados_con']
    system_data = datos_analisis['system_data']
    cache = datos_analisis['cache']

    # Factores de emisión (lb/MWh)
    NOx_factor = 5.06
    SO2_factor = 11.6
    CO2_factor = 2031

    # Energía comprada a la red (MWh/año)
    energia_grid_base = 0.0
    for hora in range(24):
        res = resultados_sin[hora]
        E_by_type = res['E_by_type']
        Eloss_by_type = res['Eloss_by_type']
        for tipo in E_by_type:
            energia_grid_base += E_by_type[tipo] + Eloss_by_type[tipo]
    energia_grid_base_anual = energia_grid_base * 365 / 1000  # MWh

    energia_grid_proy = 0.0
    for hora in range(24):
        res = resultados_con[hora]
        E_by_type = res['E_by_type']
        Eloss_by_type = res['Eloss_by_type']
        E_PV_by_bus = res['E_PV_by_bus']
        for tipo in E_by_type:
            energia_grid_proy += E_by_type[tipo] + Eloss_by_type[tipo]
        energia_grid_proy -= sum(E_PV_by_bus.values())
    energia_grid_proy_anual = energia_grid_proy * 365 / 1000

    # Emisiones
    emisiones_base = {
        'NOx': energia_grid_base_anual * NOx_factor,
        'SO2': energia_grid_base_anual * SO2_factor,
        'CO2': energia_grid_base_anual * CO2_factor
    }
    emisiones_proy = {
        'NOx': energia_grid_proy_anual * NOx_factor,
        'SO2': energia_grid_proy_anual * SO2_factor,
        'CO2': energia_grid_proy_anual * CO2_factor
    }
    reduccion = {k: emisiones_base[k] - emisiones_proy[k] for k in emisiones_base}
    porcentajes = {k: (reduccion[k] / emisiones_base[k] * 100) if emisiones_base[k] > 0 else 0
                   for k in emisiones_base}

    # Mostrar tabla
    print("\n" + "="*100)
    print("ANÁLISIS DE EMISIONES CONTAMINANTES")
    print("="*100)
    print(f"{'Contaminante':<15} {'Base (lb/año)':<20} {'Proyecto (lb/año)':<20} {'Reducción':<20} {'% Reducción':<15}")
    print("-"*100)
    for k in ['NOx', 'SO2', 'CO2']:
        print(f"{k:<15} {emisiones_base[k]:<20,.2f} {emisiones_proy[k]:<20,.2f} {reduccion[k]:<20,.2f} {porcentajes[k]:<15.2f}%")

    # CO2 en toneladas
    co2_ton_base = emisiones_base['CO2'] / 2204.62
    co2_ton_proy = emisiones_proy['CO2'] / 2204.62
    co2_ton_red = reduccion['CO2'] / 2204.62
    print(f"\nCO2 (ton/año): Base={co2_ton_base:,.2f}, Proyecto={co2_ton_proy:,.2f}, Reducción={co2_ton_red:,.2f}")

    return {
        'emisiones_base': emisiones_base,
        'emisiones_proy': emisiones_proy,
        'reduccion': reduccion,
        'porcentajes': porcentajes,
        'energia_grid_base_MWh': energia_grid_base_anual,
        'energia_grid_proy_MWh': energia_grid_proy_anual
    }
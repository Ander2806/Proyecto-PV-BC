import numpy as np

def make_bounds(NC_max, cache, top_pv_buses=None, top_bc_buses=None):
    """
    Genera los límites inferiores (lb) y superiores (ub) para el vector de decisión.
    El vector de decisión tiene la forma:
    [ubicaciones PV (NC_max), tamaños PV (NC_max), ubicaciones BC (NC_max), tamaños BC (NC_max)]
    """
    if top_pv_buses is not None and top_bc_buses is not None:
        lb_pb = np.full(NC_max, float(np.min(top_pv_buses)))
        ub_pb = np.full(NC_max, float(np.max(top_pv_buses)))
        lb_bb = np.full(NC_max, float(np.min(top_bc_buses)))
        ub_bb = np.full(NC_max, float(np.max(top_bc_buses)))
    else:
        lb_pb = np.full(NC_max, 2.0)
        ub_pb = np.full(NC_max, float(cache.nbus))
        lb_bb = np.full(NC_max, 2.0)
        ub_bb = np.full(NC_max, float(cache.nbus))

    lb = np.concatenate([
        lb_pb,                    # ubicaciones PV
        np.full(NC_max, 50.0),    # tamaños PV mínimos
        lb_bb,                    # ubicaciones BC
        np.full(NC_max, 50.0)     # tamaños BC mínimos
    ])
    ub = np.concatenate([
        ub_pb,
        np.full(NC_max, 3000.0),  # tamaños PV máximos
        ub_bb,
        np.full(NC_max, 1500.0)   # tamaños BC máximos
    ])
    return lb, ub

def seed_population(population, n_agents, NC_max, top_pv_buses, top_bc_buses):
    """
    Siembra inteligente: 1/3 con barras LSI, 1/4 con tamaños pequeños.
    """
    if top_pv_buses is not None and top_bc_buses is not None:
        for i in range(n_agents // 3):
            population[i, :NC_max] = np.random.choice(top_pv_buses, NC_max, replace=True).astype(float)
            population[i, 2*NC_max:3*NC_max] = np.random.choice(top_bc_buses, NC_max, replace=True).astype(float)
    for i in range(n_agents // 4):
        population[i, NC_max:2*NC_max] = np.random.uniform(0, 50, NC_max)
        population[i, 3*NC_max:] = np.random.uniform(0, 150, NC_max)
    return population
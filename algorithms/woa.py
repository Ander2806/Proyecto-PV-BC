import numpy as np
import time
from core.objective import objective_function_optimized
from ._utils import make_bounds, seed_population

def woa_algorithm(NC_max, opt_params, PTloss_ref_hourly, cache,
                  n_agents=30, max_iter=50,
                  top_pv_buses=None, top_bc_buses=None):
    """
    Whale Optimization Algorithm (WOA)
    """
    lb, ub = make_bounds(NC_max, cache, top_pv_buses, top_bc_buses)
    nvar = len(lb)

    positions = np.random.uniform(lb, ub, (n_agents, nvar))
    positions = seed_population(positions, n_agents, NC_max, top_pv_buses, top_bc_buses)

    fitness = np.array([objective_function_optimized(positions[i], NC_max,
                         opt_params, PTloss_ref_hourly, cache)
                        for i in range(n_agents)])

    best_idx = np.argmin(fitness)
    global_best = positions[best_idx].copy()
    global_best_fitness = fitness[best_idx]

    convergence = np.zeros(max_iter)
    all_iterations = []

    print("=" * 70)
    print(f"OPTIMIZACIÓN WOA - {cache.system_data.name}")
    print(f"Agentes: {n_agents} | Iteraciones: {max_iter}")
    print("=" * 70)
    start_time = time.time()

    for t in range(max_iter):
        alpha = opt_params.alpha_0 * np.exp(-opt_params.k_woa * t / max_iter)
        r1v = np.random.rand(n_agents)
        r2v = np.random.rand(n_agents)
        p = np.random.rand(n_agents)
        l = (alpha - 1) * np.random.rand(n_agents) + 1

        for i in range(n_agents):
            A = 2 * alpha * r1v[i] - alpha
            C = 2 * r2v[i]

            if p[i] < 0.5:
                if abs(A) >= 1:
                    # Exploración: seleccionar agente aleatorio
                    ri = np.random.randint(n_agents)
                    D = np.abs(C * positions[ri] - positions[i])
                    positions[i] = positions[ri] - A * D
                else:
                    # Explotación: hacia la mejor solución
                    D = np.abs(C * global_best - positions[i])
                    positions[i] = global_best - A * D
            else:
                # Movimiento espiral
                D = np.abs(global_best - positions[i])
                positions[i] = (D * np.exp(opt_params.b_woa * l[i]) *
                                np.cos(l[i] * 2 * np.pi) + global_best)

            positions[i] = np.clip(positions[i], lb, ub)
            f = objective_function_optimized(positions[i], NC_max,
                                             opt_params, PTloss_ref_hourly, cache)
            fitness[i] = f
            if f < global_best_fitness:
                global_best_fitness = f
                global_best = positions[i].copy()

        convergence[t] = global_best_fitness
        all_iterations.append(fitness.copy())

        if (t + 1) % 10 == 0 or t == 0:
            print(f"Iter {t+1:3d} | Best: {global_best_fitness:.6f} M$")

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"COMPLETADO EN {elapsed:.2f}s | MEJOR: {global_best_fitness:.6f} M$")
    print("=" * 70)

    return {
        'best_position': global_best,
        'best_fitness': global_best_fitness,
        'convergence': convergence,
        'elapsed_time': elapsed,
        'all_iterations': all_iterations
    }
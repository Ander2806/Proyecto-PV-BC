import numpy as np
import time
from core.objective import objective_function_optimized
from ._utils import make_bounds, seed_population

def pso_algorithm(NC_max, opt_params, PTloss_ref_hourly, cache,
                  n_agents=30, max_iter=50,
                  top_pv_buses=None, top_bc_buses=None):
    """
    Particle Swarm Optimization (PSO)
    """
    lb, ub = make_bounds(NC_max, cache, top_pv_buses, top_bc_buses)
    nvar = len(lb)

    positions = np.random.uniform(lb, ub, (n_agents, nvar))
    positions = seed_population(positions, n_agents, NC_max, top_pv_buses, top_bc_buses)
    velocities = np.zeros((n_agents, nvar))

    # Evaluación inicial
    fitness = np.array([objective_function_optimized(positions[i], NC_max,
                         opt_params, PTloss_ref_hourly, cache)
                        for i in range(n_agents)])

    personal_best = positions.copy()
    personal_best_fitness = fitness.copy()
    best_idx = np.argmin(fitness)
    global_best = positions[best_idx].copy()
    global_best_fitness = fitness[best_idx]

    convergence = np.zeros(max_iter)
    all_iterations = []

    print("=" * 70)
    print(f"OPTIMIZACIÓN PSO - {cache.system_data.name}")
    print(f"Agentes: {n_agents} | Iteraciones: {max_iter}")
    print("=" * 70)
    start_time = time.time()

    for t in range(max_iter):
        k = t / max_iter
        # Parámetros dinámicos
        C1 = opt_params.cmax + (opt_params.cmin - opt_params.cmax) * k
        C2 = opt_params.cmin + (opt_params.cmax - opt_params.cmin) * k
        W = opt_params.wmax - (opt_params.wmax - opt_params.wmin) * k

        r1 = np.random.rand(n_agents, nvar)
        r2 = np.random.rand(n_agents, nvar)

        velocities = (W * velocities
                      + C1 * r1 * (personal_best - positions)
                      + C2 * r2 * (global_best - positions))
        positions = np.clip(positions + velocities, lb, ub)

        for i in range(n_agents):
            f = objective_function_optimized(positions[i], NC_max,
                                             opt_params, PTloss_ref_hourly, cache)
            fitness[i] = f
            if f < personal_best_fitness[i]:
                personal_best_fitness[i] = f
                personal_best[i] = positions[i].copy()
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
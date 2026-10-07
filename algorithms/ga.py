import numpy as np
import time
from core.objective import objective_function_optimized
from ._utils import make_bounds, seed_population

def ga_algorithm(NC_max, opt_params, PTloss_ref_hourly, cache,
                 n_agents=30, max_iter=50,
                 top_pv_buses=None, top_bc_buses=None):
    """
    Algoritmo Genético con SBX crossover y mutación polinomial.
    """
    lb, ub = make_bounds(NC_max, cache, top_pv_buses, top_bc_buses)
    nvar = len(lb)
    pop_size = n_agents

    # Parámetros GA
    cr = opt_params.ga_crossover_rate
    mr = opt_params.ga_mutation_rate
    ts = opt_params.ga_tournament_size
    ec = opt_params.ga_elitism_count
    eta_c = 20.0   # índice de distribución para SBX
    eta_m = 20.0   # índice de distribución para mutación polinomial

    # Inicializar población
    population = np.random.uniform(lb, ub, (pop_size, nvar))
    population = seed_population(population, pop_size, NC_max, top_pv_buses, top_bc_buses)

    fitness = np.array([objective_function_optimized(population[i], NC_max,
                         opt_params, PTloss_ref_hourly, cache)
                        for i in range(pop_size)])

    best_idx = np.argmin(fitness)
    global_best = population[best_idx].copy()
    global_best_fitness = fitness[best_idx]

    convergence = np.zeros(max_iter)
    all_iterations = []

    def tournament_selection(fit):
        """Selección por torneo binario."""
        candidates = np.random.choice(pop_size, ts, replace=False)
        return candidates[np.argmin(fit[candidates])]

    def sbx_crossover(p1, p2):
        """Simulated Binary Crossover (SBX)."""
        c1, c2 = p1.copy(), p2.copy()
        for j in range(nvar):
            if np.random.rand() <= 0.5 and abs(p1[j] - p2[j]) > 1e-14:
                y1, y2 = min(p1[j], p2[j]), max(p1[j], p2[j])
                yl, yu = lb[j], ub[j]
                rand = np.random.rand()
                # Para c1
                beta = 1.0 + (2.0 * (y1 - yl) / (y2 - y1)) if (y2 - y1) > 1e-14 else 1.0
                alpha = 2.0 - beta ** (-(eta_c + 1.0))
                if rand <= 1.0 / alpha:
                    beta_q = (rand * alpha) ** (1.0 / (eta_c + 1.0))
                else:
                    beta_q = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta_c + 1.0))
                c1[j] = np.clip(0.5 * ((y1 + y2) - beta_q * (y2 - y1)), yl, yu)

                # Para c2
                beta = 1.0 + (2.0 * (yu - y2) / (y2 - y1)) if (y2 - y1) > 1e-14 else 1.0
                alpha = 2.0 - beta ** (-(eta_c + 1.0))
                rand = np.random.rand()
                if rand <= 1.0 / alpha:
                    beta_q = (rand * alpha) ** (1.0 / (eta_c + 1.0))
                else:
                    beta_q = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta_c + 1.0))
                c2[j] = np.clip(0.5 * ((y1 + y2) + beta_q * (y2 - y1)), yl, yu)
        return c1, c2

    def polynomial_mutation(ind):
        """Mutación polinomial."""
        mut = ind.copy()
        for j in range(nvar):
            if np.random.rand() < mr:
                y, yl, yu = mut[j], lb[j], ub[j]
                delta1 = (y - yl) / (yu - yl + 1e-14)
                delta2 = (yu - y) / (yu - yl + 1e-14)
                rand = np.random.rand()
                if rand < 0.5:
                    val = 2.0 * rand + (1.0 - 2.0 * rand) * ((1.0 - delta1) ** (eta_m + 1.0))
                    delta_q = val ** (1.0 / (eta_m + 1.0)) - 1.0
                else:
                    val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * ((1.0 - delta2) ** (eta_m + 1.0))
                    delta_q = 1.0 - val ** (1.0 / (eta_m + 1.0))
                mut[j] = np.clip(y + delta_q * (yu - yl), yl, yu)
        return mut

    print("=" * 70)
    print(f"OPTIMIZACIÓN GA - {cache.system_data.name}")
    print(f"Población: {pop_size} | Generaciones: {max_iter}")
    print(f"P_cruce: {cr} | P_mut: {mr} | Torneo: {ts} | Élites: {ec}")
    print("=" * 70)
    start_time = time.time()

    for t in range(max_iter):
        # Elitismo: guardar los mejores
        elite_idx = np.argsort(fitness)[:ec]
        elites = population[elite_idx].copy()
        elite_fit = fitness[elite_idx].copy()

        new_pop = np.zeros_like(population)
        new_fit = np.full(pop_size, np.inf)

        # Copiar élites
        for k in range(ec):
            new_pop[k] = elites[k]
            new_fit[k] = elite_fit[k]

        idx = ec
        while idx < pop_size:
            p1 = population[tournament_selection(fitness)]
            p2 = population[tournament_selection(fitness)]

            if np.random.rand() < cr:
                c1, c2 = sbx_crossover(p1, p2)
            else:
                c1, c2 = p1.copy(), p2.copy()

            c1 = polynomial_mutation(c1)
            c2 = polynomial_mutation(c2)

            new_pop[idx] = c1
            new_fit[idx] = objective_function_optimized(c1, NC_max,
                                                        opt_params, PTloss_ref_hourly, cache)
            idx += 1
            if idx < pop_size:
                new_pop[idx] = c2
                new_fit[idx] = objective_function_optimized(c2, NC_max,
                                                            opt_params, PTloss_ref_hourly, cache)
                idx += 1

        population = new_pop
        fitness = new_fit
        bi = np.argmin(fitness)
        if fitness[bi] < global_best_fitness:
            global_best_fitness = fitness[bi]
            global_best = population[bi].copy()

        convergence[t] = global_best_fitness
        all_iterations.append(fitness.copy())

        if (t + 1) % 10 == 0 or t == 0:
            print(f"Gen {t+1:3d} | Best: {global_best_fitness:.6f} M$")

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
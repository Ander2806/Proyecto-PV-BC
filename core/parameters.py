from dataclasses import dataclass
import numpy as np
import json

@dataclass
class SystemParameters:
    S_base: float = 100_000   # kVA
    V_base: float = 12.66     # kV
    Z_base: float = None
    I_base: float = None

    def __post_init__(self):
        self.Z_base = 1000 * (self.V_base ** 2) / self.S_base
        self.I_base = self.S_base / (np.sqrt(3) * self.V_base)

@dataclass
class OptimizationParameters:
    # Parámetros económicos y técnicos
    T_life: int = 20
    DG_cost: float = 3985          # USD/kW
    G_r: float = 1.0               # Factor de degradación
    LF: float = 0.8                # Factor de carga
    cost_OM_DG: float = 0.01207    # USD/kWh
    tiempo_vida_DG: int = 20       # años
    Cost_BC_inst: float = 1600     # USD/banco
    Cost_BC_cap: float = 25        # USD/kVAR
    cost_OM_BC: float = 300        # USD/año por banco
    tiempo_vida_BC: int = 10       # años
    umbral_pv: float = 50          # kW mínimo para considerar PV
    umbral_bc: float = 150         # kVAR mínimo para considerar BC
    # Parámetros WOA
    b_woa: float = 1.0
    alpha_0: float = 2.0
    k_woa: float = 4.0
    # Parámetros PSO
    wmin: float = 0.4
    wmax: float = 0.9
    cmin: float = 0.5
    cmax: float = 2.5
    # Parámetros GA
    ga_crossover_rate: float = 0.8
    ga_mutation_rate: float = 0.05
    ga_tournament_size: int = 3
    ga_elitism_count: int = 2

    @classmethod
    def from_json(cls, path: str):
        """Carga los parámetros desde un archivo JSON."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)
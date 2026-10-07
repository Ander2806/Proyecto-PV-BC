import numpy as np
import pandas as pd
import os

class SystemCache:
    """
    Precalcula todas las estructuras estáticas necesarias para acelerar
    el flujo de potencia y la función objetivo.
    """
    def __init__(self, sys_params, system_data):
        self.sys_params = sys_params
        self.system_data = system_data

        self.R = system_data.line_data[:, 2] / sys_params.Z_base
        self.X = system_data.line_data[:, 3] / sys_params.Z_base
        self.nbus = system_data.nbus
        self.nline = system_data.nline

        self.from_bus = system_data.line_data[:, 0].astype(int) - 1
        self.to_bus   = system_data.line_data[:, 1].astype(int) - 1
        self.line_idx = system_data.line_data[:, 4].astype(int) - 1

        self.Z_line = self.R + 1j * self.X
        self.bus_to_category_idx = system_data.get_bus_category_map()
        self.BIBC = self._compute_BIBC()

        # Rutas absolutas para perfiles
        profiles_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'profiles'))
        demand_file = os.path.join(profiles_dir, 'demand_curves.csv')
        prices_file = os.path.join(profiles_dir, 'energy_prices.csv')

        self.demand_factors, self.pv_factor, self.cost_energy_hourly = self._load_profiles(demand_file, prices_file)
        self._precompute_hourly_demand()

    def _compute_BIBC(self):
        BIBC = np.zeros((self.nbus - 1, self.nline))
        for i in range(self.nline):
            fb = self.from_bus[i]
            tb = self.to_bus[i]
            li = self.line_idx[i]
            if fb > 0:
                BIBC[:, li] = BIBC[:, fb - 1]
            BIBC[tb - 1, li] = 1
        return BIBC

    def _load_profiles(self, demand_file, prices_file):
        demand = pd.read_csv(demand_file).to_numpy()
        prices = pd.read_csv(prices_file).to_numpy()
        pv_factor = demand[:, 1]
        demand_factors = demand[:, 2:5]
        return demand_factors, pv_factor, prices

    def _precompute_hourly_demand(self):
        self.demand_h = np.zeros((24, self.nbus, 2))
        cat_idx = self.bus_to_category_idx[1:]
        for h in range(24):
            factors = self.demand_factors[h, cat_idx]
            self.demand_h[h, 1:, 0] = self.system_data.bus_data_base[1:, 1] * factors
            self.demand_h[h, 1:, 1] = self.system_data.bus_data_base[1:, 2] * factors
        self.Pt_dem_h = np.sum(self.demand_h[:, 1:, 0], axis=1)
        self.Qt_dem_h = np.sum(self.demand_h[:, 1:, 1], axis=1)
import json
import numpy as np
import pandas as pd
import os

class SystemData:
    """
    Carga los datos de la red (líneas, barras y categorías de consumo)
    desde archivos CSV/JSON ubicados en data/networks/<system_type>/.
    """
    def __init__(self, system_type='IEEE33', data_dir=None):
        self.system_type = system_type
        if data_dir is None:
            # Determinar la raíz del proyecto (subir dos niveles desde este archivo)
            self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'networks'))
        else:
            self.data_dir = data_dir
        self._load_network_data()
        self._load_bus_categories()
        self.nbus = self.bus_data_base.shape[0]
        self.nline = self.line_data.shape[0]
        self.name = system_type

    def _load_network_data(self):
        net_dir = os.path.join(self.data_dir, self.system_type.lower())
        line_file = os.path.join(net_dir, 'line_data.csv')
        bus_file = os.path.join(net_dir, 'bus_data.csv')
        self.line_data = pd.read_csv(line_file).to_numpy()
        self.bus_data_base = pd.read_csv(bus_file).to_numpy()

    def _load_bus_categories(self):
        net_dir = os.path.join(self.data_dir, self.system_type.lower())
        cat_file = os.path.join(net_dir, 'bus_categories.json')
        with open(cat_file, 'r') as f:
            cats = json.load(f)
        self.residential_buses = np.array(cats['residential'], dtype=int)
        self.commercial_buses = np.array(cats['commercial'], dtype=int)
        self.industrial_buses = np.array(cats['industrial'], dtype=int)

        self.bus_categories = {}
        for b in self.residential_buses:
            self.bus_categories[b] = 'residential'
        for b in self.commercial_buses:
            self.bus_categories[b] = 'commercial'
        for b in self.industrial_buses:
            self.bus_categories[b] = 'industrial'

    def get_bus_category_map(self):
        mapping = np.zeros(self.nbus, dtype=int)
        for b in self.residential_buses:
            mapping[b-1] = 0
        for b in self.commercial_buses:
            mapping[b-1] = 1
        for b in self.industrial_buses:
            mapping[b-1] = 2
        return mapping
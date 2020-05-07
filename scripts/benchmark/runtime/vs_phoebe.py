"""
2.0
20324
7544
-------------------------------
5.0
3376
1132
-------------------------------
7.0
1604
564
-------------------------------
10.0
848
288
-------------------------------
"""

import time
import json
import numpy as np

from elisa.binary_system.system import BinarySystem
from elisa.observer.observer import Observer


PASSBAND = ["Generic.Bessell.B", "Generic.Bessell.V"]


def get_params(eccentricity, discretization_factor):
    return {
        "system": {
            "inclination": 85.0,
            "period": 3.0,
            "argument_of_periastron": 210.0,
            "gamma": 0.0,
            "eccentricity": eccentricity,
            "primary_minimum_time": 0.0,
            "phase_shift": 0.0
        },
        "primary": {
            "mass": 2.0,
            "surface_potential": 5.0,
            "synchronicity": 1.0,
            "t_eff": 5500,
            "gravity_darkening": 0.32,
            "discretization_factor": discretization_factor,
            "albedo": 0.6,
            "metallicity": 0.0,
        },
        "secondary": {
            "mass": 1.0,
            "surface_potential": 5.0,
            "synchronicity": 1.0,
            "t_eff": 5500,
            "gravity_darkening": 0.32,
            "albedo": 0.6,
            "metallicity": 0.0,
        }
    }


def timeit(f):
    def timed(*args, **kw):
        ts = time.time()
        f(*args, **kw)
        te = time.time()
        return te - ts
    return timed


def get_elisa_binary_observer(passband, eccentricity, discretization_factor):
    params = get_params(eccentricity=eccentricity, discretization_factor=discretization_factor)
    bs_system = BinarySystem.from_json(params, _verify=False, _kind_of="std")
    return Observer(passband, system=bs_system)


def run_observation(observer, phases):
    observer.observe.lc(phases=phases)


def main():
    # elisa runtime test ################
    test_runs = 1
    result = {
        "elisa": {
            "circular": dict(),
            "eccentric": dict()
        }
    }

    for eccentricity in [0]:
        orbit = "circular" if eccentricity == 0 else "eccentric"
        for alpha in [2, 5, 7, 10]:
            observer = get_elisa_binary_observer(PASSBAND[0], eccentricity=eccentricity, discretization_factor=alpha)
            result["elisa"][orbit][str(alpha)] = dict()
            for n_phases in [20, 50, 100, 150, 200, 250, 300]:
                phases = np.linspace(-0.6, 0.6, n_phases, endpoint=True)
                runtime = 0
                for _ in range(test_runs):
                    runtime += timeit(run_observation)(observer, phases)
                result["elisa"][orbit][str(alpha)][str(n_phases)] = runtime / test_runs

    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    main()


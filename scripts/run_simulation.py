#!/usr/bin/env python
"""Entry point: python run_simulation.py --scenario {normal,extended_green,emergency} [--gui]"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sumolib
import traci

from scenarios import SCENARIOS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE_DIR, "..", "intersection.sumocfg")
CFG_LIGHT = os.path.join(BASE_DIR, "..", "intersection_light.sumocfg")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=sorted(SCENARIOS.keys()), default="normal")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--light", action="store_true",
                         help="use the ~10-vehicle demand file (req #1 GUI viewing only)")
    args = parser.parse_args()

    binary = sumolib.checkBinary("sumo-gui" if args.gui else "sumo")
    cfg = CFG_LIGHT if args.light else CFG
    traci.start([binary, "-c", cfg, "--no-step-log", "true"])
    # Activate the editable program from routes/intersection.tls.add.xml (req #5)
    # instead of the fixed one netconvert embedded in the .net.xml.
    traci.trafficlight.setProgram("TL1", "1")

    try:
        departed_total = SCENARIOS[args.scenario]()
    finally:
        traci.close()

    print(f"Total vehicles departed: {departed_total}")
    if not args.light:
        assert 20 <= departed_total <= 60, f"expected 20-50 vehicles inserted, got {departed_total}"
    print("OK")


if __name__ == "__main__":
    main()

"""Three demo scenarios exercising the TL1 traffic light controller (req #8)."""
import traci
import tls_control as tls

PRINT_EVERY = 10  # seconds


def _step_loop(on_step=None):
    last_print = -PRINT_EVERY
    total_departed = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        total_departed += traci.simulation.getDepartedNumber()
        t = traci.simulation.getTime()
        tls.tick("TL1")
        if on_step:
            on_step(t)
        if t - last_print >= PRINT_EVERY:
            last_print = t
            state = tls.get_traffic_light_state("TL1")
            print(f"t={t:6.0f}s  vehicles={traci.vehicle.getIDCount():3d}  "
                  f"phase={state['phase']} state={state['state']}")
    return total_departed


def run_normal():
    """Scenario 1: default program runs untouched."""
    return _step_loop()


def run_extended_green():
    """Scenario 2: extend the currently active phase by 20s at t=100s."""
    applied = {"done": False}

    def on_step(t):
        if not applied["done"] and t >= 100:
            print(f"t={t:6.0f}s  >>> extending current phase by 20s")
            tls.extend_current_phase("TL1", 20)
            applied["done"] = True

    return _step_loop(on_step)


def run_emergency():
    """Scenario 3: abnormal/emergency override - force all-red for 15s at t=150s."""
    applied = {"done": False}

    def on_step(t):
        if not applied["done"] and t >= 150:
            print(f"t={t:6.0f}s  >>> EMERGENCY: set_traffic_light('TL1','RED',15)")
            tls.set_traffic_light("TL1", "RED", 15)
            applied["done"] = True

    return _step_loop(on_step)


SCENARIOS = {
    "normal": run_normal,
    "extended_green": run_extended_green,
    "emergency": run_emergency,
}

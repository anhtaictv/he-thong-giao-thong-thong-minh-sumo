"""TraCI wrapper for controlling the TL1 traffic light.

Exposes the simple command shape from the assignment (req #9):
set_traffic_light("TL1", "GREEN", 30) — a stub ready for an external agent
(Agent Guard) to call once its real command schema is defined.
"""
import traci

_forced_until = {}


def get_traffic_light_state(tls_id="TL1"):
    return {
        "state": traci.trafficlight.getRedYellowGreenState(tls_id),
        "phase": traci.trafficlight.getPhase(tls_id),
        "program": traci.trafficlight.getProgram(tls_id),
        "next_switch": traci.trafficlight.getNextSwitch(tls_id),
    }


def set_traffic_light(tls_id, color, duration=0):
    """External command API, e.g. set_traffic_light("TL1", "GREEN", 30).

    ponytail: single-axis simplification, not per-approach control. RED/YELLOW
    force every controlled link to that color for `duration` seconds (safe
    all-stop, e.g. emergency vehicle preemption). GREEN restores the normal
    timed program. Per-approach commands are future work once Agent Guard
    defines its real command schema.
    """
    color = color.upper()
    if color == "GREEN":
        traci.trafficlight.setProgram(tls_id, "1")
        _forced_until.pop(tls_id, None)
    elif color in ("RED", "YELLOW"):
        n = len(traci.trafficlight.getRedYellowGreenState(tls_id))
        traci.trafficlight.setRedYellowGreenState(tls_id, ("r" if color == "RED" else "y") * n)
        _forced_until[tls_id] = traci.simulation.getTime() + duration
    else:
        raise ValueError(f"unknown color: {color}")


def extend_current_phase(tls_id, extra_seconds):
    """Add extra_seconds to whatever phase is active right now (req #5)."""
    remaining = traci.trafficlight.getNextSwitch(tls_id) - traci.simulation.getTime()
    traci.trafficlight.setPhaseDuration(tls_id, remaining + extra_seconds)


def tick(tls_id="TL1"):
    """Call once per simulation step; auto-reverts a forced RED/YELLOW back to
    the normal program once its commanded duration has elapsed."""
    until = _forced_until.get(tls_id)
    if until is not None and traci.simulation.getTime() >= until:
        traci.trafficlight.setProgram(tls_id, "1")
        del _forced_until[tls_id]

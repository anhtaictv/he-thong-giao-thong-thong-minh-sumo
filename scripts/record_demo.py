"""Capture SUMO-GUI screenshots via TraCI's built-in gui.screenshot() and
assemble them into a short demo GIF (req #10 media). Uses the light demand
config so the environment's GUI rendering stays reliable; runs 1 sim-second
per step and plays the GIF back at ~1s/frame so its length matches the
simulated duration (roughly real-time).

If the sumo-gui connection drops partway (this sandbox's GUI has been
unreliable under sustained load), whatever frames were captured before the
failure are still assembled into a (shorter) GIF instead of losing the run.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sumolib
import traci
from PIL import Image

import tls_control as tls

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE, "..", "intersection_light.sumocfg")
MEDIA_DIR = os.path.join(BASE, "..", "media")
FRAMES_DIR = os.path.join(MEDIA_DIR, "frames")
END_TIME = 150
EXTEND_AT = 40
EMERGENCY_AT = 90

# t -> label, used to also save a few standalone named screenshots
HIGHLIGHTS = {
    1: "01_start",
    25: "02_ns_green",
    45: "03_extended_green",
    70: "04_ew_green",
    91: "05_emergency_all_red",
    100: "06_all_red_hold",
    108: "07_resumed",
}


def main():
    os.makedirs(FRAMES_DIR, exist_ok=True)
    binary = sumolib.checkBinary("sumo-gui")
    traci.start([binary, "-c", CFG, "--no-step-log", "true", "--start", "true"])
    traci.trafficlight.setProgram("TL1", "1")
    traci.gui.setZoom("View #0", 600)

    frame_paths = []
    extended = False
    emergency = False
    try:
        while traci.simulation.getTime() < END_TIME:
            traci.simulationStep()
            t = int(traci.simulation.getTime())

            tls.tick("TL1")
            if not extended and t >= EXTEND_AT:
                tls.extend_current_phase("TL1", 15)
                extended = True
            if not emergency and t >= EMERGENCY_AT:
                tls.set_traffic_light("TL1", "RED", 10)
                emergency = True

            frame_path = os.path.join(FRAMES_DIR, f"frame_{t:04d}.png")
            traci.gui.screenshot("View #0", frame_path)
            frame_paths.append(frame_path)

            if t in HIGHLIGHTS:
                highlight_path = os.path.join(MEDIA_DIR, f"{HIGHLIGHTS[t]}.png")
                traci.gui.screenshot("View #0", highlight_path)
    except traci.exceptions.FatalTraCIError as exc:
        print(f"GUI connection dropped at t={traci.simulation.getTime()}: {exc}")
    finally:
        try:
            traci.close()
        except Exception:
            pass

    print(f"Captured {len(frame_paths)} frames")
    if not frame_paths:
        print("No frames captured, nothing to assemble.")
        return

    frames = [Image.open(p) for p in frame_paths]
    gif_path = os.path.join(MEDIA_DIR, "demo.gif")
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=1000, loop=0)
    print(f"Wrote {gif_path} ({len(frames)} frames, ~{len(frames)}s playback)")


if __name__ == "__main__":
    main()

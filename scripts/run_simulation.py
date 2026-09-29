#!/usr/bin/env python
"""Chạy mô phỏng giao lộ TL1.

Ví dụ:
  python scripts/run_simulation.py --scenario normal
  python scripts/run_simulation.py --scenario extended_green
  python scripts/run_simulation.py --scenario dangerous            # guard chặn lệnh nguy hiểm
  python scripts/run_simulation.py --scenario dangerous --unsafe   # tắt guard để thấy hậu quả
  python scripts/run_simulation.py --scenario emergency --gui
  python scripts/run_simulation.py --scenario interactive --gui    # chờ lệnh qua TCP :9000
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sumolib
import traci

import command_interface as ci
import scenarios

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE_DIR, "..", "intersection.sumocfg")
CFG_DEMO = os.path.join(BASE_DIR, "..", "intersection_light.sumocfg")
VIEW_SETTINGS = os.path.join(BASE_DIR, "view_settings.xml")
MIN_VEHICLES, MAX_VEHICLES = 20, 50      # yêu cầu #3


def build_cmd(gui=False, demo=False, delay=100, extra=()):
    binary = sumolib.checkBinary("sumo-gui" if gui else "sumo")
    cmd = [binary, "-c", CFG_DEMO if demo else CFG, "--no-step-log", "true",
           "--collision.check-junctions", "true", "--collision.action", "warn"]
    if gui:
        cmd += ["--start", "true", "--quit-on-end", "true", "--delay", str(delay),
                "--gui-settings-file", VIEW_SETTINGS]
    return cmd + list(extra)


def main():
    p = argparse.ArgumentParser(description="Mô phỏng giao lộ thông minh TL1 (SUMO + TraCI)")
    p.add_argument("--scenario", choices=list(scenarios.SCENARIOS), default="normal")
    p.add_argument("--gui", action="store_true", help="mở SUMO-GUI")
    p.add_argument("--light", "--demo", dest="demo", action="store_true",
                   help="dùng intersection_light.sumocfg (36 xe dồn trong ~4 phút, hợp để xem/quay video)")
    p.add_argument("--delay", type=int, default=100, help="độ trễ mỗi bước của SUMO-GUI (ms)")
    p.add_argument("--server", action="store_true",
                   help="bật cổng nhận lệnh TCP (tự bật với --scenario interactive)")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--realtime", action="store_true", help="1 giây mô phỏng = 1 giây thực")
    p.add_argument("--max-time", type=float, default=None, help="dừng tại thời điểm này (giây)")
    p.add_argument("--verbose", action="store_true", help="in mọi lần đổi pha đèn")
    p.add_argument("--unsafe", action="store_true",
                   help="TẮT safety guard (chỉ để minh họa hậu quả của lệnh nguy hiểm)")
    args = p.parse_args()

    interactive = args.scenario == "interactive"
    use_server = args.server or interactive
    max_time = args.max_time if args.max_time is not None else (1800 if interactive else None)
    realtime = args.realtime or (interactive and not args.gui)

    ci.enable_guard(not args.unsafe)
    if args.unsafe:
        print("*** CẢNH BÁO: safety guard đang TẮT (--unsafe) ***")

    traci.start(build_cmd(args.gui, args.demo, args.delay))
    # Kích hoạt chương trình đèn chỉnh sửa được (routes/intersection.tls.add.xml, yêu cầu #5)
    traci.trafficlight.setProgram("TL1", "1")
    if args.gui:
        traci.gui.setOffset("View #0", 200, 200)   # phóng to vào giao lộ TL1
        traci.gui.setZoom("View #0", 300)
    server = ci.CommandServer(port=args.port) if use_server else None
    try:
        stats = scenarios.run(args.scenario, server=server, realtime=realtime,
                              max_time=max_time, verbose=args.verbose)
    except traci.exceptions.FatalTraCIError:
        print("SUMO đã đóng (cửa sổ GUI bị tắt?) — kết thúc.")
        return
    finally:
        if server:
            server.close()
        try:
            traci.close()
        except Exception:
            pass

    print("\n=== Kết quả ===")
    for k, v in stats.items():
        print(f"  {k:15s}: {v}")
    if not interactive and max_time is None:
        ok = MIN_VEHICLES <= stats["departed"] <= MAX_VEHICLES + 1   # +1: xe cứu thương
        print(f"  Số xe tham gia {stats['departed']} trong khoảng {MIN_VEHICLES}-{MAX_VEHICLES}: "
              f"{'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    main()

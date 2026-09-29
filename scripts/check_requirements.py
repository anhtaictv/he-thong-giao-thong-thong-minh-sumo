#!/usr/bin/env python
"""Tự kiểm tra các yêu cầu #1-#9 bằng mô phỏng headless. In bảng ĐẠT / KHÔNG ĐẠT.

    python scripts/check_requirements.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import traci

import command_interface as ci
import safety_guard
import tls_control as tls
from run_simulation import build_cmd

results = []


def check(req, desc, cond, detail=""):
    results.append((req, desc, bool(cond), detail))


def step(n=1):
    for _ in range(n):
        traci.simulationStep()
        tls.tick("TL1")


def start(demo=False):
    tls.reset()
    ci.enable_guard(True)
    traci.start(build_cmd(demo=demo))
    traci.trafficlight.setProgram("TL1", "1")


def main():
    # ---- #1: có sumo và sumo-gui
    import subprocess
    import sumolib
    vers = []
    for b in ("sumo", "sumo-gui"):
        path = sumolib.checkBinary(b)
        ok = os.path.exists(path) or os.path.exists(path + ".exe")
        vers.append(ok)
    out = subprocess.run([sumolib.checkBinary("sumo"), "--version"], capture_output=True, text=True).stdout
    check(1, "Cài đặt SUMO / SUMO-GUI", all(vers), out.splitlines()[0] if out else "")

    # ---- #2, #3, #4: mạng, số xe, chu kỳ đèn tự động (không can thiệp)
    start()
    edges = set(traci.edge.getIDList())
    need = {f"{d}_{io}" for d in "NSEW" for io in ("in", "out")}
    check(2, "Giao lộ 4 hướng Bắc-Nam-Đông-Tây (8 cạnh vào/ra, 1 đèn TL1)",
          need <= edges and traci.trafficlight.getIDList() == ("TL1",),
          f"cạnh={sorted(e for e in edges if not e.startswith(':'))}")
    seen_states, departed, transitions_ok = set(), 0, True
    prev = traci.trafficlight.getRedYellowGreenState("TL1")
    while traci.simulation.getMinExpectedNumber() > 0:
        step()
        departed += traci.simulation.getDepartedNumber()
        cur = traci.trafficlight.getRedYellowGreenState("TL1")
        seen_states.update(set(cur))
        if any(a in "Gg" and b == "r" for a, b in zip(prev, cur)):
            transitions_ok = False
        prev = cur
    traci.close()
    check(3, "Có 20-50 xe tham gia mô phỏng", 20 <= departed <= 50, f"{departed} xe")
    check(4, "Đèn Đỏ-Vàng-Xanh tự động, không chuyển Xanh->Đỏ đột ngột",
          {"G", "y", "r"} <= seen_states and transitions_ok, f"ký tự gặp: {sorted(seen_states)}")

    # ---- #5, #6, #7, #9
    start()
    step(5)
    st = tls.get_traffic_light_state("TL1")
    check(6, "Python + TraCI đọc được trạng thái đèn",
          st["state"] == "GGgrrrGGgrrr" and st["directions"]["N"] == "GREEN", str(st["directions"]))

    before = traci.trafficlight.getNextSwitch("TL1")
    tls.extend_current_phase("TL1", 20)
    after = traci.trafficlight.getNextSwitch("TL1")
    check(5, "Đổi thời gian pha khi đang chạy (extend_current_phase)", after - before == 20,
          f"next_switch {before} -> {after}")

    r = tls.set_cycle("TL1", 30, 50)
    phases = traci.trafficlight.getAllProgramLogics("TL1")
    logic = [l for l in phases if l.programID == "1"][0]
    check(5, "Đổi chu kỳ đèn khi đang chạy (set_cycle)",
          logic.phases[0].duration == 30 and logic.phases[3].duration == 50, r["message"])

    # set_traffic_light("TL1","GREEN",30) khi đang xanh Bắc-Nam -> xanh đúng 30s
    t0 = traci.simulation.getTime()
    r = ci.execute('set_traffic_light("TL1","GREEN",30)')
    green_until = None
    for _ in range(60):
        step()
        if "G" not in traci.trafficlight.getRedYellowGreenState("TL1")[:3]:
            green_until = traci.simulation.getTime()
            break
    check(9, 'Nhận lệnh văn bản set_traffic_light("TL1","GREEN",30) -> xanh đúng 30s',
          r["ok"] and green_until is not None and abs((green_until - t0) - 31) <= 1,
          f"{r.get('message')}; hết xanh sau {green_until - t0 if green_until else '?'}s")

    # đổi sang hướng khác phải qua Vàng + Đỏ toàn phần
    r = tls.set_traffic_light("TL1", "GREEN", 15, "E")
    seq = []
    for _ in range(10):
        s = traci.trafficlight.getRedYellowGreenState("TL1")
        if not seq or seq[-1] != s:
            seq.append(s)
        step()
    check(7, "Python gửi lệnh đổi trạng thái đèn (GREEN hướng Đông) có Vàng + Đỏ chuyển tiếp",
          r["ok"] and any("y" in s for s in seq) and "rrrGGGrrrrrr" in seq, " -> ".join(seq))

    r = ci.execute('set_traffic_light("TL1","RED",10)')
    step(6)
    check(7, "Lệnh RED 10s: đỏ toàn bộ giao lộ", r["ok"] and
          traci.trafficlight.getRedYellowGreenState("TL1") == "r" * 12)

    # ---- #8 tình huống nguy hiểm: guard phải chặn
    bad = [
        'set_state("TL1","GGGGGGGGGGGG",20)',
        'set_traffic_light("TL1","GREEN",999)',
        'set_traffic_light("TL9","GREEN",30)',
        'set_traffic_light("TL1","BLUE",30)',
        '__import__("os").system("echo hacked")',
    ]
    rejected = [not ci.execute(c)["ok"] for c in bad]
    check(8, "Lệnh bất thường/nguy hiểm bị từ chối (5/5)", all(rejected), f"{sum(rejected)}/5 bị từ chối")
    check(8, "Phát hiện xung đột khi mọi hướng cùng xanh",
          bool(safety_guard.find_conflicts("GGGGGGGGGGGG")) and not safety_guard.find_conflicts("GGgrrrGGgrrr"))
    r = ci.execute('{"command":"get_traffic_light_state","args":["TL1"]}')
    check(9, "Nhận lệnh dạng JSON", r["ok"] and "state" in r)
    traci.close()

    print(f"\n{'#':>2}  {'Kết quả':9s} Nội dung")
    for req, desc, ok, detail in results:
        print(f"{req:>2}  {'ĐẠT' if ok else 'KHÔNG ĐẠT':9s} {desc}" + (f"\n             ({detail})" if detail else ""))
    failed = [r for r in results if not r[2]]
    print(f"\nTổng: {len(results) - len(failed)}/{len(results)} kiểm tra đạt")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

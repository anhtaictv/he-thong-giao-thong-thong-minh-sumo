"""Các tình huống minh họa (yêu cầu #8) + vòng lặp mô phỏng dùng chung.

  normal          — Giao thông bình thường: chu kỳ đèn tự động, không can thiệp.
  extended_green  — Tăng thời gian đèn xanh: kéo dài pha xanh, lệnh GREEN 30s, đổi chu kỳ.
  dangerous       — Lệnh điều khiển bất thường / nguy hiểm: bật xanh mọi hướng, xanh->đỏ
                    đột ngột, thời gian vô lý, sai ID đèn, sai màu, chèn mã... -> safety guard
                    chặn (với --unsafe: cho chạy để thấy nguy cơ xung đột).
  emergency       — Xe cứu thương từ hướng Đông: chỉ mở xanh hướng Đông, sau đó đỏ toàn bộ.
  demo            — Gộp các tình huống trên trong ~4 phút để quay video (record_demo.py).
  interactive     — Không có lệnh định sẵn, chờ lệnh từ bên ngoài qua TCP (Agent Guard).

Mọi lệnh trong kịch bản được gửi dưới DẠNG VĂN BẢN qua command_interface.execute(),
giống hệt cách Agent Guard sẽ gửi sau này.
"""
import time

import traci

import command_interface as ci
import safety_guard
import tls_control as tls

TLS_ID = "TL1"
NEAR_JUNCTION = 50.0   # m — xe cách vạch dừng <= 50m coi là "đang tới giao lộ"

SCENARIOS = {
    "normal": {
        "title": "Giao thông bình thường (chu kỳ tự động)",
        "events": [],
    },
    "extended_green": {
        "title": "Tăng thời gian đèn xanh",
        "events": [
            (30,  'extend_current_phase("TL1", 20)'),          # xanh Bắc-Nam 42s -> 62s
            (150, 'set_traffic_light("TL1", "GREEN", 30)'),    # lệnh mẫu của đề bài
            (250, 'set_cycle("TL1", 60, 30)'),                 # đổi chu kỳ: xanh NS 60s, EW 30s
        ],
    },
    "dangerous": {
        "title": "Lệnh điều khiển bất thường / nguy hiểm",
        "events": [
            (100, 'set_state("TL1", "GGGGGGGGGGGG", 20)'),      # xanh MỌI hướng -> xung đột
            (104, 'set_state("TL1", "rrrrrrrrrrrr", 10)'),      # xanh -> đỏ ngay, không qua vàng
            (106, 'set_traffic_light("TL1", "GREEN", 999)'),    # thời gian vô lý
            (108, 'set_traffic_light("TL9", "GREEN", 30)'),     # đèn không tồn tại
            (110, 'set_traffic_light("TL1", "BLUE", 30)'),      # màu không tồn tại
            (112, '__import__("os").system("echo hacked")'),    # chèn mã -> bị từ chối
        ],
    },
    "emergency": {
        "title": "Ưu tiên xe cứu thương + dừng toàn bộ giao lộ",
        "events": [
            (140, "__ambulance__"),                             # xe cứu thương xuất hiện hướng Đông
            (142, 'set_traffic_light("TL1", "GREEN", 25, "E")'),
            (200, 'set_traffic_light("TL1", "RED", 15)'),       # sự cố: dừng toàn bộ 15s
        ],
    },
    "demo": {
        "title": "Kịch bản tổng hợp để quay video demo (dùng với --light)",
        "events": [
            (40,  'extend_current_phase("TL1", 15)'),
            (100, 'set_traffic_light("TL1", "GREEN", 30)'),
            (150, 'set_state("TL1", "GGGGGGGGGGGG", 10)'),      # guard BẬT -> bị chặn
            (156, "__guard_off__"),
            (157, 'set_state("TL1", "GGGGGGGGGGGG", 10)'),      # guard TẮT -> xanh mọi hướng
            (167, "__guard_on__"),
            (190, "__ambulance__"),
            (191, 'set_traffic_light("TL1", "GREEN", 20, "E")'),
            (235, 'set_traffic_light("TL1", "RED", 10)'),
        ],
    },
    "interactive": {
        "title": "Chờ lệnh từ bên ngoài (TCP) — dùng scripts/send_command.py",
        "events": [],
    },
}


def add_ambulance():
    if "amb_route" not in traci.route.getIDList():
        traci.route.add("amb_route", ["E_far_in", "E_in", "W_out", "W_far_out"])
    traci.vehicle.add("ambulance_1", "amb_route", typeID="ambulance", departSpeed="max")
    return {"ok": True, "message": "Xe cứu thương 'ambulance_1' xuất hiện ở hướng Đông"}


def _approaching(edges):
    n = 0
    for edge in edges:
        length = traci.lane.getLength(f"{edge}_0")
        for v in traci.edge.getLastStepVehicleIDs(edge):
            if length - traci.vehicle.getLanePosition(v) <= NEAR_JUNCTION:
                n += 1
    return n


def run(name, server=None, realtime=False, max_time=None, log=print, on_step=None, verbose=False):
    """Chạy một kịch bản tới khi hết xe (hoặc tới max_time). Trả về dict thống kê.
    on_step(t, info, last_event) — callback tùy chọn (dùng khi quay video).
    Nhật ký: in mỗi lần đổi pha khi verbose / đèn đang MANUAL / trong 60s sau một lệnh;
    ngoài ra in 1 dòng trạng thái mỗi 60s."""
    tls.reset()
    ci.history.clear()
    sc = SCENARIOS[name]
    events = sorted(sc["events"])
    log(f"=== Kịch bản: {name} — {sc['title']} ===")
    departed = collisions = danger_steps = 0
    last_label = None
    last_event = None
    wall0, t0 = time.time(), traci.simulation.getTime()

    while True:
        t = traci.simulation.getTime()
        if max_time is not None and t >= max_time:
            break
        if max_time is None and t > 0 and traci.simulation.getMinExpectedNumber() <= 0:
            break
        traci.simulationStep()
        t = traci.simulation.getTime()
        departed += traci.simulation.getDepartedNumber()
        collisions += traci.simulation.getCollidingVehiclesNumber()
        tls.tick(TLS_ID)

        while events and t >= events[0][0]:
            _, cmd = events.pop(0)
            if cmd == "__ambulance__":
                res = add_ambulance()
            elif cmd in ("__guard_off__", "__guard_on__"):
                ci.enable_guard(cmd == "__guard_on__")
                res = {"ok": True, "message": "Safety guard " + ("BẬT" if cmd == "__guard_on__"
                                                                 else "TẮT (chỉ để minh họa)")}
            else:
                res = ci.execute(cmd, source="scenario")
            tag = "OK" if res.get("ok") else ("CHẶN" if res.get("blocked") else "LỖI")
            log(f"t={t:6.0f}s  >>> {cmd}")
            log(f"            [{tag}] {res.get('message') or res.get('error')}")
            last_event = (t, cmd, tag, res.get("message") or res.get("error"))
        if server:
            server.poll()

        info = tls.get_traffic_light_state(TLS_ID)
        changed = info["phase_name"] != last_label
        recent = last_event is not None and t - last_event[0] <= 60
        if (changed and (verbose or recent or info["mode"] == "MANUAL" or t <= 1)) or int(t) % 60 == 0:
            log(f"t={t:6.0f}s  xe={traci.vehicle.getIDCount():3d}  {tls.format_state(info)}")
        last_label = info["phase_name"]

        conflicts = safety_guard.find_conflicts(info["state"])
        if conflicts:
            danger_steps += 1
            if danger_steps == 1 or int(t) % 2 == 0:
                ns, ew = _approaching(["N_in", "S_in"]), _approaching(["E_in", "W_in"])
                log(f"t={t:6.0f}s  !!! NGUY HIỂM: {conflicts[0]} — {ns} xe Bắc-Nam và {ew} xe "
                    f"Đông-Tây đang tới giao lộ cùng lúc")
        if on_step:
            on_step(t, info, last_event)

        if realtime:
            delay = wall0 + (t - t0) - time.time()
            if delay > 0:
                time.sleep(delay)

    return {
        "scenario": name,
        "end_time": traci.simulation.getTime(),
        "departed": departed,
        "collisions": collisions,
        "danger_seconds": danger_steps,
        "commands": len(ci.history),
        "blocked": sum(1 for h in ci.history if h.get("blocked")),
        "errors": sum(1 for h in ci.history if not h.get("ok") and not h.get("blocked")),
    }

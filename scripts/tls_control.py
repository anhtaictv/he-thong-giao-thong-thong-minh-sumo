"""Lớp điều khiển đèn tín hiệu TL1 qua TraCI (yêu cầu #5, #6, #7, #9).

Các hàm chính:
    get_traffic_light_state(tls_id)                 -> đọc trạng thái đèn hiện tại (#6)
    set_traffic_light(tls_id, color, duration, direction=None)
                                                    -> lệnh đơn giản cho Agent Guard (#7, #9)
    extend_current_phase(tls_id, extra_seconds)     -> kéo dài pha hiện tại (#5, #7)
    set_cycle(tls_id, green_ns, green_ew, yellow, all_red) -> đổi chu kỳ khi đang chạy (#5)
    set_state(tls_id, state, duration)              -> lệnh "thô" cấp thấp (có thể nguy hiểm,
                                                       phải đi qua safety_guard)
    resume_program(tls_id)                          -> trả về chu kỳ tự động
    tick(tls_id)                                    -> gọi mỗi bước mô phỏng

Mọi lệnh cấp cao (set_traffic_light, resume_program) đều tự chèn pha VÀNG (3s) + ĐỎ
TOÀN PHẦN (2s) khi chuyển hướng, nên không bao giờ chuyển thẳng Xanh -> Đỏ. Chỉ
set_state() mới có thể tạo trạng thái nguy hiểm — vì vậy nó được safety_guard kiểm tra.
"""
import traci

PROGRAM_ID = "1"          # chương trình đèn trong routes/intersection.tls.add.xml
YELLOW_TIME = 3
ALL_RED_TIME = 2
MIN_DURATION = 1
MAX_DURATION = 120

# Vị trí các link trong chuỗi state 12 ký tự (xem routes/intersection.tls.add.xml):
#   (rẽ phải, đi thẳng, rẽ trái) của từng hướng vào
APPROACH_LINKS = {"N": (0, 1, 2), "E": (3, 4, 5), "S": (6, 7, 8), "W": (9, 10, 11)}
AXIS_OF = {"N": "NS", "S": "NS", "E": "EW", "W": "EW"}
AXIS_APPROACHES = {"NS": ("N", "S"), "EW": ("E", "W")}
GREEN_PHASE = {"NS": 0, "EW": 3}           # chỉ số pha xanh trong chương trình "1"
PHASE_NAMES = ["NS_GREEN", "NS_YELLOW", "ALL_RED_1", "EW_GREEN", "EW_YELLOW", "ALL_RED_2"]
DIRECTION_NAMES = {"N": "Bắc", "S": "Nam", "E": "Đông", "W": "Tây",
                   "NS": "Bắc-Nam", "EW": "Đông-Tây"}
COLOR_OF_CHAR = {"G": "GREEN", "g": "GREEN", "y": "YELLOW", "Y": "YELLOW",
                 "r": "RED", "R": "RED", "o": "OFF", "O": "OFF", "s": "RED", "u": "RED"}
VALID_CHARS = set("GgyYrRoOsu")


class CommandError(ValueError):
    """Lệnh không hợp lệ (sai ID đèn, sai màu, thời gian ngoài phạm vi...)."""


# Trạng thái điều khiển thủ công của từng đèn:
#   {"queue": [(state, giây, nhãn), ...], "step_until": t, "label": str,
#    "final": (axis, duration|None)}  -> khi hết hàng đợi: quay về chương trình, pha xanh `axis`
_manual = {}
_last_green_axis = {}


# ============================================================================ đọc trạng thái
def _now():
    return traci.simulation.getTime()


def _check_tls(tls_id):
    ids = traci.trafficlight.getIDList()
    if tls_id not in ids:
        raise CommandError(f"không tồn tại đèn '{tls_id}' (hiện có: {', '.join(ids)})")


def describe_state(state):
    """Chuỗi state -> màu đèn của từng hướng (lấy theo làn đi thẳng)."""
    return {d: COLOR_OF_CHAR.get(state[idx[1]], "?") for d, idx in APPROACH_LINKS.items()}


def get_traffic_light_state(tls_id="TL1"):
    """Đọc trạng thái đèn hiện tại (yêu cầu #6)."""
    _check_tls(tls_id)
    state = traci.trafficlight.getRedYellowGreenState(tls_id)
    program = traci.trafficlight.getProgram(tls_id)
    phase = traci.trafficlight.getPhase(tls_id)
    now = _now()
    if tls_id in _manual:
        m = _manual[tls_id]
        mode, remaining, phase_name = "MANUAL", m["step_until"] - now, m["label"]
    else:
        mode = "AUTO"
        remaining = traci.trafficlight.getNextSwitch(tls_id) - now
        phase_name = PHASE_NAMES[phase] if program == PROGRAM_ID and phase < len(PHASE_NAMES) else "?"
    return {
        "tls_id": tls_id,
        "time": now,
        "state": state,
        "directions": describe_state(state),
        "program": program,
        "phase": phase,
        "phase_name": phase_name,
        "remaining": round(max(0.0, remaining), 1),
        "mode": mode,
    }


def format_state(info):
    d = info["directions"]
    return (f"[{info['mode']:6s}] {info['phase_name']:11s} còn {info['remaining']:5.1f}s | "
            f"Bắc={d['N']:6s} Nam={d['S']:6s} Đông={d['E']:6s} Tây={d['W']:6s} | {info['state']}")


# ============================================================================ tiện ích nội bộ
def _check_duration(duration, name="duration"):
    if isinstance(duration, bool):
        raise CommandError(f"{name} phải là số")
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        raise CommandError(f"{name} phải là số, nhận '{duration}'")
    if not MIN_DURATION <= duration <= MAX_DURATION:
        raise CommandError(f"{name}={duration:g}s ngoài phạm vi cho phép [{MIN_DURATION}, {MAX_DURATION}]")
    return duration


def _state_for(approaches, protected_left=False, n=12):
    """Chuỗi state: các hướng trong `approaches` xanh, còn lại đỏ."""
    s = ["r"] * n
    for d in approaches:
        right, straight, left = APPROACH_LINKS[d]
        s[right] = s[straight] = "G"
        s[left] = "G" if protected_left else "g"
    return "".join(s)


def _transition_steps(current, target):
    """Các bước an toàn từ `current` sang `target`: Vàng 3s -> Đỏ toàn phần 2s (nếu cần)."""
    n = len(current)
    losing = {i for i in range(n)
              if (current[i] in "Gg" and target[i] not in "Gg") or current[i] in "yY"}
    if not losing:
        return []
    keep = {i for i in range(n) if current[i] in "Gg" and target[i] in "Gg"}
    # link được giữ xanh lấy ký tự của target (vd. rẽ trái 'G' -> 'g' phải nhường)
    yellow = "".join(target[i] if i in keep else ("y" if i in losing else "r") for i in range(n))
    all_red = "".join(target[i] if i in keep else "r" for i in range(n))
    return [(yellow, YELLOW_TIME, "YELLOW"), (all_red, ALL_RED_TIME, "ALL_RED")]


def _next_axis(tls_id):
    return "EW" if _last_green_axis.get(tls_id, "EW") == "NS" else "NS"


def _start_manual(tls_id, steps, final_axis, final_duration=None):
    """Lập hàng đợi: [chuyển tiếp an toàn + từng bước] rồi quay về pha xanh `final_axis`."""
    prev = traci.trafficlight.getRedYellowGreenState(tls_id)
    queue = []
    for state, dur, label in steps:
        queue.extend(_transition_steps(prev, state))
        queue.append((state, dur, label))
        prev = state
    queue.extend(_transition_steps(prev, _state_for(AXIS_APPROACHES[final_axis])))
    _manual[tls_id] = {"queue": queue, "final": (final_axis, final_duration),
                       "step_until": _now(), "label": "MANUAL"}
    _advance(tls_id)


def _advance(tls_id):
    m = _manual[tls_id]
    if m["queue"]:
        state, dur, label = m["queue"].pop(0)
        traci.trafficlight.setRedYellowGreenState(tls_id, state)
        m["step_until"] = _now() + dur
        m["label"] = label
        return
    axis, duration = m["final"]          # hết hàng đợi -> về chu kỳ tự động
    del _manual[tls_id]
    traci.trafficlight.setProgram(tls_id, PROGRAM_ID)
    traci.trafficlight.setPhase(tls_id, GREEN_PHASE[axis])
    if duration is not None:
        traci.trafficlight.setPhaseDuration(tls_id, duration)
    _last_green_axis[tls_id] = axis


def _current_or_next_axis(tls_id):
    """Trục đang xanh; nếu đang vàng/đỏ thì trục sẽ được xanh kế tiếp."""
    d = describe_state(traci.trafficlight.getRedYellowGreenState(tls_id))
    ns = d["N"] == "GREEN" or d["S"] == "GREEN"
    ew = d["E"] == "GREEN" or d["W"] == "GREEN"
    if ns and not ew:
        return "NS"
    if ew and not ns:
        return "EW"
    return _next_axis(tls_id)


# ============================================================================ lệnh điều khiển
def set_traffic_light(tls_id, color, duration=30, direction=None):
    """Lệnh đơn giản cho Agent Guard (yêu cầu #9), ví dụ set_traffic_light("TL1","GREEN",30).

    color = "GREEN"  — bật xanh trong `duration` giây, sau đó chạy tiếp chu kỳ tự động.
        direction=None       : xanh cho trục đang (hoặc sắp) được xanh
        direction="NS"/"EW"  : xanh cả trục Bắc-Nam / Đông-Tây
        direction="N"/"S"/"E"/"W": chỉ một hướng xanh (kể cả rẽ trái), các hướng khác đỏ
                               (ví dụ mở đường cho xe cứu thương)
    color = "RED"    — tất cả hướng đỏ trong `duration` giây
    color = "YELLOW" — tất cả hướng vàng (cảnh báo) trong `duration` giây
    Luôn tự chèn Vàng 3s + Đỏ toàn phần 2s khi chuyển hướng.
    """
    _check_tls(tls_id)
    if not isinstance(color, str):
        raise CommandError("color phải là chuỗi GREEN / YELLOW / RED")
    color = color.strip().upper()
    duration = _check_duration(duration)
    if direction is not None:
        direction = {"SN": "NS", "WE": "EW"}.get(str(direction).strip().upper(),
                                                   str(direction).strip().upper())
        if direction not in ("N", "S", "E", "W", "NS", "EW"):
            raise CommandError(f"direction '{direction}' không hợp lệ (N/S/E/W/NS/EW)")

    if color == "GREEN":
        if direction in (None, "NS", "EW"):
            axis = direction or _current_or_next_axis(tls_id)
            already_green = (tls_id not in _manual
                             and traci.trafficlight.getProgram(tls_id) == PROGRAM_ID
                             and traci.trafficlight.getPhase(tls_id) == GREEN_PHASE[axis])
            if already_green:
                traci.trafficlight.setPhaseDuration(tls_id, duration)
            else:
                _start_manual(tls_id, [], axis, duration)
            msg = f"Xanh hướng {DIRECTION_NAMES[axis]} trong {duration:g}s"
        else:
            target = _state_for([direction], protected_left=True)
            other = "EW" if AXIS_OF[direction] == "NS" else "NS"
            _start_manual(tls_id, [(target, duration, f"{direction}_ONLY")], other)
            msg = (f"Chỉ hướng {DIRECTION_NAMES[direction]} xanh trong {duration:g}s, "
                   f"các hướng khác đỏ")
    elif color == "RED":
        _start_manual(tls_id, [("r" * 12, duration, "ALL_RED_CMD")], _next_axis(tls_id))
        msg = f"Đỏ toàn bộ giao lộ trong {duration:g}s"
    elif color == "YELLOW":
        _start_manual(tls_id, [("y" * 12, duration, "ALL_YELLOW")], _next_axis(tls_id))
        msg = f"Vàng cảnh báo toàn bộ giao lộ trong {duration:g}s"
    else:
        raise CommandError(f"màu '{color}' không hợp lệ (GREEN / YELLOW / RED)")
    return {"ok": True, "message": msg}


def extend_current_phase(tls_id, extra_seconds):
    """Cộng thêm extra_seconds vào pha đang chạy (yêu cầu #5, #7)."""
    _check_tls(tls_id)
    extra = _check_duration(extra_seconds, "extra_seconds")
    if tls_id in _manual:
        _manual[tls_id]["step_until"] += extra
    else:
        remaining = traci.trafficlight.getNextSwitch(tls_id) - _now()
        traci.trafficlight.setPhaseDuration(tls_id, remaining + extra)
    return {"ok": True, "message": f"Kéo dài pha hiện tại thêm {extra:g}s"}


def set_cycle(tls_id, green_ns=42, green_ew=42, yellow=YELLOW_TIME, all_red=ALL_RED_TIME):
    """Đổi thời gian các pha / tổng chu kỳ đèn ngay khi mô phỏng đang chạy (yêu cầu #5)."""
    _check_tls(tls_id)
    green_ns = _check_duration(green_ns, "green_ns")
    green_ew = _check_duration(green_ew, "green_ew")
    yellow, all_red = float(yellow), float(all_red)
    if not 3 <= yellow <= 6:
        raise CommandError("yellow phải trong khoảng 3-6s")
    if not 1 <= all_red <= 5:
        raise CommandError("all_red phải trong khoảng 1-5s")
    P = traci.trafficlight.Phase
    phases = [P(green_ns, "GGgrrrGGgrrr", name="NS_GREEN"),
              P(yellow, "yyyrrryyyrrr", name="NS_YELLOW"),
              P(all_red, "rrrrrrrrrrrr", name="ALL_RED_1"),
              P(green_ew, "rrrGGgrrrGGg", name="EW_GREEN"),
              P(yellow, "rrryyyrrryyy", name="EW_YELLOW"),
              P(all_red, "rrrrrrrrrrrr", name="ALL_RED_2")]
    logic = traci.trafficlight.Logic(PROGRAM_ID, 0, 0, phases)
    auto = tls_id not in _manual
    phase = traci.trafficlight.getPhase(tls_id) if auto else 0
    traci.trafficlight.setProgramLogic(tls_id, logic)
    if auto:
        traci.trafficlight.setProgram(tls_id, PROGRAM_ID)
        traci.trafficlight.setPhase(tls_id, phase)
    cycle = green_ns + green_ew + 2 * yellow + 2 * all_red
    return {"ok": True,
            "message": f"Chu kỳ mới {cycle:g}s (xanh Bắc-Nam {green_ns:g}s, xanh Đông-Tây {green_ew:g}s)"}


def validate_raw_state(state, n=12):
    if not isinstance(state, str) or len(state) != n:
        raise CommandError(f"state phải là chuỗi {n} ký tự")
    bad = set(state) - VALID_CHARS
    if bad:
        raise CommandError(f"state chứa ký tự không hợp lệ: {''.join(sorted(bad))}")


def set_state(tls_id, state, duration=10):
    """Lệnh CẤP THẤP: đặt trực tiếp chuỗi state trong `duration` giây, KHÔNG tự chèn pha
    vàng -> có thể gây nguy hiểm. Luôn phải qua safety_guard trước khi gọi."""
    _check_tls(tls_id)
    validate_raw_state(state, len(traci.trafficlight.getRedYellowGreenState(tls_id)))
    duration = _check_duration(duration)
    axis = _next_axis(tls_id)
    traci.trafficlight.setRedYellowGreenState(tls_id, state)
    _manual[tls_id] = {"queue": _transition_steps(state, _state_for(AXIS_APPROACHES[axis])),
                       "final": (axis, None), "step_until": _now() + duration,
                       "label": "RAW_STATE"}
    return {"ok": True, "message": f"Đã đặt state thô '{state}' trong {duration:g}s"}


def resume_program(tls_id="TL1"):
    """Hủy mọi lệnh thủ công, quay về chu kỳ tự động (có chuyển tiếp an toàn)."""
    _check_tls(tls_id)
    if tls_id not in _manual:
        return {"ok": True, "message": "Đèn đang chạy tự động"}
    _start_manual(tls_id, [], _next_axis(tls_id))
    return {"ok": True, "message": "Quay về chu kỳ đèn tự động"}


def tick(tls_id="TL1"):
    """Gọi mỗi bước mô phỏng: chạy hàng đợi lệnh thủ công và ghi nhớ trục vừa được xanh."""
    if tls_id in _manual:
        if _now() >= _manual[tls_id]["step_until"]:
            _advance(tls_id)
    elif traci.trafficlight.getProgram(tls_id) == PROGRAM_ID:
        phase = traci.trafficlight.getPhase(tls_id)
        for axis, idx in GREEN_PHASE.items():
            if phase == idx:
                _last_green_axis[tls_id] = axis


def reset():
    """Xóa trạng thái nội bộ (khi chạy nhiều mô phỏng liên tiếp trong một tiến trình)."""
    _manual.clear()
    _last_green_axis.clear()

"""Bộ kiểm tra an toàn tối thiểu cho lệnh điều khiển đèn — "chỗ cắm" cho Agent Guard.

Mọi lệnh từ bên ngoài đi qua command_interface.execute() sẽ được gọi check() trước khi
thực thi. Sau này Agent Guard chỉ cần thay hàm này (command_interface.set_validator(fn))
bằng bộ kiểm tra thật của mình.

Quy tắc hiện có:
  1. Không cho 2 trục xung đột (Bắc-Nam và Đông-Tây) cùng xanh.
  2. Không cho rẽ trái "ưu tiên" (G) cùng lúc với luồng đi thẳng ngược chiều đang xanh.
  3. Không chuyển thẳng Xanh -> Đỏ khi chưa qua Vàng.
"""
import traci

import tls_control as tls

NS_LINKS = set(tls.APPROACH_LINKS["N"] + tls.APPROACH_LINKS["S"])
EW_LINKS = set(tls.APPROACH_LINKS["E"] + tls.APPROACH_LINKS["W"])
# (rẽ trái của hướng A, đi thẳng của hướng đối diện)
LEFT_VS_OPPOSING = [(2, 7), (8, 1), (5, 10), (11, 4)]


def find_conflicts(state):
    """Trả về danh sách mô tả các xung đột có trong chuỗi state."""
    problems = []
    ns_green = [i for i in NS_LINKS if state[i] in "Gg"]
    ew_green = [i for i in EW_LINKS if state[i] in "Gg"]
    if ns_green and ew_green:
        problems.append("trục Bắc-Nam và Đông-Tây cùng xanh (các luồng cắt nhau)")
    for left, straight in LEFT_VS_OPPOSING:
        if state[left] == "G" and state[straight] in "Gg":
            problems.append(f"rẽ trái ưu tiên (link {left}) cùng lúc với luồng thẳng đối diện (link {straight})")
    return problems


def check(command, args, kwargs):
    """Trả về (True, "") nếu cho phép, (False, lý do) nếu chặn."""
    if command != "set_state":
        return True, ""       # lệnh cấp cao đã tự đảm bảo an toàn trong tls_control
    params = dict(zip(("tls_id", "state", "duration"), args))
    params.update(kwargs)
    tls_id, state = params.get("tls_id"), params.get("state")
    if not isinstance(state, str) or len(state) != 12:
        return True, ""       # để tls_control báo lỗi định dạng
    problems = find_conflicts(state)
    try:
        current = traci.trafficlight.getRedYellowGreenState(tls_id)
    except Exception:
        current = None
    if current and len(current) == len(state):
        abrupt = [i for i, (a, b) in enumerate(zip(current, state)) if a in "Gg" and b in "rR"]
        if abrupt:
            problems.append(f"chuyển Xanh -> Đỏ đột ngột không qua Vàng (link {abrupt})")
    if problems:
        more = f" (+{len(problems) - 1} vi phạm khác)" if len(problems) > 1 else ""
        return False, problems[0] + more
    return True, ""

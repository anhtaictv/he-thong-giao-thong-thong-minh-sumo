"""Cổng nhận lệnh từ bên ngoài (yêu cầu #9) — để sau này nối Agent Guard.

Hỗ trợ 2 dạng lệnh dạng văn bản:
  1) Cú pháp gọi hàm:  set_traffic_light("TL1","GREEN",30)
                        set_traffic_light("TL1","GREEN",20,"E")
                        get_traffic_light_state("TL1")
  2) JSON:             {"command": "set_traffic_light", "args": ["TL1", "GREEN", 30]}
                        {"command": "set_traffic_light", "params": {"tls_id": "TL1", "color": "RED", "duration": 10}}

Lệnh được phân tích bằng `ast` (chỉ chấp nhận giá trị hằng: chuỗi/số), KHÔNG dùng eval().

Có thể dùng theo 2 cách:
  - Gọi trực tiếp trong Python: execute('set_traffic_light("TL1","GREEN",30)')
  - Qua mạng TCP: CommandServer lắng nghe (mặc định 127.0.0.1:9000), mỗi dòng 1 lệnh,
    phản hồi 1 dòng JSON. Client mẫu: scripts/send_command.py
"""
import ast
import json
import selectors
import socket

import tls_control as tls
import safety_guard

COMMANDS = {
    "set_traffic_light": tls.set_traffic_light,
    "get_traffic_light_state": tls.get_traffic_light_state,
    "extend_current_phase": tls.extend_current_phase,
    "set_cycle": tls.set_cycle,
    "set_state": tls.set_state,
    "resume_program": tls.resume_program,
}

_validator = safety_guard.check
_guard_enabled = True
history = []            # nhật ký mọi lệnh đã nhận (phục vụ báo cáo / Agent Guard)


def set_validator(fn):
    """Thay bộ kiểm tra an toàn (Agent Guard sẽ gắn hàm của mình vào đây).
    fn(command, args, kwargs) -> (bool cho_phép, str lý_do)"""
    global _validator
    _validator = fn


def enable_guard(enabled=True):
    global _guard_enabled
    _guard_enabled = enabled


def parse_command(text):
    """Chuỗi lệnh -> (tên_lệnh, args, kwargs)."""
    text = text.strip()
    if not text:
        raise tls.CommandError("lệnh rỗng")
    if text.startswith("{"):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise tls.CommandError(f"JSON không hợp lệ: {exc}")
        name = obj.get("command") or obj.get("cmd")
        args = obj.get("args", [])
        kwargs = obj.get("params", obj.get("kwargs", {}))
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            raise tls.CommandError("'args' phải là mảng, 'params' phải là object")
        return name, args, kwargs
    try:
        node = ast.parse(text, mode="eval").body
    except SyntaxError:
        raise tls.CommandError(f"sai cú pháp lệnh: {text}")
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        raise tls.CommandError("lệnh phải có dạng ten_lenh(tham_so, ...)")
    try:
        args = [ast.literal_eval(a) for a in node.args]
        kwargs = {k.arg: ast.literal_eval(k.value) for k in node.keywords}
    except ValueError:
        raise tls.CommandError("tham số chỉ được là chuỗi hoặc số")
    return node.func.id, args, kwargs


def execute(text, source="local"):
    """Phân tích + kiểm tra an toàn + thực thi 1 lệnh. Luôn trả về dict (không ném lỗi)."""
    import traci
    entry = {"time": traci.simulation.getTime(), "source": source, "command": text.strip()}
    try:
        name, args, kwargs = parse_command(text)
        if name not in COMMANDS:
            raise tls.CommandError(f"lệnh '{name}' không được hỗ trợ (có: {', '.join(COMMANDS)})")
        if _guard_enabled:
            allowed, reason = _validator(name, args, kwargs)
            if not allowed:
                result = {"ok": False, "blocked": True, "error": f"BỊ CHẶN bởi safety guard: {reason}"}
                history.append({**entry, **result})
                return result
        try:
            out = COMMANDS[name](*args, **kwargs)
        except TypeError as exc:
            raise tls.CommandError(f"sai tham số cho {name}: {exc}")
        result = out if name != "get_traffic_light_state" else {"ok": True, "state": out}
    except tls.CommandError as exc:
        result = {"ok": False, "error": str(exc)}
    except Exception as exc:  # lỗi TraCI...
        result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    history.append({**entry, **result})
    return result


class CommandServer:
    """Máy chủ TCP không chặn, gọi poll() mỗi bước mô phỏng để xử lý lệnh đến."""

    def __init__(self, host="127.0.0.1", port=9000, log=print):
        self.sel = selectors.DefaultSelector()
        self.log = log
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind((host, port))
        self.listener.listen()
        self.listener.setblocking(False)
        self.sel.register(self.listener, selectors.EVENT_READ, data=None)
        self.buffers = {}
        self.log(f"[server] Đang nhận lệnh tại {host}:{port} (mỗi dòng 1 lệnh)")

    def poll(self):
        for key, _ in self.sel.select(timeout=0):
            if key.data is None:
                conn, addr = self.listener.accept()
                conn.setblocking(False)
                self.sel.register(conn, selectors.EVENT_READ, data=addr)
                self.buffers[conn] = b""
            else:
                self._read(key.fileobj, key.data)

    def _read(self, conn, addr):
        try:
            chunk = conn.recv(4096)
        except (ConnectionResetError, BlockingIOError):
            chunk = b""
        if not chunk:
            self._drop(conn)
            return
        self.buffers[conn] += chunk
        while b"\n" in self.buffers[conn]:
            line, self.buffers[conn] = self.buffers[conn].split(b"\n", 1)
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            result = execute(text, source=f"tcp:{addr[0]}:{addr[1]}")
            self.log(f"[server] {text}  ->  {result}")
            try:
                conn.sendall((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
            except OSError:
                self._drop(conn)
                return

    def _drop(self, conn):
        self.sel.unregister(conn)
        self.buffers.pop(conn, None)
        conn.close()

    def close(self):
        for conn in list(self.buffers):
            self._drop(conn)
        self.sel.unregister(self.listener)
        self.listener.close()

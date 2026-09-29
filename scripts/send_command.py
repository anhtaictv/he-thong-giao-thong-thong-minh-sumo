#!/usr/bin/env python
"""Client mẫu gửi lệnh tới mô phỏng đang chạy (giả lập Agent Guard gửi lệnh từ bên ngoài).

Trước tiên chạy mô phỏng có bật server, ví dụ:
    python scripts/run_simulation.py --scenario interactive --gui

Rồi ở cửa sổ khác:
    python scripts/send_command.py "set_traffic_light('TL1','GREEN',30)"
    python scripts/send_command.py "set_traffic_light('TL1','GREEN',20,'E')"
    python scripts/send_command.py "get_traffic_light_state('TL1')"
    python scripts/send_command.py            # chế độ gõ lệnh tương tác
"""
import argparse
import json
import socket


def send(text, host="127.0.0.1", port=9000, timeout=5.0):
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall((text.strip() + "\n").encode("utf-8"))
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
    return json.loads(buf.decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="?", help='ví dụ: set_traffic_light("TL1","GREEN",30)')
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9000)
    args = ap.parse_args()

    if args.command:
        print(json.dumps(send(args.command, args.host, args.port), ensure_ascii=False, indent=2))
        return
    print("Nhập lệnh (Ctrl+C để thoát). Ví dụ: set_traffic_light(\"TL1\",\"GREEN\",30)")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line:
            try:
                print(json.dumps(send(line, args.host, args.port), ensure_ascii=False, indent=2))
            except OSError as exc:
                print(f"Không kết nối được mô phỏng: {exc}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Quay video demo (yêu cầu #10): chạy kịch bản "demo" trên SUMO-GUI, chụp màn hình từng
bước bằng traci.gui.screenshot(), ghép thêm bảng thông tin (đèn 4 hướng, lệnh vừa gửi,
cảnh báo) rồi xuất:
    media/demo.mp4               — video ~2,5 phút (cần ffmpeg)
    media/demo.gif               — bản GIF thu nhỏ để xem trong README
    media/01_...png ... 08_...png — ảnh chụp các mốc quan trọng

Chạy trên máy có màn hình:   python scripts/record_demo.py
Chạy trên Linux không màn hình: xvfb-run -a -s "-screen 0 1400x1000x24" python scripts/record_demo.py
"""
import os
import shutil
import subprocess
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sumolib
import traci
from PIL import Image, ImageDraw, ImageFont

import command_interface as ci
import safety_guard
import scenarios

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(BASE, ".."))
CFG = os.path.join(ROOT, "intersection_light.sumocfg")
VIEW_SETTINGS = os.path.join(BASE, "view_settings.xml")
MEDIA = os.path.join(ROOT, "media")
FRAMES = os.path.join(MEDIA, "frames")
END_TIME = 270          # giây mô phỏng
STEP = 0.5              # giây mô phỏng mỗi khung hình
FPS = 4                 # 4 khung/giây -> video chạy nhanh gấp 2 lần thời gian mô phỏng
W, H = 1280, 720
PANEL_W = 470

CHAPTERS = [
    (0,   "1. Giao thông bình thường",
          "Chu kỳ tự động: Xanh 42s -> Vàng 3s -> Đỏ toàn phần 2s, luân phiên Bắc-Nam / Đông-Tây"),
    (40,  "2. Tăng thời gian đèn xanh",
          "extend_current_phase(\"TL1\", 15): pha xanh Bắc-Nam dài thêm 15 giây"),
    (100, "3. Lệnh từ bên ngoài (Agent Guard)",
          "set_traffic_light(\"TL1\",\"GREEN\",30): giữ xanh trục đang chạy đúng 30 giây"),
    (150, "4. Lệnh nguy hiểm bị CHẶN",
          "set_state: xanh MỌI hướng -> safety guard phát hiện xung đột và từ chối"),
    (156, "4b. Nếu KHÔNG có guard",
          "Mọi hướng cùng xanh 10s: các luồng cắt nhau -> nguy cơ va chạm"),
    (172, "Trở lại chu kỳ tự động",
          "Luôn qua Vàng 3s + Đỏ toàn phần 2s trước khi đổi hướng"),
    (190, "5. Ưu tiên xe cứu thương",
          "set_traffic_light(\"TL1\",\"GREEN\",20,\"E\"): chỉ hướng Đông xanh, các hướng khác đỏ"),
    (235, "6. Sự cố: dừng toàn bộ giao lộ",
          "set_traffic_light(\"TL1\",\"RED\",10): đỏ tất cả các hướng 10 giây"),
    (252, "Khôi phục",
          "Đèn tự quay về chu kỳ tự động sau khi hết thời gian lệnh"),
]
HIGHLIGHTS = {10: "01_normal", 50: "02_extended_green", 110: "03_green_command",
              151: "04_dangerous_blocked", 160: "05_unsafe_all_green",
              200: "06_ambulance_east", 243: "07_all_red", 262: "08_resumed"}

COLORS = {"GREEN": (40, 200, 70), "YELLOW": (250, 200, 30), "RED": (230, 50, 50), "OFF": (90, 90, 90)}


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in ("/usr/share/fonts/truetype/dejavu", "C:/Windows/Fonts", "/Library/Fonts"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    for alt in ("arialbd.ttf" if bold else "arial.ttf",):
        try:
            return ImageFont.truetype(alt, size)
        except OSError:
            pass
    return ImageFont.load_default()


F_TITLE, F_H, F_TXT, F_SMALL = font(26, True), font(20, True), font(17), font(15)


def chapter_at(t):
    cur = CHAPTERS[0]
    for c in CHAPTERS:
        if t >= c[0]:
            cur = c
    return cur


def draw_light(d, x, y, label, color):
    d.rounded_rectangle([x, y, x + 96, y + 118], 12, fill=(30, 30, 34))
    for i, c in enumerate(("RED", "YELLOW", "GREEN")):
        on = c == color
        fill = COLORS[c] if on else tuple(v // 5 for v in COLORS[c])
        d.ellipse([x + 32, y + 8 + i * 34, x + 64, y + 40 + i * 34], fill=fill)
    d.text((x + 48, y + 128), label, font=F_TXT, fill=(235, 235, 235), anchor="mt")


def compose(shot_path, rec):
    t, info, last_event, veh, guard_on, conflicts = rec
    canvas = Image.new("RGB", (W, H), (18, 20, 26))
    try:
        sim = Image.open(shot_path).convert("RGB")
        sw = W - PANEL_W
        scale = max(sw / sim.width, H / sim.height)
        sim = sim.resize((int(sim.width * scale), int(sim.height * scale)))
        left, top = (sim.width - sw) // 2, (sim.height - H) // 2
        canvas.paste(sim.crop((left, top, left + sw, top + H)), (0, 0))
    except (OSError, FileNotFoundError):
        pass
    d = ImageDraw.Draw(canvas)
    x0 = W - PANEL_W
    d.rectangle([x0, 0, W, H], fill=(24, 27, 35))
    d.text((x0 + 20, 16), "Giao lộ thông minh TL1", font=F_TITLE, fill="white")
    d.text((x0 + 20, 52), f"SUMO + TraCI   |   t = {t:5.0f}s   |   {veh} xe", font=F_SMALL, fill=(170, 175, 190))

    dirs = info["directions"]
    for i, (k, name) in enumerate((("N", "Bắc"), ("S", "Nam"), ("E", "Đông"), ("W", "Tây"))):
        draw_light(d, x0 + 20 + i * 110, 86, name, dirs[k])
    d.text((x0 + 20, 244), f"Chế độ: {info['mode']}   Pha: {info['phase_name']}", font=F_TXT, fill="white")
    d.text((x0 + 20, 268), f"Còn lại: {info['remaining']:.0f}s   State: {info['state']}", font=F_SMALL,
           fill=(170, 175, 190))
    g_col = (60, 200, 90) if guard_on else (240, 80, 70)
    d.text((x0 + 20, 294), f"Safety guard: {'BẬT' if guard_on else 'TẮT'}", font=F_TXT, fill=g_col)

    title, desc = chapter_at(t)[1:]
    d.line([x0 + 20, 330, W - 20, 330], fill=(60, 64, 76), width=1)
    d.text((x0 + 20, 342), title, font=F_H, fill=(120, 190, 255))
    yy = 372
    for line in textwrap.wrap(desc, 44):
        d.text((x0 + 20, yy), line, font=F_TXT, fill=(225, 225, 230))
        yy += 23

    d.line([x0 + 20, 470, W - 20, 470], fill=(60, 64, 76), width=1)
    d.text((x0 + 20, 480), "Lệnh gần nhất:", font=F_H, fill="white")
    if last_event:
        et, cmd, tag, msg = last_event
        yy = 510
        for line in textwrap.wrap(f"[t={et:.0f}s] {cmd}", 50)[:3]:
            d.text((x0 + 20, yy), line, font=F_SMALL, fill=(200, 205, 215))
            yy += 20
        col = {"OK": (60, 200, 90), "CHẶN": (250, 170, 40)}.get(tag, (240, 80, 70))
        for line in textwrap.wrap(f"{tag}: {msg}", 50)[:4]:
            d.text((x0 + 20, yy + 4), line, font=F_SMALL, fill=col)
            yy += 20
    if conflicts:
        d.rectangle([0, H - 64, x0, H], fill=(200, 30, 30))
        d.text((20, H - 50), "NGUY HIỂM: các hướng xung đột cùng được XANH!", font=F_H, fill="white")
    return canvas


def card(lines):
    img = Image.new("RGB", (W, H), (18, 20, 26))
    d = ImageDraw.Draw(img)
    y = H // 2 - len(lines) * 24
    for i, text in enumerate(lines):
        f = F_TITLE if i == 0 else F_TXT
        d.text((W // 2, y), text, font=f, fill="white" if i == 0 else (200, 205, 215), anchor="mt")
        y += 48 if i == 0 else 32
    return img


def main():
    if os.path.isdir(FRAMES):
        shutil.rmtree(FRAMES)
    os.makedirs(FRAMES)
    traci.start([sumolib.checkBinary("sumo-gui"), "-c", CFG, "--no-step-log", "true",
                 "--start", "true", "--quit-on-end", "true", "--delay", "0",
                 "--step-length", str(STEP), "--window-size", "1100,900",
                 "--gui-settings-file", VIEW_SETTINGS,
                 "--collision.check-junctions", "true", "--collision.action", "warn"])
    traci.trafficlight.setProgram("TL1", "1")
    traci.gui.setOffset("View #0", 200, 200)   # tâm giao lộ TL1
    traci.gui.setZoom("View #0", 420)
    records = []

    def on_step(t, info, last_event):
        path = os.path.join(FRAMES, f"frame_{len(records):05d}.png")
        traci.gui.screenshot("View #0", path)
        records.append((path, (t, info, last_event, traci.vehicle.getIDCount(),
                               ci._guard_enabled, safety_guard.find_conflicts(info["state"]))))

    try:
        stats = scenarios.run("demo", max_time=END_TIME, on_step=on_step)
        traci.simulationStep()          # screenshot được ghi ở lần vẽ kế tiếp
        print(stats)
    except traci.exceptions.FatalTraCIError as exc:
        print(f"SUMO-GUI ngắt kết nối: {exc} — vẫn dựng video từ các khung đã chụp")
    finally:
        try:
            traci.close(False)
        except Exception:
            pass

    out_dir = os.path.join(FRAMES, "composed")
    os.makedirs(out_dir)
    n = 0

    def put(img):
        nonlocal n
        img.save(os.path.join(out_dir, f"c_{n:05d}.png"))
        n += 1

    intro = card(["Mô phỏng giao lộ thông minh bằng Eclipse SUMO",
                  "Giao lộ 4 hướng Bắc-Nam-Đông-Tây, đèn TL1, 36 xe + 1 xe cứu thương",
                  "Điều khiển đèn bằng Python + TraCI, sẵn sàng nhận lệnh từ Agent Guard",
                  "Video chạy nhanh gấp 2 lần thời gian mô phỏng"])
    for _ in range(FPS * 5):
        put(intro)
    shots = {}
    for path, rec in records:
        if not os.path.exists(path):
            continue
        img = compose(path, rec)
        put(img)
        t = int(rec[0])
        if t in HIGHLIGHTS and t not in shots:
            shots[t] = img
            img.save(os.path.join(MEDIA, f"{HIGHLIGHTS[t]}.png"))
    outro = card(["Kết thúc demo",
                  "Kịch bản: bình thường -> tăng xanh -> lệnh GREEN 30s -> lệnh nguy hiểm bị chặn",
                  "-> xe cứu thương hướng Đông -> đỏ toàn bộ -> khôi phục",
                  "Mã nguồn: scripts/tls_control.py, command_interface.py, safety_guard.py"])
    for _ in range(FPS * 5):
        put(outro)
    print(f"Đã dựng {n} khung hình, {len(shots)} ảnh mốc")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
    if ffmpeg:
        mp4 = os.path.join(MEDIA, "demo.mp4")
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", os.path.join(out_dir, "c_%05d.png"), "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-r", "24", "-crf", "23", mp4], check=True)
        print(f"Video: {mp4} (~{n / FPS:.0f}s)")
    else:
        print("Không có ffmpeg -> bỏ qua demo.mp4 (pip install imageio-ffmpeg)")

    frames = sorted(os.listdir(out_dir))[FPS * 5:-FPS * 5:4]      # 1 khung / 2s mô phỏng
    gif = [Image.open(os.path.join(out_dir, f)).resize((640, 360)) for f in frames]
    if gif:
        gif[0].save(os.path.join(MEDIA, "demo.gif"), save_all=True, append_images=gif[1:],
                    duration=250, loop=0, optimize=True)
        print(f"GIF: media/demo.gif ({len(gif)} khung)")


if __name__ == "__main__":
    main()

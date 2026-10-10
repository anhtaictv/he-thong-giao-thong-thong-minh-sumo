# Hướng dẫn sử dụng — Mô phỏng giao lộ SUMO

## 1. Cài đặt

```bash
pip install eclipse-sumo traci sumolib pillow
sumo --version
sumo-gui --version
```

Nếu muốn quay lại video bằng `record_demo.py`, cần thêm `ffmpeg`. Trên Windows có thể cài
bằng `pip install imageio-ffmpeg`, script sẽ tự tìm.

Mọi lệnh bên dưới chạy từ **thư mục gốc của dự án** (thư mục chứa `intersection.sumocfg`).

## 2. Cấu trúc thư mục

```
network/    → định nghĩa nút/cạnh + intersection.net.xml đã biên dịch
routes/     → luồng xe (.rou.xml), chương trình đèn chỉnh được (.tls.add.xml), ảnh xe (cars/)
scripts/    → mã Python (xem bảng trong README.md)
media/      → video demo.mp4, demo.gif, ảnh chụp các mốc
intersection.sumocfg        → cấu hình chính (36 xe, ~10 phút)
intersection_light.sumocfg  → cùng 36 xe dồn trong ~4 phút (xem GUI / quay video)
```

## 3. Tự kiểm tra yêu cầu

```bash
python scripts/check_requirements.py
```

Chương trình chạy mô phỏng không giao diện và in bảng ĐẠT / KHÔNG ĐẠT cho các yêu cầu 1–9.

## 4. Chạy các tình huống

```bash
python scripts/run_simulation.py --scenario normal           # 1. giao thông bình thường
python scripts/run_simulation.py --scenario extended_green   # 2. tăng thời gian đèn xanh
python scripts/run_simulation.py --scenario dangerous        # 3. lệnh bất thường / nguy hiểm
python scripts/run_simulation.py --scenario emergency        #    xe cứu thương + đỏ toàn bộ
```

| Cờ | Ý nghĩa |
|---|---|
| `--scenario` | `normal`, `extended_green`, `dangerous`, `emergency`, `demo`, `interactive` |
| `--gui` | mở SUMO-GUI (tự phóng to vào giao lộ) |
| `--light` | dùng `intersection_light.sumocfg` (xe dày hơn, hợp để xem GUI) |
| `--delay 200` | độ trễ mỗi bước trên GUI (ms), số càng lớn chạy càng chậm |
| `--server --port 9000` | bật cổng nhận lệnh TCP (tự bật với `interactive`) |
| `--realtime` | 1 giây mô phỏng = 1 giây thực |
| `--max-time 300` | dừng tại giây thứ 300 |
| `--unsafe` | TẮT safety guard (chỉ để minh họa hậu quả của lệnh nguy hiểm) |
| `--verbose` | in mọi lần đổi pha đèn |

Khi kết thúc, chương trình in số xe, số va chạm, số lệnh bị chặn, và kiểm tra số xe có nằm
trong khoảng 20–50 hay không.

## 5. Gửi lệnh từ bên ngoài (chuẩn bị cho Agent Guard)

Cửa sổ 1, chạy mô phỏng và chờ lệnh:

```bash
python scripts/run_simulation.py --scenario interactive --gui --light
```

Cửa sổ 2, gửi lệnh:

```bash
python scripts/send_command.py "set_traffic_light('TL1','GREEN',30)"
python scripts/send_command.py "set_traffic_light('TL1','GREEN',20,'E')"
python scripts/send_command.py "get_traffic_light_state('TL1')"
python scripts/send_command.py "{\"command\":\"set_traffic_light\",\"args\":[\"TL1\",\"RED\",10]}"
python scripts/send_command.py          # chế độ gõ lệnh liên tục
```

Mỗi lệnh nhận về một phản hồi JSON, ví dụ `{"ok": true, "message": "Xanh hướng Bắc-Nam trong 30s"}`
hoặc `{"ok": false, "blocked": true, "error": "BỊ CHẶN bởi safety guard: ..."}`.

Giao thức rất đơn giản: TCP `127.0.0.1:9000`, mỗi dòng một lệnh (UTF-8), mỗi phản hồi một dòng
JSON. Agent Guard có thể dùng bất kỳ ngôn ngữ nào để gửi lệnh.

## 6. Đổi chu kỳ đèn

- **Trước khi chạy:** sửa `duration` trong `routes/intersection.tls.add.xml`. Không cần biên dịch lại mạng.
- **Khi đang chạy:** gửi lệnh `set_cycle("TL1", 60, 30)` (xanh Bắc-Nam 60s, xanh Đông-Tây 30s),
  hoặc `extend_current_phase("TL1", 20)` để kéo dài pha đang chạy.

## 7. Quay lại video và ảnh demo

```bash
python scripts/record_demo.py
# Linux không màn hình:
xvfb-run -a -s "-screen 0 1400x1000x24" python scripts/record_demo.py
```

Kết quả được ghi vào `media/`: `demo.mp4` (~2,5 phút), `demo.gif`, và `01_…png` đến `08_…png`.

## 8. Sửa mạng giao lộ

Mỗi chiều có 3 làn:
- Đoạn xa giao lộ (`*_far_in` / `*_far_out`, 100m) chia làn theo **loại xe**: làn 0 xe máy,
  làn 1 ô tô con/taxi, làn 2 xe tải/xe buýt (xe cứu thương đi mọi làn).
- Đoạn sát giao lộ (`*_in` / `*_out`, 100m) là làn chung, chia theo **hướng rẽ**: làn 0 rẽ phải + thẳng,
  làn 1 thẳng, làn 2 thẳng + rẽ trái (`intersection.con.xml`). Xe tự chuyển làn trước khi vào giao lộ,
  nhờ vậy các luồng của cùng một hướng không cắt ngang nhau.
- `intersection.tll.xml` gán `linkIndex` cố định để chuỗi state đèn vẫn là 12 ký tự.

Nếu sửa các file trong `network/`, cần biên dịch lại:

```bash
netconvert -n network/intersection.nod.xml -e network/intersection.edg.xml \
           -x network/intersection.con.xml -i network/intersection.tll.xml \
           --no-turnarounds true --tls.yellow.time 3 -o network/intersection.net.xml
```

Cỏ và cây trên GUI nằm ở `network/decor.add.xml` (chỉ để trang trí); nếu đổi kích thước giao lộ thì
sinh lại bằng `python scripts/generate_decor.py`.

Nếu số hướng thay đổi, cần cập nhật lại chuỗi `state` trong
`routes/intersection.tls.add.xml` và `APPROACH_LINKS` trong `scripts/tls_control.py`.

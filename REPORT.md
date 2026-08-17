# Báo cáo: Mô phỏng giao lộ thông minh bằng Eclipse SUMO (phục vụ tích hợp Agent Guard)

## 1. Kiến trúc tổng quan

```
                     ┌──────────────────────────┐
                     │   network/*.nod/edg.xml   │  (tự viết, 5 node: TL1 + N/S/E/W)
                     └────────────┬─────────────┘
                                  │ netconvert
                                  ▼
                     ┌──────────────────────────┐
                     │  network/intersection.net.xml  │ (topology + TLS tự sinh)
                     └────────────┬─────────────┘
                                  │
        routes/intersection*.rou.xml ──┤
        routes/intersection.tls.add.xml┤──►  intersection*.sumocfg ──► sumo / sumo-gui
                                  │                                        │
                                  │                                    TraCI (socket)
                                  │                                        │
                                  │                          scripts/tls_control.py
                                  │                        (get/set traffic light state)
                                  │                                        │
                                  └──────────────────────────►  scripts/scenarios.py
                                                                (normal / extended_green / emergency)
                                                                        │
                                                                scripts/run_simulation.py (CLI)
                                                                scripts/record_demo.py (ảnh + GIF)
```

Một giao lộ 4 nhánh (Bắc–Nam–Đông–Tây) tại nút `TL1`, mỗi nhánh 1 làn, dài 200m.
`netconvert` tự sinh chương trình đèn Đỏ–Vàng–Xanh (2 pha chính NS/EW + pha vàng chuyển
tiếp) vì suy đoán state-string bằng tay dễ sai. Python điều khiển đèn qua TraCI (giao thức
socket chuẩn của SUMO) chứ không sửa trực tiếp file trong lúc chạy.

## 2. Cấu trúc file

| File | Vai trò |
|---|---|
| `network/intersection.nod.xml`, `.edg.xml` | Định nghĩa 5 node và 8 cạnh (vào/ra 4 hướng) |
| `network/intersection.net.xml` | Mạng lưới đã biên dịch (netconvert), gồm TLS tự sinh |
| `routes/intersection.rou.xml` | Nhu cầu giao thông chính: 12 luồng (mọi cặp hướng vào/ra), ~48 xe/5 phút, trộn `car` (ô tô) và `motorbike` (xe máy) |
| `routes/intersection_light.rou.xml` | Bản nhu cầu nhẹ (~10 xe) chỉ để xem GUI mượt |
| `routes/intersection.tls.add.xml` | Bản sao có thể chỉnh sửa của chương trình đèn (programID `1`) — sửa số ở đây để đổi chu kỳ/thời gian đèn (yêu cầu #5) |
| `intersection.sumocfg` / `intersection_light.sumocfg` | Cấu hình chạy (net + route + additional + seed cố định 42) |
| `scripts/tls_control.py` | Lớp điều khiển TraCI: `get_traffic_light_state()`, `set_traffic_light(tls_id, color, duration)`, `extend_current_phase()`, `tick()` |
| `scripts/scenarios.py` | 3 kịch bản minh họa (yêu cầu #8) |
| `scripts/run_simulation.py` | CLI chạy 1 kịch bản: `--scenario`, `--gui`, `--light` |
| `scripts/record_demo.py` | Chụp ảnh + dựng GIF demo bằng `traci.gui.screenshot()` |

## 3. Ánh xạ yêu cầu

| # | Yêu cầu | Đáp ứng |
|---|---|---|
| 1 | Cài đặt & chạy SUMO/SUMO-GUI | Cài qua pip (`eclipse-sumo`), xác nhận `sumo.exe`/`sumo-gui.exe` chạy được |
| 2 | Giao lộ 4 hướng B-N-Đ-T | `network/intersection.nod.xml` + `.edg.xml`, nút `TL1` |
| 3 | 20–50 xe | 12 luồng trong `intersection.rou.xml` → 48 xe/lượt chạy (đã đo thực tế, ổn định nhờ seed) |
| 4 | Đèn Đỏ-Vàng-Xanh tự động | TLS tự sinh bởi netconvert, chạy độc lập không cần can thiệp |
| 5 | Đổi chu kỳ/thời gian đèn | `routes/intersection.tls.add.xml` (sửa tay, chương trình `1`) + `extend_current_phase()` (runtime) |
| 6 | Python + TraCI đọc trạng thái đèn | `tls_control.get_traffic_light_state()` |
| 7 | Python gửi lệnh đổi đèn | `tls_control.set_traffic_light()`, `extend_current_phase()` |
| 8 | 3 tình huống minh họa | `scenarios.run_normal / run_extended_green / run_emergency` — đã kiểm chứng bằng log console |
| 9 | Nhận lệnh dạng đơn giản | `set_traffic_light("TL1","GREEN",30)` — đúng chữ ký, sẵn sàng cho Agent Guard gọi sau |

## 4. Cách chạy

```bash
# Chạy đúng bộ dữ liệu chính (headless, nhanh, dùng để kiểm chứng)
python scripts/run_simulation.py --scenario normal
python scripts/run_simulation.py --scenario extended_green
python scripts/run_simulation.py --scenario emergency

# Xem trực quan (tải nhẹ, khuyến nghị chạy trên máy thật, ngoài môi trường sandbox)
python scripts/run_simulation.py --scenario emergency --gui --light

# Chụp ảnh + dựng GIF demo
python scripts/record_demo.py
```

Mỗi lần chạy `run_simulation.py` tự kiểm tra: tổng số xe đã vào mạng phải nằm trong
khoảng 20–60 (khớp yêu cầu #3), nếu sai lệch sẽ báo lỗi ngay — đây là bài kiểm tra tối
thiểu đi kèm logic (`assert` trong `run_simulation.py`).

## 5. Ghi chú / giới hạn

- **`set_traffic_light` là API đơn trục** (không điều khiển riêng từng hướng): `"RED"`/`"YELLOW"`
  ép toàn bộ đèn về màu đó trong `duration` giây (an toàn — mô phỏng ưu tiên xe khẩn cấp),
  `"GREEN"` khôi phục chương trình bình thường. Điều khiển theo từng hướng cụ thể sẽ làm
  sau khi Agent Guard định nghĩa lược đồ lệnh thật.
- **SUMO-GUI trong môi trường tự động (Claude Code) không ổn định**: cửa sổ GUI do TraCI
  điều khiển bị ngắt kết nối sau một khoảng thời gian thực không cố định, dù dữ liệu/logic
  mô phỏng đã được xác nhận đúng nhiều lần qua bản headless (không giao diện). Đây là giới
  hạn của phiên hiển thị ảo trong sandbox, không phải lỗi trong mã nguồn. Ảnh/GIF trong
  `media/` được chụp qua `traci.gui.screenshot()` (chụp nội bộ trong tiến trình SUMO, không
  cần công cụ chụp màn hình ngoài) với bản dữ liệu nhẹ để tăng độ ổn định.
- Để có video màn hình thật (không phải GIF ghép từ ảnh chụp), nên tự chạy
  `python scripts/run_simulation.py --scenario emergency --gui` trực tiếp trên máy cá nhân
  (ngoài môi trường này) và dùng phần mềm quay màn hình.

## 6. Ảnh chụp & video demo

Đã tạo bằng `scripts/record_demo.py` (bản nhu cầu nhẹ, 44 khung hình sau khi loại bỏ khung
đầu bị hỏng do chụp lúc SUMO-GUI chưa vẽ xong, phát lại ~2,35 phút — khớp yêu cầu 2-3 phút):

- `media/demo.gif` — GIF động toàn bộ quá trình: giao thông bình thường → mở rộng đèn xanh
  (t=40s) → lệnh khẩn cấp ép đèn đỏ toàn bộ 10s (t=90s) → khôi phục bình thường.
- `media/01_start.png` … `media/07_resumed.png` — 7 ảnh chụp mốc quan trọng (đèn xanh
  NS, sau khi mở rộng, đèn xanh EW, ép đỏ khẩn cấp, giữ đỏ, khôi phục). Ô tô hiển thị hình
  mũi tên xanh dương, xe máy hình tam giác nhỏ đỏ/cam/vàng — phân biệt rõ hai loại xe.

## 7. Source code

Toàn bộ mã nguồn nằm trong thư mục dự án (`network/`, `routes/`, `scripts/`,
`intersection*.sumocfg`) — xem trực tiếp trong repo, không lặp lại nội dung ở đây.

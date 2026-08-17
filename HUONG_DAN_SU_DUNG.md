# Hướng dẫn sử dụng — Mô phỏng giao lộ SUMO

## 1. Yêu cầu cài đặt

```bash
pip install eclipse-sumo sumolib traci
```

Kiểm tra cài đặt đúng:
```bash
sumo --version
sumo-gui --version
```

## 2. Cấu trúc thư mục

```
network/    → định nghĩa node/cạnh + net.xml biên dịch (netconvert)
routes/     → luồng xe (.rou.xml) và chương trình đèn có thể chỉnh (.tls.add.xml)
scripts/    → mã Python điều khiển (tls_control.py, scenarios.py, run_simulation.py, record_demo.py)
media/      → ảnh + GIF demo đã ghi sẵn
intersection.sumocfg        → cấu hình chạy đầy đủ (~48 xe)
intersection_light.sumocfg  → cấu hình nhẹ (~10 xe), dùng khi xem GUI cho mượt
REPORT.md   → báo cáo kỹ thuật chi tiết, ánh xạ từng yêu cầu
```

## 3. Chạy mô phỏng (dòng lệnh)

Đứng ở thư mục gốc `D:\App\SUMO`, chạy:

```bash
# Headless (không giao diện) — nhanh, dùng để kiểm chứng logic
python scripts/run_simulation.py --scenario normal
python scripts/run_simulation.py --scenario extended_green
python scripts/run_simulation.py --scenario emergency

# Có giao diện đồ họa (SUMO-GUI), dùng bộ dữ liệu nhẹ cho mượt
python scripts/run_simulation.py --scenario emergency --gui --light
```

Tham số:
| Cờ | Ý nghĩa |
|---|---|
| `--scenario` | `normal` / `extended_green` / `emergency` (mặc định `normal`) |
| `--gui` | mở SUMO-GUI thay vì chạy ẩn |
| `--light` | dùng `intersection_light.sumocfg` (~10 xe) thay vì bộ đầy đủ (~48 xe) — chỉ nên dùng chung với `--gui` |

3 kịch bản:
- **normal**: chương trình đèn chạy mặc định, không can thiệp.
- **extended_green**: tại t=100s, tự động kéo dài pha đèn hiện tại thêm 20s.
- **emergency**: tại t=150s, ép toàn bộ đèn về đỏ trong 15s (mô phỏng nhường đường xe ưu tiên), sau đó tự khôi phục chương trình bình thường.

Chương trình tự kiểm tra: tổng số xe vào mạng phải nằm trong khoảng 20–60, nếu sai sẽ báo lỗi ngay (`assert`).

## 4. Xem GUI trực quan trên máy thật

Chạy trực tiếp trên máy cá nhân (ngoài môi trường sandbox/Claude Code, vì cửa sổ SUMO-GUI ở đó không ổn định):

```bash
python scripts/run_simulation.py --scenario emergency --gui --light
```

Muốn quay video màn hình thật, dùng phần mềm quay màn hình song song lúc chạy lệnh trên.

## 5. Xem demo có sẵn (ảnh + GIF)

Không cần chạy lại SUMO — mở trực tiếp:
- `media/demo.gif` — toàn bộ kịch bản: giao thông bình thường → mở rộng đèn xanh (t=40s) → lệnh khẩn cấp ép đỏ 10s (t=90s) → khôi phục.
- `media/01_start.png` … `media/07_resumed.png` — 7 ảnh chụp các mốc quan trọng.

Muốn tạo lại (ghi đè) bộ ảnh/GIF:
```bash
python scripts/record_demo.py
```

## 6. Điều khiển đèn bằng Python (API cho Agent Guard)

Trong `scripts/tls_control.py`:

```python
get_traffic_light_state("TL1")        # đọc trạng thái đèn hiện tại (state, phase, program, next_switch)
set_traffic_light("TL1", "GREEN", 30) # RED/YELLOW: ép toàn bộ đèn về màu đó N giây rồi tự khôi phục
                                       # GREEN: khôi phục chương trình bình thường ngay
extend_current_phase("TL1", 20)       # kéo dài pha đang chạy thêm N giây
```

Lưu ý: `set_traffic_light` là API đơn trục (điều khiển toàn bộ nút, không tách riêng từng hướng) — an toàn cho tình huống khẩn cấp, chưa hỗ trợ lệnh theo từng nhánh riêng lẻ.

## 7. Đổi chu kỳ đèn thủ công

Sửa số giây trong `routes/intersection.tls.add.xml` (chương trình `programID="1"`), sau đó chạy lại mô phỏng — không cần biên dịch lại `network/`.

## 8. Đọc thêm

Xem `REPORT.md` để biết kiến trúc tổng quan, bảng ánh xạ từng yêu cầu đề bài, và các giới hạn đã biết (ví dụ GUI không ổn định trong môi trường tự động).

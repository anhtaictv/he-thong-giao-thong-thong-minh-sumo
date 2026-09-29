# Báo cáo: Mô phỏng giao lộ thông minh bằng Eclipse SUMO (phục vụ tích hợp Agent Guard)

Phiên bản 0.2.0 — kiểm thử với Eclipse SUMO 1.27.1, Python 3.11.

## 1. Mục tiêu

Xây dựng một giao lộ 4 hướng có đèn tín hiệu và phương tiện lưu thông trên SUMO, quan sát
được trực quan trên SUMO-GUI, và điều khiển được đèn từ Python qua TraCI. Chuẩn bị sẵn một
cổng nhận lệnh đơn giản dạng `set_traffic_light("TL1","GREEN",30)` để sau này Agent Guard
gửi lệnh vào và kiểm duyệt lệnh.

## 2. Kiến trúc

```
                ┌───────────────────────── SUMO / SUMO-GUI ─────────────────────────┐
                │  intersection.net.xml   intersection.rou.xml   intersection.tls.add.xml
                │   (giao lộ TL1)          (36 xe, 6 loại)        (chu kỳ đèn "1")      │
                └──────────────────────────────▲────────────────────────────────────┘
                                               │ TraCI (socket)
   ┌───────────────────────────────────────────┴──────────────────────────────────┐
   │ tls_control.py   get_traffic_light_state · set_traffic_light · extend_current_phase
   │                  set_cycle · set_state (lệnh thô) · resume_program · tick      │
   └───────────────────────────────────────────▲──────────────────────────────────┘
                                               │ chỉ gọi khi lệnh được phép
   ┌───────────────────────────────────────────┴──────────────────────────────────┐
   │ safety_guard.py  chặn: hai trục cùng xanh · rẽ trái ưu tiên đối đầu luồng thẳng │
   │                  · Xanh→Đỏ không qua Vàng   (Agent Guard sẽ thay thế/bổ sung)  │
   └───────────────────────────────────────────▲──────────────────────────────────┘
                                               │
   ┌───────────────────────────────────────────┴──────────────────────────────────┐
   │ command_interface.py  phân tích lệnh văn bản / JSON bằng ast (không eval),      │
   │                       ghi nhật ký, máy chủ TCP 127.0.0.1:9000                   │
   └─────────▲──────────────────────────────▲─────────────────────────────────────┘
             │ lệnh định sẵn                 │ lệnh từ bên ngoài
      scenarios.py                    send_command.py / Agent Guard
      run_simulation.py · check_requirements.py · record_demo.py
```

Nguyên tắc thiết kế:

- Python không sửa file khi mô phỏng đang chạy. Mọi thay đổi đi qua TraCI.
- Lệnh cấp cao (`set_traffic_light`) luôn tự chèn Vàng 3s rồi Đỏ toàn phần 2s khi đổi hướng.
  Vì vậy lệnh hợp lệ không bao giờ gây chuyển Xanh→Đỏ đột ngột.
- Chỉ lệnh thô `set_state` mới có thể tạo trạng thái nguy hiểm. Lệnh này luôn phải qua
  `safety_guard` trước. `command_interface.set_validator(fn)` là chỗ để Agent Guard gắn bộ
  kiểm duyệt của mình.

## 3. Mô hình giao lộ và nhu cầu giao thông

| Thành phần | Mô tả |
|---|---|
| Nút | `TL1` (đèn tín hiệu) tại tâm; `N`, `S`, `E`, `W` cách 200 m |
| Cạnh | `N_in/N_out`, `S_in/S_out`, `E_in/E_out`, `W_in/W_out` — 1 làn, 50 km/h |
| Liên kết đèn | 12 link: mỗi hướng có rẽ phải / đi thẳng / rẽ trái (thứ tự N, E, S, W) |
| Chu kỳ đèn | Xanh B-N 42s → Vàng 3s → Đỏ toàn phần 2s → Xanh Đ-T 42s → Vàng 3s → Đỏ toàn phần 2s (94s) |
| Phương tiện | 12 luồng × 3 xe = **36 xe** (sedan, SUV, taxi, xe tải, xe buýt, xe máy), đến theo phân phối Poisson |
| Xe ưu tiên | 1 xe cứu thương (`vClass=emergency`), chỉ thêm trong kịch bản `emergency` / `demo` |

Lưu ý kỹ thuật: trong SUMO, `period="exp(X)"` nghĩa là trung bình **X xe/giây**, không phải
"1 xe mỗi X giây". Bản 0.1.0 viết `exp(180)`, tức 180 xe/giây cho mỗi luồng. Kết quả là hơn
345.000 xe được nạp và mô phỏng bị treo. Bản này dùng `exp(0.012)` kèm `number="3"`, nên số xe
luôn là 36 với mọi seed.

## 4. Ánh xạ yêu cầu

| # | Yêu cầu | Đáp ứng | Kiểm chứng |
|---|---|---|---|
| 1 | Cài đặt, chạy SUMO/SUMO-GUI | `pip install eclipse-sumo`; `run_simulation.py --gui` | `check_requirements.py` in phiên bản SUMO; video quay từ SUMO-GUI |
| 2 | Giao lộ 4 hướng | `network/*.nod.xml`, `*.edg.xml` → `netconvert` | kiểm tra đủ 8 cạnh + đèn `TL1` |
| 3 | 20–50 xe | 36 xe (+1 xe cứu thương) | `run_simulation.py` báo "ĐẠT" / thoát mã 1 nếu sai |
| 4 | Đèn Đỏ–Vàng–Xanh tự động | `intersection.tls.add.xml` | kiểm tra có đủ G/y/r và không có Xanh→Đỏ trực tiếp |
| 5 | Thay đổi chu kỳ / thời gian đèn | (a) sửa `duration` trong XML; (b) `extend_current_phase()`; (c) `set_cycle()` khi đang chạy | next_switch tăng đúng 20s; logic mới có pha 30s/50s |
| 6 | Python đọc trạng thái đèn | `get_traffic_light_state()` trả về state, màu từng hướng, pha, thời gian còn lại, chế độ | so khớp `GGgrrrGGgrrr` → Bắc/Nam xanh |
| 7 | Python gửi lệnh đổi trạng thái / thời gian | `set_traffic_light()`, `extend_current_phase()`, `set_cycle()` | GREEN hướng Đông: `yyy…` → `rrr…` → `rrrGGGrrrrrr` |
| 8 | 3 tình huống minh họa | `normal`, `extended_green`, `dangerous` (+ `emergency`, `demo`) | log console mục 6 |
| 9 | Nhận lệnh `set_traffic_light("TL1","GREEN",30)` từ bên ngoài | `command_interface.execute()` + TCP :9000 + `send_command.py`; hỗ trợ cả JSON | xanh kéo dài đúng 30s; gửi thử qua TCP thành công |
| 10 | Báo cáo, source, ảnh, video 2–3 phút | tài liệu này, `media/demo.mp4` (2:25), `demo.gif`, 8 ảnh | mục 7 |

## 5. API điều khiển đèn

```python
get_traffic_light_state("TL1")
# {'state': 'GGgrrrGGgrrr', 'directions': {'N':'GREEN','E':'RED','S':'GREEN','W':'RED'},
#  'phase': 0, 'phase_name': 'NS_GREEN', 'remaining': 37.0, 'mode': 'AUTO', ...}

set_traffic_light("TL1", "GREEN", 30)          # xanh trục đang/sắp chạy đúng 30s
set_traffic_light("TL1", "GREEN", 30, "EW")    # xanh trục Đông-Tây 30s
set_traffic_light("TL1", "GREEN", 20, "E")     # chỉ hướng Đông xanh 20s (xe cứu thương)
set_traffic_light("TL1", "RED", 10)            # đỏ toàn bộ 10s
set_traffic_light("TL1", "YELLOW", 10)         # vàng cảnh báo toàn bộ 10s
extend_current_phase("TL1", 20)                # kéo dài pha hiện tại 20s
set_cycle("TL1", green_ns=60, green_ew=30)     # đổi chu kỳ khi đang chạy
set_state("TL1", "GGgrrrGGgrrr", 10)           # lệnh thô — luôn qua safety_guard
resume_program("TL1")                          # quay lại chu kỳ tự động
```

Mọi tham số đều được kiểm tra: `duration` phải nằm trong 1–120s; ID đèn phải tồn tại; màu
chỉ gồm GREEN/YELLOW/RED; hướng chỉ gồm N/S/E/W/NS/EW. Sau khi hết thời gian lệnh, đèn tự quay
về chu kỳ tự động và có chuyển tiếp an toàn.

Lệnh từ bên ngoài (mỗi dòng một lệnh, mỗi phản hồi là một dòng JSON):

```text
set_traffic_light("TL1","GREEN",30)
{"command": "set_traffic_light", "args": ["TL1", "RED", 10]}
{"command": "set_traffic_light", "params": {"tls_id": "TL1", "color": "GREEN", "duration": 20, "direction": "E"}}
```

## 6. Kết quả các tình huống (log rút gọn)

**Tình huống 1: bình thường** (`--scenario normal`). Chu kỳ 94s chạy tự động, 36 xe, 0 va chạm.

```
t=     1s  [AUTO  ] NS_GREEN    còn  41.0s | Bắc=GREEN  Nam=GREEN  Đông=RED    Tây=RED
t=    43s  [AUTO  ] NS_YELLOW   còn   2.0s | Bắc=YELLOW Nam=YELLOW Đông=RED    Tây=RED
t=    46s  [AUTO  ] ALL_RED_1   còn   1.0s | Bắc=RED    Nam=RED    Đông=RED    Tây=RED
t=    48s  [AUTO  ] EW_GREEN    còn  41.0s | Bắc=RED    Nam=RED    Đông=GREEN  Tây=GREEN
```

**Tình huống 2: tăng thời gian đèn xanh** (`--scenario extended_green`)

```
t=    30s  >>> extend_current_phase("TL1", 20)       [OK] Kéo dài pha hiện tại thêm 20s
t=    63s  [AUTO  ] NS_YELLOW   (xanh Bắc-Nam kéo dài từ 42s lên 62s)
t=   150s  >>> set_traffic_light("TL1", "GREEN", 30)  [OK] Xanh hướng Bắc-Nam trong 30s
t=   181s  [AUTO  ] NS_YELLOW   (xanh giữ đúng 30s kể từ lệnh)
t=   250s  >>> set_cycle("TL1", 60, 30)               [OK] Chu kỳ mới 100s
t=   316s  [AUTO  ] EW_GREEN    còn  29.0s  … NS_GREEN còn 59.0s
```

**Tình huống 3: lệnh bất thường / nguy hiểm** (`--scenario dangerous`)

```
t=   100s  >>> set_state("TL1", "GGGGGGGGGGGG", 20)
            [CHẶN] trục Bắc-Nam và Đông-Tây cùng xanh (các luồng cắt nhau) (+4 vi phạm khác)
t=   104s  >>> set_state("TL1", "rrrrrrrrrrrr", 10)
            [CHẶN] chuyển Xanh -> Đỏ đột ngột không qua Vàng
t=   106s  >>> set_traffic_light("TL1", "GREEN", 999)   [LỖI] duration=999s ngoài phạm vi [1, 120]
t=   108s  >>> set_traffic_light("TL9", "GREEN", 30)    [LỖI] không tồn tại đèn 'TL9'
t=   110s  >>> set_traffic_light("TL1", "BLUE", 30)     [LỖI] màu 'BLUE' không hợp lệ
t=   112s  >>> __import__("os").system("echo hacked")    [LỖI] lệnh phải có dạng ten_lenh(tham_so, ...)
```

Chạy với `--unsafe` (tắt guard), lệnh xanh mọi hướng được áp dụng. Log cảnh báo
`!!! NGUY HIỂM` mỗi giây, và SUMO ghi nhận **va chạm thật trong giao lộ**
(`junction collision … collisions: 2`). Đây là minh chứng vì sao cần một lớp kiểm duyệt như
Agent Guard.

**Tình huống bổ sung: xe cứu thương** (`--scenario emergency`)

```
t=   140s  >>> Xe cứu thương 'ambulance_1' xuất hiện ở hướng Đông
t=   142s  >>> set_traffic_light("TL1", "GREEN", 25, "E")
t=   142s  [MANUAL] YELLOW   | Bắc=RED Nam=RED Đông=GREEN Tây=YELLOW
t=   145s  [MANUAL] ALL_RED  | Bắc=RED Nam=RED Đông=GREEN Tây=RED
t=   147s  [MANUAL] E_ONLY   | chỉ hướng Đông xanh 25s
t=   177s  [AUTO  ] NS_GREEN  (tự quay về chu kỳ)
t=   200s  >>> set_traffic_light("TL1", "RED", 15)    → Vàng 3s → Đỏ toàn phần 15s → tự khôi phục
```

**Tự kiểm tra** (`python scripts/check_requirements.py`): **13/13 kiểm tra đạt**.

## 7. Ảnh chụp và video demo

`scripts/record_demo.py` chạy kịch bản `demo` trên SUMO-GUI. Script chụp từng bước bằng
`traci.gui.screenshot()`, ghép bảng thông tin (đèn 4 hướng, chế độ, lệnh vừa gửi, cảnh báo) vào
khung hình, rồi xuất:

| File | Nội dung |
|---|---|
| `media/demo.mp4` | Video 2 phút 25 giây, 1280×720 (chạy nhanh ×2 so với thời gian mô phỏng) |
| `media/demo.gif` | Bản thu nhỏ để xem trong README |
| `media/01_normal.png` | Giao thông bình thường |
| `media/02_extended_green.png` | Sau khi kéo dài pha xanh |
| `media/03_green_command.png` | Lệnh `set_traffic_light("TL1","GREEN",30)` |
| `media/04_dangerous_blocked.png` | Lệnh xanh mọi hướng bị guard chặn |
| `media/05_unsafe_all_green.png` | Khi tắt guard: mọi hướng cùng xanh, cảnh báo nguy hiểm |
| `media/06_ambulance_east.png` | Chỉ hướng Đông xanh cho xe cứu thương |
| `media/07_all_red.png` | Đỏ toàn bộ giao lộ |
| `media/08_resumed.png` | Khôi phục chu kỳ tự động |

Nội dung video: giới thiệu → bình thường → tăng xanh → lệnh GREEN 30s → lệnh nguy hiểm bị chặn
→ tắt guard (mọi hướng xanh) → xe cứu thương hướng Đông → đỏ toàn bộ → khôi phục.

## 8. Giới hạn và hướng phát triển

- `safety_guard.py` mới là bộ kiểm tra tối thiểu dựa trên luật cố định. Agent Guard sẽ thay nó
  qua `command_interface.set_validator(fn)`. Nên bổ sung xác thực nguồn lệnh, giới hạn tần suất
  và kiểm tra theo ngữ cảnh (ví dụ số xe đang chờ).
- Cổng TCP chỉ lắng nghe trên `127.0.0.1` và chưa có xác thực, nên chỉ dùng trong môi trường thử nghiệm.
- Mỗi nhánh có 1 làn và rẽ trái dùng "xanh phải nhường" (`g`). Có thể mở rộng thành nhiều làn
  với pha rẽ trái riêng.

## 9. Các thay đổi so với bản 0.1.0

| Vấn đề ở bản 0.1.0 | Cách sửa |
|---|---|
| `exp(180)` khiến hơn 345.000 xe được nạp, mô phỏng treo, GUI hay bị ngắt | Sửa tốc độ đến thành `exp(0.012)` + `number="3"` → 36 xe cố định |
| Làn "quay đầu" (`bypass_to_*`) cắt thẳng qua tâm giao lộ, xe đi xuyên đèn | Bỏ các nút/cạnh bypass; `netconvert --no-turnarounds` |
| `set_traffic_light("TL1","GREEN",30)` bỏ qua tham số 30 | GREEN giữ xanh đúng `duration`, hỗ trợ hướng N/S/E/W/NS/EW |
| RED/YELLOW chuyển thẳng Xanh→Đỏ, không qua Vàng | Tự chèn Vàng 3s + Đỏ toàn phần 2s |
| Chưa có cổng nhận lệnh từ bên ngoài | `command_interface.py` (văn bản/JSON, TCP) + `send_command.py` |
| Kịch bản "nguy hiểm" thực chất là lệnh an toàn (đỏ toàn bộ) | Thêm kịch bản `dangerous` với các lệnh nguy hiểm thật + `safety_guard` |
| Không đổi được chu kỳ khi đang chạy | Thêm `set_cycle()` |
| `demo.gif`, `01_start.png` hỏng (1×1 pixel), không có video | Viết lại `record_demo.py`: `demo.mp4` 2:25, GIF, 8 ảnh mốc |
| Tài liệu lệch với code (số nút/cạnh, số xe, số khung hình) | Viết lại README, REPORT, hướng dẫn |

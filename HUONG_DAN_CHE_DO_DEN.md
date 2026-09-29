# Hướng dẫn: các chế độ và lệnh điều khiển đèn TL1

## 1. Chu kỳ tự động (mặc định)

Chương trình `programID="1"` trong `routes/intersection.tls.add.xml`:

| Pha | Tên | Thời gian | State | Ý nghĩa |
|---|---|---|---|---|
| 0 | NS_GREEN | 42s | `GGgrrrGGgrrr` | Bắc, Nam xanh (rẽ trái `g` phải nhường xe đi thẳng ngược chiều) |
| 1 | NS_YELLOW | 3s | `yyyrrryyyrrr` | Bắc, Nam vàng |
| 2 | ALL_RED_1 | 2s | `rrrrrrrrrrrr` | Đỏ toàn phần để giải phóng giao lộ |
| 3 | EW_GREEN | 42s | `rrrGGgrrrGGg` | Đông, Tây xanh |
| 4 | EW_YELLOW | 3s | `rrryyyrrryyy` | Đông, Tây vàng |
| 5 | ALL_RED_2 | 2s | `rrrrrrrrrrrr` | Đỏ toàn phần |

Thứ tự 12 ký tự: `0-2` Bắc, `3-5` Đông, `6-8` Nam, `9-11` Tây. Mỗi hướng gồm (rẽ phải, đi thẳng, rẽ trái).

## 2. Các lệnh

Các lệnh có thể gọi trực tiếp trong Python (`import tls_control as tls`). Cũng có thể gửi dưới
dạng văn bản qua `command_interface.execute(...)` hoặc TCP (`send_command.py`).

| Lệnh | Tác dụng |
|---|---|
| `get_traffic_light_state("TL1")` | Đọc state, màu từng hướng, pha, thời gian còn lại, chế độ AUTO/MANUAL |
| `set_traffic_light("TL1","GREEN",30)` | Giữ xanh trục đang (hoặc sắp) được xanh đúng 30s |
| `set_traffic_light("TL1","GREEN",30,"EW")` | Xanh trục Đông-Tây 30s (tự qua Vàng + Đỏ toàn phần nếu đang xanh Bắc-Nam) |
| `set_traffic_light("TL1","GREEN",20,"E")` | Chỉ hướng Đông xanh 20s (cả rẽ trái), 3 hướng còn lại đỏ |
| `set_traffic_light("TL1","RED",15)` | Đỏ toàn bộ 15s (qua Vàng trước nếu đang xanh) |
| `set_traffic_light("TL1","YELLOW",10)` | Vàng cảnh báo toàn bộ 10s |
| `extend_current_phase("TL1",20)` | Cộng thêm 20s cho pha đang chạy |
| `set_cycle("TL1",60,30)` | Đổi chu kỳ: xanh Bắc-Nam 60s, xanh Đông-Tây 30s (vàng 3s, đỏ toàn phần 2s) |
| `set_state("TL1","GGgrrrGGgrrr",10)` | Lệnh thô, đặt trực tiếp chuỗi state. **Luôn qua safety guard** |
| `resume_program("TL1")` | Hủy lệnh thủ công, quay về chu kỳ tự động |

Quy tắc chung:

- `duration` phải nằm trong khoảng 1–120s. Sai ID đèn, sai màu hoặc sai hướng đều bị từ chối và báo lỗi rõ ràng.
- Hết thời gian lệnh thì đèn tự quay về chu kỳ tự động, bắt đầu từ trục chưa được phục vụ.
- Mọi lần đổi hướng đều qua Vàng 3s rồi Đỏ toàn phần 2s.

## 3. Safety guard — lệnh nào bị chặn?

`scripts/safety_guard.py` kiểm tra các lệnh `set_state` và chặn khi:

1. Trục Bắc-Nam và Đông-Tây cùng xanh (các luồng cắt nhau).
2. Rẽ trái ưu tiên (`G`) cùng lúc với luồng thẳng ngược chiều đang xanh.
3. Đang xanh mà chuyển thẳng sang đỏ, không qua vàng.

Để Agent Guard thay bộ kiểm tra này:

```python
import command_interface as ci

def agent_guard_validator(command, args, kwargs):
    # ... gọi Agent Guard, trả về (True, "") nếu cho phép, (False, "lý do") nếu chặn
    return True, ""

ci.set_validator(agent_guard_validator)
```

## 4. Tạo tình huống mới

Thêm một mục vào `SCENARIOS` trong `scripts/scenarios.py`. Mỗi sự kiện gồm (thời điểm, lệnh dạng văn bản):

```python
SCENARIOS["gio_cao_diem"] = {
    "title": "Ưu tiên Bắc-Nam giờ cao điểm",
    "events": [
        (60,  'set_cycle("TL1", 70, 30)'),
        (300, 'set_cycle("TL1", 42, 42)'),
    ],
}
```

Sau đó chạy: `python scripts/run_simulation.py --scenario gio_cao_diem`.

Các sự kiện đặc biệt: `"__ambulance__"` thêm xe cứu thương ở hướng Đông;
`"__guard_off__"` / `"__guard_on__"` tắt/bật safety guard (chỉ dùng để minh họa).

## 5. Đọc log

```
t=   142s  xe=  7  [MANUAL] YELLOW      còn   3.0s | Bắc=RED    Nam=RED    Đông=GREEN  Tây=YELLOW | rrrGGgrrryyy
```

`t` là thời gian mô phỏng. `xe` là số xe đang trong mạng. `[AUTO]` nghĩa là chu kỳ tự động,
`[MANUAL]` nghĩa là đang thực hiện lệnh. Tiếp theo là tên pha, thời gian còn lại, màu đèn từng
hướng và chuỗi state gốc.
Dòng `>>>` là lệnh vừa gửi; `[OK]` / `[CHẶN]` / `[LỖI]` là kết quả.

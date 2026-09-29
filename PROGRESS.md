# Tiến độ phát triển: Mô phỏng giao lộ thông minh bằng Eclipse SUMO

## Trạng thái 10 yêu cầu (v0.2.0)

| # | Yêu cầu | Trạng thái | Ghi chú |
|---|---------|-----------|---------|
| 1 | Cài đặt và chạy SUMO/SUMO-GUI | ✅ | Kiểm thử với SUMO 1.27.1; `check_requirements.py` kiểm tra tự động |
| 2 | 01 giao lộ 4 hướng Bắc-Nam-Đông-Tây | ✅ | 5 nút, 8 cạnh, đèn `TL1`; đã bỏ các làn "quay đầu" đi xuyên giao lộ |
| 3 | 20-50 xe | ✅ | 36 xe cố định (12 luồng × 3), Poisson; +1 xe cứu thương ở kịch bản emergency |
| 4 | Đèn Đỏ-Vàng-Xanh tự động | ✅ | Xanh 42s / Vàng 3s / Đỏ toàn phần 2s |
| 5 | Thay đổi chu kỳ/thời gian đèn | ✅ | XML, `extend_current_phase()`, `set_cycle()` khi đang chạy |
| 6 | Python + TraCI đọc trạng thái đèn | ✅ | `get_traffic_light_state()` có màu từng hướng |
| 7 | Python gửi lệnh đổi trạng thái/thời gian | ✅ | `set_traffic_light()` có chuyển tiếp an toàn |
| 8 | ≥ 3 tình huống | ✅ | normal, extended_green, dangerous (+ emergency, demo) |
| 9 | Nhận lệnh `set_traffic_light("TL1","GREEN",30)` từ bên ngoài | ✅ | `command_interface.py` + TCP :9000 + `send_command.py` |
| 10 | Báo cáo + source + ảnh + video 2-3 phút | ✅ | `REPORT.md`, `media/demo.mp4` (2:25), GIF, 8 ảnh |

Kiểm tra lại bất kỳ lúc nào: `python scripts/check_requirements.py` (hiện đạt 13/13).

## Lịch sử phiên bản

**v0.2.0** (29/09/2026): sửa theo kết quả rà soát yêu cầu

- Sửa lỗi tốc độ sinh xe `exp(180)`. Lỗi này làm SUMO nạp hơn 345.000 xe, khiến mô phỏng
  treo và GUI bị ngắt.
- Bỏ các làn bypass "quay đầu" cắt thẳng qua tâm giao lộ.
- `set_traffic_light(..., "GREEN", 30)` giờ giữ xanh đúng 30s và hỗ trợ chọn hướng.
- Lệnh RED/YELLOW/đổi hướng luôn qua Vàng 3s rồi Đỏ toàn phần 2s.
- Thêm cổng nhận lệnh từ bên ngoài: văn bản, JSON và TCP.
- Thêm `safety_guard.py` và tình huống `dangerous` với lệnh nguy hiểm thật.
- Thêm `set_cycle()` để đổi chu kỳ khi đang chạy.
- Thêm tình huống xe cứu thương.
- Thêm `check_requirements.py` để tự kiểm tra yêu cầu.
- Viết lại `record_demo.py`: xuất video MP4 2:25, GIF và 8 ảnh mốc (bản cũ hỏng, chỉ 1×1 pixel).
- Cập nhật toàn bộ tài liệu cho khớp với code.

**v0.1.0** (17/08/2026): bản đầu tiên.

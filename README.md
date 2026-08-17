# Khảo sát, xây dựng hệ thống giao thông thông minh bằng SUMO

![version](https://img.shields.io/badge/version-0.1.0-blue)
![license](https://img.shields.io/badge/license-Apache--2.0-green)

Mô phỏng một giao lộ 4 nhánh (Bắc–Nam–Đông–Tây) với đèn tín hiệu tự động bằng
[Eclipse SUMO](https://eclipse.dev/sumo/), điều khiển qua TraCI (Python) — phục vụ
tích hợp với Agent Guard.

## Kiến trúc

```
network/*.nod/edg.xml  →  netconvert  →  network/intersection.net.xml (topology + TLS)
                                                     │
routes/intersection*.rou.xml ───────────────────────┤
routes/intersection.tls.add.xml ────────────────────┴──► intersection*.sumocfg ──► sumo / sumo-gui
                                                                    │
                                                              TraCI (socket)
                                                                    │
                                                        scripts/tls_control.py
                                                     (đọc/ghi trạng thái đèn)
                                                                    │
                                                          scripts/scenarios.py
                                             (normal / extended_green / emergency)
                                                                    │
                                        scripts/run_simulation.py (CLI) · scripts/record_demo.py (ảnh/GIF)
```

Giao lộ có nút trung tâm `TL1`, mỗi nhánh 1 làn dài 200m. `netconvert` tự sinh chương
trình đèn Đỏ–Vàng–Xanh (2 pha chính NS/EW + pha vàng chuyển tiếp). Python không sửa
file trong lúc chạy mà điều khiển đèn qua TraCI — giao thức socket chuẩn của SUMO.

## Cấu trúc thư mục

| File | Vai trò |
|---|---|
| `network/intersection.nod.xml`, `.edg.xml` | Định nghĩa node và cạnh của giao lộ |
| `network/intersection.net.xml` | Mạng lưới đã biên dịch (netconvert), gồm TLS tự sinh |
| `routes/intersection.rou.xml` | Nhu cầu giao thông chính: 12 luồng, ~48 xe/lượt, trộn `car` và `motorbike` |
| `routes/intersection_light.rou.xml` | Bản nhu cầu nhẹ (~10 xe) để xem GUI mượt |
| `routes/intersection.tls.add.xml` | Chương trình đèn có thể chỉnh sửa (đổi chu kỳ/thời gian) |
| `intersection.sumocfg` / `intersection_light.sumocfg` | Cấu hình chạy (net + route + additional, seed cố định) |
| `scripts/tls_control.py` | Điều khiển TraCI: đọc/đặt trạng thái đèn, mở rộng pha hiện tại |
| `scripts/scenarios.py` | 3 kịch bản minh họa |
| `scripts/run_simulation.py` | CLI chạy 1 kịch bản (`--scenario`, `--gui`, `--light`) |
| `scripts/record_demo.py` | Chụp ảnh + dựng GIF demo |

## Cách chạy

```bash
# Headless (nhanh, dùng để kiểm chứng)
python scripts/run_simulation.py --scenario normal
python scripts/run_simulation.py --scenario extended_green
python scripts/run_simulation.py --scenario emergency

# Xem trực quan (khuyến nghị chạy trên máy thật)
python scripts/run_simulation.py --scenario emergency --gui --light

# Chụp ảnh + dựng GIF demo
python scripts/record_demo.py
```

## Demo

![demo](media/demo.gif)

Xem chi tiết đầy đủ (ánh xạ yêu cầu, ghi chú/giới hạn) trong [REPORT.md](REPORT.md)
và hướng dẫn sử dụng trong [HUONG_DAN_SU_DUNG.md](HUONG_DAN_SU_DUNG.md).

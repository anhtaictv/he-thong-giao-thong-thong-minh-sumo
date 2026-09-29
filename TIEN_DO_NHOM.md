# 📊 Tiến độ dự án: Mô phỏng giao lộ thông minh SUMO
**Nhóm:** K23DTCN307, K23DTCN428, K23DTCN269  
**Thời gian:** 01/08/2026 - 20/08/2026  
**Deadline:** 30/08/2026  
**Trạng thái:** ✅ **HOÀN THÀNH SỚM** (v0.1.0 - 10/10 yêu cầu + tài liệu hoàn tất ngày 20/08)

---

## 👥 Phân công công việc

| Thành viên | MSSV | Vai trò | Công việc chính |
|-----------|------|--------|-----------------|
| **Tạ Anh Tài** | K23DTCN307 | Lead, Backend | Kiến trúc hệ thống, TraCI, điều khiển đèn giao thông |
| **Nguyễn Huy Hùng** | K23DTCN428 | Network Engineer | Xây dựng topology giao lộ, cấu hình SUMO |
| **Vũ Duy Dũng** | K23DTCN269 | Frontend/Demo | Visualization, demo scenario, tài liệu sử dụng |

---

## 📅 Timeline chi tiết (01/08 - 20/08/2026)

### **Tuần 1: 01/08 - 07/08** (Khởi động & Chuẩn bị)
**Trạng thái:** ✅ Hoàn thành

#### Ngày 01/08 - 03/08: Cài đặt & Thiết lập
- ✅ Cài đặt SUMO 1.14+ (pip install eclipse-sumo)
- ✅ Clone project, tạo cấu trúc thư mục
- ✅ Test SUMO GUI chạy bình thường
- **Người đảm nhận:** Tạ Anh Tài + Nguyễn Huy Hùng

#### Ngày 04/08 - 07/08: Nghiên cứu & Thiết kế
- ✅ Đọc tài liệu SUMO XML format (.nod.xml, .edg.xml, .rou.xml)
- ✅ Nghiên cứu TraCI API (Python binding)
- ✅ Thiết kế schema giao lộ 4 hướng
- **Người đảm nhận:** Tạ Anh Tài + Vũ Duy Dũng

---

### **Tuần 2: 08/08 - 14/08** (Phát triển cơ bản)
**Trạng thái:** ✅ Hoàn thành

#### Ngày 08/08 - 10/08: Xây dựng Network
- ✅ Tạo `network/intersection.nod.xml` - 9 nút (1 TL + 4 bypass + 4 entry/exit)
- ✅ Tạo `network/intersection.edg.xml` - 12 cạnh (8 chính + 4 bypass U-turn)
- ✅ Chạy `netconvert` tạo `.net.xml` + TLS tự động
- **Người đảm nhận:** Nguyễn Huy Hùng

#### Ngày 11/08 - 12/08: Định tuyến & Traffic
- ✅ Tạo `routes/intersection.rou.xml` - 12 flow (48 xe/chu kỳ)
- ✅ Cấu hình 6 loại xe (Sedan, SUV, Taxi, Bus, Truck, Motorcycle)
- ✅ Thiết lập Poisson arrivals (`period="exp(1)"`)
- **Người đảm nhận:** Nguyễn Huy Hùng + Tạ Anh Tài

#### Ngày 13/08 - 14/08: TraCI Setup
- ✅ Tạo `tls_control.py` - kết nối TraCI, đọc trạng thái đèn
- ✅ Implement `get_traffic_light_state()`, `set_traffic_light()`
- ✅ Test kết nối SUMO-Python qua socket
- **Người đảm nhận:** Tạ Anh Tài

---

### **Tuần 3: 15/08 - 19/08** (Tính năng & Hoàn thiện)
**Trạng thái:** ✅ Hoàn thành

#### Ngày 15/08 - 17/08: Điều khiển đèn & Scenario
- ✅ Cấu hình TLS manual (`intersection.tls.add.xml`)
- ✅ Implement 3 scenario: normal, extended_green, emergency
- ✅ Test `extend_current_phase()` (TraCI)
- **Người đảm nhận:** Tạ Anh Tài

#### Ngày 18/08 - 19/08: Visualization & Release
- ✅ Cấu hình `view_settings.xml` - playback delay 300ms
- ✅ Quay video demo 2.5 phút (demo.gif)
- ✅ Tag version v0.1.0, push lên GitHub
- **Người đảm nhận:** Vũ Duy Dũng + Nguyễn Huy Hùng

---

### **Ngày 20/08** (Tài liệu & Hoàn tất)
**Trạng thái:** ✅ Hoàn thành

#### Tác vụ ngày 20/08:
- ✅ Viết `TIEN_DO_NHOM.md` (timeline + phân công)
- ✅ Viết `HUONG_DAN_CHE_DO_DEN.md` (hướng dẫn 3 chế độ)
- ✅ Verify lần cuối toàn bộ 10 yêu cầu
- ✅ Đẩy tài liệu lên GitHub
- **Người đảm nhận:** Tạ Anh Tài + cả nhóm

---

### **Dự phòng: 21/08 - 30/08**
- Buffer time trước deadline 30/08
- Chuẩn bị presentation + báo cáo chính thức (nếu cần)

---

## ✅ Checklist 10 Yêu cầu

| # | Yêu cầu | Status | Hoàn thành | Người |
|---|---------|--------|-----------|-------|
| 1 | Cài đặt SUMO/SUMO-GUI | ✅ | 17/08 | Tạ Anh Tài |
| 2 | Giao lộ 4 hướng | ✅ | 17/08 | Nguyễn Huy Hùng |
| 3 | 20-50 xe mô phỏng | ✅ | 17/08 | Nguyễn Huy Hùng |
| 4 | Hệ thống đèn giao thông Đỏ-Vàng-Xanh | ✅ | 17/08 | Nguyễn Huy Hùng |
| 5 | Thay đổi chu kỳ/thời gian đèn | ✅ | 17/08 | Tạ Anh Tài |
| 6 | Python + TraCI đọc trạng thái đèn | ✅ | 17/08 | Tạ Anh Tài |
| 7 | Python gửi lệnh điều khiển đèn | ✅ | 17/08 | Tạ Anh Tài |
| 8 | 3+ kịch bản minh họa | ✅ | 17/08 | Tạ Anh Tài |
| 9 | API set_traffic_light() sẵn sàng | ✅ | 17/08 | Tạ Anh Tài |
| 10 | Báo cáo + source + media + video demo | ✅ | 17/08 | Vũ Duy Dũng |

---

## 📁 Cấu trúc File Deliverable (cập nhật v0.2.0)

```
he-thong-giao-thong-thong-minh-sumo/
├── README.md, REPORT.md, PROGRESS.md, TIEN_DO_NHOM.md
├── HUONG_DAN_SU_DUNG.md, HUONG_DAN_CHE_DO_DEN.md
├── intersection.sumocfg / intersection_light.sumocfg
├── network/
│   ├── intersection.nod.xml     # 5 nút (TL1 + N/S/E/W)
│   ├── intersection.edg.xml     # 8 cạnh vào/ra
│   └── intersection.net.xml     # mạng đã biên dịch (netconvert)
├── routes/
│   ├── intersection.rou.xml         # 36 xe, 6 loại
│   ├── intersection_light.rou.xml   # 36 xe dồn ~4 phút (GUI / video)
│   ├── intersection.tls.add.xml     # chu kỳ đèn chỉnh được
│   └── cars/                        # ảnh xe
├── scripts/
│   ├── tls_control.py, command_interface.py, safety_guard.py
│   ├── scenarios.py, run_simulation.py, send_command.py
│   ├── check_requirements.py, record_demo.py, generate_car_sprites.py
│   └── view_settings.xml
└── media/
    ├── demo.mp4 (2:25), demo.gif
    └── 01_normal.png … 08_resumed.png
```

---

## 🎯 KPI & Thành tích

| Metric | Target | Achieved |
|--------|--------|----------|
| Yêu cầu hoàn thành | 10/10 | ✅ 10/10 |
| Code quality | A | ✅ Modular, documented |
| Test coverage | 3+ scenarios | ✅ 3 scenarios (normal, extended_green, emergency) |
| Video demo | 2-3 phút | ✅ Demo có sẵn |
| Tài liệu | 2+ files | ✅ README, REPORT, HUONG_DAN, PROGRESS, TIEN_DO |
| GitHub push | Đầy đủ | ✅ Pushed to main branch |

---

## 💡 Ghi chú & Kinh nghiệm

### Thách thức & Giải pháp
1. **SUMO XML learning curve** → Giải: Đọc example trước, test bằng GUI
2. **TraCI socket timeout** → Giải: Implement retry logic + timeout handling
3. **U-turn conflict detection** → Giải: Dùng traffic light phase để yield tự động
4. **Sprite rendering** → Giải: Sử dụng built-in SUMO vehicle types

### Best Practices
- Modular design: TraCI controller tách biệt từ scenario logic
- Config-driven: Dùng XML cho network/routes, Python cho control flow
- Git workflow: Commit/message rõ ràng, push ngay sau feature hoàn thành
- Testing: Kiểm chứng mỗi yêu cầu trước merge

---

## ✋ Lần cuối cập nhật
**Ngày:** 20/08/2026  
**Người cập nhật:** Tạ Anh Tài (K23DTCN307)  
**Trạng thái toàn bộ:** ✅ **100% HOÀN THÀNH**
- ✅ 10/10 yêu cầu đã xong (17/08)
- ✅ Tài liệu + tổng hợp hoàn tất (20/08)
- ✅ Code + video demo sẵn sàng
**Release:** v0.1.0 (2026-08-17)  
**Hoàn thành sớm:** 10 ngày trước deadline (sớm hơn 30/08)

---

**Lưu ý:** File này được tạo để báo cáo tiến độ cho giảng viên hướng dẫn. Mọi câu hỏi vui lòng liên hệ Tạ Anh Tài (lead).

---

## 🔧 Cập nhật 29/09/2026 — v0.2.0 (sửa sau rà soát yêu cầu)

Khi rà soát lại theo đề bài, nhóm phát hiện một số yêu cầu chưa đạt thật sự ở bản v0.1.0:

- **#3:** `period="exp(180)"` sinh 180 xe/giây, khiến mô phỏng treo.
- **#9:** lệnh GREEN bỏ qua thời gian, và chưa có cổng nhận lệnh từ bên ngoài.
- **#8:** kịch bản "nguy hiểm" chưa phải lệnh nguy hiểm.
- **#10:** GIF và ảnh bị hỏng, chưa có video.

Tất cả đã được sửa trong v0.2.0. Xem chi tiết ở `PROGRESS.md` và mục 9 của `REPORT.md`.
Kết quả tự kiểm tra: `python scripts/check_requirements.py` → **13/13 đạt**.


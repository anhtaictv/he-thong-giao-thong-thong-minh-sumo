# 📖 Hướng dẫn: Cách thay đổi chế độ đèn giao thông

Trong dự án SUMO này, có **3 chế độ chính** cho đèn giao thông:
1. **Normal** - Đèn chạy tự động theo chương trình mặc định
2. **Extended Green** - Kéo dài thời gian xanh
3. **Emergency** - Bắt buộc đèn đỏ (ưu tiên cứu thương)

---

## 🚦 Hiểu cấu trúc code

### File quan trọng:
- `scripts/tls_control.py` - Thư viện điều khiển đèn giao thông
- `scripts/scenarios.py` - Các kịch bản/chế độ khác nhau
- `scripts/run_simulation.py` - Chạy mô phỏng với chế độ được chọn

---

## 1️⃣ Chế độ Normal (Bình thường)

### Lệnh chạy:
```bash
python scripts/run_simulation.py --scenario normal
```

### Giải thích:
- Đèn chạy theo chương trình mặc định (2 pha chính)
- Không can thiệp, để SUMO tự điều khiển
- Thích hợp để kiểm tra luồng giao thông bình thường

### Code trong `scenarios.py`:
```python
def run_normal():
    """Scenario 1: default program runs untouched."""
    return _step_loop()
```

---

## 2️⃣ Chế độ Extended Green (Kéo dài xanh)

### Lệnh chạy:
```bash
python scripts/run_simulation.py --scenario extended_green
```

### Giải thích:
- Tại **t=100 giây**, hệ thống sẽ **kéo dài thời gian xanh thêm 20 giây**
- Dùng để ưu tiên một hướng nhất định khi tắc nghẽn

### Code trong `scenarios.py`:
```python
def run_extended_green():
    """Scenario 2: extend the currently active phase by 20s at t=100s."""
    applied = {"done": False}

    def on_step(t):
        if not applied["done"] and t >= 100:
            print(f"t={t:6.0f}s  >>> extending current phase by 20s")
            tls.extend_current_phase("TL1", 20)  # Kéo dài 20 giây
            applied["done"] = True

    return _step_loop(on_step)
```

### Cách chỉnh sửa:
1. Thay `t >= 100` → Thời điểm bạn muốn kích hoạt (giây)
2. Thay `20` → Số giây muốn kéo dài

**Ví dụ:** Kéo dài xanh lúc t=50s thêm 30s
```python
if not applied["done"] and t >= 50:  # Lúc 50 giây
    tls.extend_current_phase("TL1", 30)  # Kéo dài 30 giây
    applied["done"] = True
```

---

## 3️⃣ Chế độ Emergency (Khẩn cấp)

### Lệnh chạy:
```bash
python scripts/run_simulation.py --scenario emergency
```

### Giải thích:
- Tại **t=150 giây**, hệ thống sẽ **bắt tất cả làn đèn thành đỏ 15 giây**
- Dùng khi có xe cứu hộ, cẩu cứu nạn cần ưu tiên
- Cho phép xe cứu hộ qua giao lộ an toàn

### Code trong `scenarios.py`:
```python
def run_emergency():
    """Scenario 3: abnormal/emergency override - force all-red for 15s at t=150s."""
    applied = {"done": False}

    def on_step(t):
        if not applied["done"] and t >= 150:
            print(f"t={t:6.0f}s  >>> EMERGENCY: set_traffic_light('TL1','RED',15)")
            tls.set_traffic_light("TL1", "RED", 15)  # Đỏ 15 giây
            applied["done"] = True

    return _step_loop(on_step)
```

### Cách chỉnh sửa:
1. Thay `t >= 150` → Thời điểm kích hoạt
2. Thay `"RED"` → Màu đèn (RED, YELLOW, hoặc GREEN để trở lại bình thường)
3. Thay `15` → Thời lượng (giây)

**Ví dụ:** Bắt đỏ tại t=120s trong 10 giây
```python
if not applied["done"] and t >= 120:
    tls.set_traffic_light("TL1", "RED", 10)
    applied["done"] = True
```

---

## 🎛️ Các hàm điều khiển (trong `tls_control.py`)

### 1. Đọc trạng thái đèn
```python
state = tls.get_traffic_light_state("TL1")
print(state["state"])   # "GrGr" (xanh-đỏ)
print(state["phase"])   # 0 (pha hiện tại)
```

### 2. Bắt đèn màu cụ thể
```python
# Bắt đỏ trong 15 giây
tls.set_traffic_light("TL1", "RED", 15)

# Bắt vàng trong 5 giây
tls.set_traffic_light("TL1", "YELLOW", 5)

# Trở lại chương trình bình thường
tls.set_traffic_light("TL1", "GREEN", 0)
```

### 3. Kéo dài pha hiện tại
```python
# Kéo dài pha hiện tại thêm 20 giây
tls.extend_current_phase("TL1", 20)
```

---

## 📝 Tạo chế độ mới

Để tạo chế độ mới, thêm vào `scenarios.py`:

```python
def run_custom():
    """Chế độ tuỳ chỉnh của bạn."""
    applied = {"done": False}

    def on_step(t):
        if not applied["done"] and t >= 50:  # Tại 50 giây
            print(f"t={t:6.0f}s  >>> Custom action")
            tls.set_traffic_light("TL1", "RED", 10)  # Đỏ 10s
            applied["done"] = True

    return _step_loop(on_step)

# Thêm vào từ điển SCENARIOS
SCENARIOS["custom"] = run_custom
```

Sau đó chạy:
```bash
python scripts/run_simulation.py --scenario custom
```

---

## 🔄 Ví dụ thực tế

### Ví dụ 1: Ưu tiên hướng Bắc-Nam vào giờ cao điểm
```python
def run_north_south_priority():
    """Ưu tiên hướng Bắc-Nam (NS) từ 100s đến 200s."""
    applied = {"done": False}

    def on_step(t):
        if not applied["done"] and t >= 100:
            print(f"t={t:6.0f}s  >>> Prioritizing North-South traffic")
            tls.extend_current_phase("TL1", 30)  # Kéo dài 30s
            applied["done"] = True

    return _step_loop(on_step)
```

### Ví dụ 2: Xe cứu hộ ưu tiên
```python
def run_ambulance_priority():
    """Ưu tiên xe cứu thương lúc 80 giây."""
    applied = {"done": False}

    def on_step(t):
        if not applied["done"] and t >= 80:
            print(f"t={t:6.0f}s  >>> AMBULANCE PRIORITY - All stop!")
            tls.set_traffic_light("TL1", "RED", 20)  # Dành 20s cho xe cứu hộ
            applied["done"] = True

    return _step_loop(on_step)
```

### Ví dụ 3: Tắc đường cấp bách
```python
def run_congestion_relief():
    """Khi phát hiện tắc, giảm chu kỳ."""
    last_check = -10
    
    def on_step(t):
        nonlocal last_check
        if t - last_check >= 10:
            last_check = t
            vehicle_count = traci.vehicle.getIDCount()
            if vehicle_count > 40:  # Nếu > 40 xe
                print(f"t={t:6.0f}s  >>> Congestion detected ({vehicle_count} vehicles)")
                tls.extend_current_phase("TL1", 15)  # Kéo xanh thêm 15s
    
    return _step_loop(on_step)
```

---

## 🏃 Chạy mô phỏng

### Chạy GUI (xem trực quan):
```bash
python scripts/run_simulation.py --scenario normal --gui
```

### Chạy command-line (nhanh):
```bash
python scripts/run_simulation.py --scenario extended_green
```

### Chạy tất cả 3 chế độ:
```bash
python scripts/run_simulation.py --scenario normal
python scripts/run_simulation.py --scenario extended_green
python scripts/run_simulation.py --scenario emergency
```

---

## 📊 Đọc kết quả

Trong khi chạy, bạn sẽ thấy output:
```
t=   0s  vehicles=  0d  phase=0 state=GrGr
t=  10s  vehicles=  5d  phase=0 state=GrGr
t= 100s  vehicles= 32d  phase=1 state=rGrG
t= 100s  >>> extending current phase by 20s
t= 110s  vehicles= 45d  phase=1 state=rGrG
t= 120s  vehicles= 48d  phase=0 state=GrGr
```

- `t`: Thời gian (giây)
- `vehicles`: Số xe trong mô phỏng
- `phase`: Pha đèn hiện tại (0=NS, 1=EW)
- `state`: Trạng thái từng làn (G=xanh, r=đỏ)

---

## ❓ Câu hỏi thường gặp

**Q: Làm sao để bắt đèn xanh lâu hơn lúc 200 giây?**
```python
if t >= 200:
    tls.extend_current_phase("TL1", 30)
```

**Q: Làm sao để khôi phục đèn bình thường sau khi bắt đỏ?**
```python
tls.set_traffic_light("TL1", "GREEN", 0)  # GREEN = quay lại bình thường
```

**Q: Có thể điều khiển từng hướng riêng không?**
Hiện tại là điều khiển toàn bộ giao lộ. Điều khiển per-hướng cần sửa `tls_control.py` (đó là future work).

---

**Ngày cập nhật:** 20/08/2026

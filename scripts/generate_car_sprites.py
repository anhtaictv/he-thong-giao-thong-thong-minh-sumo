from PIL import Image, ImageDraw


WIDTH = 256
HEIGHT = 512


def create_car(filename, body_width=150, body_length=400,
                body_color=(180, 180, 180, 255), roof_color=None):
    """
    Tạo sprite xe nhìn từ trên xuống.
    Nền trong suốt. Màu thân xe tùy chỉnh qua body_color, mui xe tối hơn
    thân xe một mức trừ khi truyền roof_color riêng.
    """

    if roof_color is None:
        r, g, b, a = body_color
        roof_color = (max(r - 60, 0), max(g - 60, 0), max(b - 60, 0), a)

    img = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(img)

    cx = WIDTH // 2

    left = cx - body_width // 2
    right = cx + body_width // 2

    top = (HEIGHT - body_length) // 2
    bottom = top + body_length

    # -----------------------------
    # Bóng xe
    # -----------------------------

    draw.rounded_rectangle(
        (
            left + 8,
            top + 10,
            right + 8,
            bottom + 10
        ),
        radius=35,
        fill=(0, 0, 0, 70)
    )

    # -----------------------------
    # Thân xe
    # -----------------------------

    draw.rounded_rectangle(
        (
            left,
            top,
            right,
            bottom
        ),
        radius=35,
        fill=body_color
    )

    # -----------------------------
    # Mui xe
    # -----------------------------

    roof_top = top + 105
    roof_bottom = bottom - 100

    draw.rounded_rectangle(
        (
            left + 15,
            roof_top,
            right - 15,
            roof_bottom
        ),
        radius=28,
        fill=roof_color
    )

    # -----------------------------
    # Kính trước
    # -----------------------------

    draw.polygon(
        [
            (left + 25, roof_top + 20),
            (right - 25, roof_top + 20),
            (right - 35, roof_top + 90),
            (left + 35, roof_top + 90),
        ],
        fill=(210, 225, 235, 220)
    )

    # -----------------------------
    # Kính sau
    # -----------------------------

    draw.polygon(
        [
            (left + 35, roof_bottom - 90),
            (right - 35, roof_bottom - 90),
            (right - 25, roof_bottom - 20),
            (left + 25, roof_bottom - 20),
        ],
        fill=(190, 210, 225, 220)
    )

    # -----------------------------
    # Gương
    # -----------------------------

    draw.ellipse(
        (
            left - 14,
            roof_top + 40,
            left + 8,
            roof_top + 75
        ),
        fill=(70, 70, 70, 255)
    )

    draw.ellipse(
        (
            right - 8,
            roof_top + 40,
            right + 14,
            roof_top + 75
        ),
        fill=(70, 70, 70, 255)
    )

    # -----------------------------
    # Đèn trước
    # -----------------------------

    draw.rounded_rectangle(
        (
            left + 20,
            top + 18,
            left + 55,
            top + 42
        ),
        radius=8,
        fill=(245, 245, 220, 255)
    )

    draw.rounded_rectangle(
        (
            right - 55,
            top + 18,
            right - 20,
            top + 42
        ),
        radius=8,
        fill=(245, 245, 220, 255)
    )

    # -----------------------------
    # Đèn sau
    # -----------------------------

    draw.rounded_rectangle(
        (
            left + 20,
            bottom - 42,
            left + 55,
            bottom - 18
        ),
        radius=8,
        fill=(180, 30, 30, 255)
    )

    draw.rounded_rectangle(
        (
            right - 55,
            bottom - 42,
            right - 20,
            bottom - 18
        ),
        radius=8,
        fill=(180, 30, 30, 255)
    )

    # -----------------------------
    # Bánh xe
    # -----------------------------

    wheel_w = 25
    wheel_h = 70

    for y in [
        top + 95,
        bottom - 165
    ]:

        draw.rounded_rectangle(
            (
                left - 12,
                y,
                left + wheel_w - 12,
                y + wheel_h
            ),
            radius=10,
            fill=(25, 25, 25, 255)
        )

        draw.rounded_rectangle(
            (
                right - wheel_w + 12,
                y,
                right + 12,
                y + wheel_h
            ),
            radius=10,
            fill=(25, 25, 25, 255)
        )

    img.save(filename)


# Mỗi loại xe một màu thân xe riêng để phân biệt trong media/vehicles/.
CAR_TYPES = {
    "sedan": {"body_width": 150, "body_length": 400, "body_color": (60, 90, 180, 255)},   # xanh dương
    "suv":   {"body_width": 175, "body_length": 410, "body_color": (60, 140, 70, 255)},   # xanh lá
    "taxi":  {"body_width": 150, "body_length": 400, "body_color": (235, 200, 40, 255)},  # vàng
    "truck": {"body_width": 180, "body_length": 470, "body_color": (150, 40, 40, 255)},   # đỏ
}


def demo():
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        for name, kwargs in CAR_TYPES.items():
            path = os.path.join(tmp, f"{name}.png")
            create_car(path, **kwargs)
            assert os.path.exists(path), f"{name} sprite was not created"
            with Image.open(path) as img:
                assert img.size == (WIDTH, HEIGHT), f"{name} sprite has wrong size"
    print("demo() OK: all sprites generated with correct size")


if __name__ == "__main__":
    import os

    out_dir = os.path.join(os.path.dirname(__file__), "..", "media", "vehicles")
    os.makedirs(out_dir, exist_ok=True)

    for name, kwargs in CAR_TYPES.items():
        create_car(os.path.join(out_dir, f"{name}.png"), **kwargs)

    demo()

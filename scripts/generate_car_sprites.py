from PIL import Image, ImageDraw
import os

CANVAS_W = 256
CANVAS_H = 512


def save_vehicle(
    filename,
    body_w,
    body_h,
    body_color=(180, 180, 180, 255),
    roof_color=None,
    roof_ratio=0.55,
    wheel_w=25,
    wheel_h=70,
    bus=False,
    truck=False,
    motorcycle=False,
):
    if roof_color is None:
        r, g, b, a = body_color
        roof_color = (max(r - 90, 0), max(g - 90, 0), max(b - 90, 0), a)

    img = Image.new(
        "RGBA",
        (CANVAS_W, CANVAS_H),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(img)

    cx = CANVAS_W // 2

    left = cx - body_w // 2
    right = cx + body_w // 2

    top = (CANVAS_H - body_h) // 2
    bottom = top + body_h

    # Shadow
    draw.rounded_rectangle(
        (
            left + 8,
            top + 10,
            right + 8,
            bottom + 10
        ),
        radius=30,
        fill=(0, 0, 0, 60)
    )

    if motorcycle:

        draw.rounded_rectangle(
            (
                cx - 18,
                top + 40,
                cx + 18,
                bottom - 40
            ),
            radius=12,
            fill=body_color
        )

        draw.ellipse(
            (
                cx - 35,
                top + 30,
                cx + 35,
                top + 100
            ),
            fill=(40, 40, 40, 255)
        )

        draw.ellipse(
            (
                cx - 35,
                bottom - 100,
                cx + 35,
                bottom - 30
            ),
            fill=(40, 40, 40, 255)
        )

        draw.line(
            (
                cx - 30,
                top + 80,
                cx + 30,
                top + 50
            ),
            fill=(120, 120, 120, 255),
            width=8
        )

        img.save(filename)
        return

    # Body
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

    roof_top = top + int(body_h * 0.25)
    roof_bottom = roof_top + int(body_h * roof_ratio)

    draw.rounded_rectangle(
        (
            left + 18,
            roof_top,
            right - 18,
            roof_bottom
        ),
        radius=25,
        fill=roof_color
    )

    # windshield
    draw.polygon(
        [
            (left + 25, roof_top + 20),
            (right - 25, roof_top + 20),
            (right - 35, roof_top + 90),
            (left + 35, roof_top + 90)
        ],
        fill=(230, 230, 230, 220)
    )

    # rear glass
    draw.polygon(
        [
            (left + 35, roof_bottom - 90),
            (right - 35, roof_bottom - 90),
            (right - 25, roof_bottom - 20),
            (left + 25, roof_bottom - 20)
        ],
        fill=(220, 220, 220, 220)
    )

    # headlights
    draw.rounded_rectangle(
        (
            left + 15,
            top + 15,
            left + 55,
            top + 40
        ),
        radius=8,
        fill=(255, 255, 255, 255)
    )

    draw.rounded_rectangle(
        (
            right - 55,
            top + 15,
            right - 15,
            top + 40
        ),
        radius=8,
        fill=(255, 255, 255, 255)
    )

    # tail lights
    draw.rounded_rectangle(
        (
            left + 15,
            bottom - 40,
            left + 55,
            bottom - 15
        ),
        radius=8,
        fill=(180, 30, 30, 255)
    )

    draw.rounded_rectangle(
        (
            right - 55,
            bottom - 40,
            right - 15,
            bottom - 15
        ),
        radius=8,
        fill=(180, 30, 30, 255)
    )

    # wheels
    wheel_positions = [
        top + 90,
        bottom - 170
    ]

    for y in wheel_positions:

        draw.rounded_rectangle(
            (
                left - 10,
                y,
                left + wheel_w,
                y + wheel_h
            ),
            radius=8,
            fill=(40, 40, 40, 255)
        )

        draw.rounded_rectangle(
            (
                right - wheel_w,
                y,
                right + 10,
                y + wheel_h
            ),
            radius=8,
            fill=(40, 40, 40, 255)
        )

    if bus:

        for i in range(6):
            x1 = left + 25 + i * 25

            draw.rectangle(
                (
                    x1,
                    top + 110,
                    x1 + 18,
                    top + 160
                ),
                fill=(240, 240, 240, 255)
            )

    if truck:

        draw.rectangle(
            (
                left + 10,
                top + 120,
                right - 10,
                bottom - 90
            ),
            outline=(100, 100, 100, 255),
            width=4
        )

    img.save(filename)


# Mỗi loại xe một màu riêng, khớp với color="..." trong vType (routes/*.rou.xml).
VEHICLE_TYPES = {
    "sedan":      {"body_w": 150, "body_h": 390, "body_color": (50, 100, 220, 255)},
    "suv":        {"body_w": 180, "body_h": 420, "body_color": (220, 60, 60, 255)},
    "taxi":       {"body_w": 150, "body_h": 390, "body_color": (255, 200, 40, 255)},
    "bus":        {"body_w": 190, "body_h": 470, "body_color": (50, 180, 50, 255), "bus": True},
    "truck":      {"body_w": 190, "body_h": 500, "body_color": (120, 120, 120, 255), "truck": True},
    "motorcycle": {"body_w": 60, "body_h": 260, "body_color": (180, 50, 180, 255), "motorcycle": True},
}


def demo():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        for name, kwargs in VEHICLE_TYPES.items():
            path = os.path.join(tmp, f"{name}.png")
            save_vehicle(path, **kwargs)
            assert os.path.exists(path), f"{name} sprite was not created"
            with Image.open(path) as img:
                assert img.size == (CANVAS_W, CANVAS_H), f"{name} sprite has wrong size"
    print("demo() OK: all sprites generated with correct size")


def generate(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, kwargs in VEHICLE_TYPES.items():
        save_vehicle(os.path.join(out_dir, f"{name}.png"), **kwargs)
    print(f"Generated {len(VEHICLE_TYPES)} vehicle sprites in {out_dir}")


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "routes", "cars")
    generate(out_dir)
    demo()

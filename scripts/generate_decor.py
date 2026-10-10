"""Sinh phần trang trí cho SUMO-GUI: thảm cỏ 4 góc + hàng cây dọc 2 bên đường.

Tạo ra:
  network/tree_*.png      ảnh tán cây nhìn từ trên xuống (4 loại)
  network/decor.add.xml   polygon (cỏ) + POI (cây), được nạp qua additional-files trong *.sumocfg

Chỉ để hiển thị, không ảnh hưởng tới xe. Chạy lại khi đổi kích thước giao lộ:
    python scripts/generate_decor.py
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

NET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "network")
CENTER = 200          # tâm giao lộ trong toạ độ net (netOffset 200,200)
ARM = 200             # chiều dài mỗi nhánh đường
ROAD_HALF = 9.6       # 3 làn x 3.2m mỗi chiều
GRASS_GAP = 2.5       # vỉa hè giữa mép đường và cỏ
TREE_OFFSET = 15      # khoảng cách hàng cây tới tim đường
TREE_START, TREE_STEP = 35, 18
TREE_SIZE = (7, 10)   # đường kính tán (m), ngẫu nhiên trong khoảng này


# Loại cây: (màu tán tối, màu tán sáng, màu hoa hoặc None)
TREE_KINDS = {
    "tree_green":  ((22, 78, 30), (126, 196, 84), None),
    "tree_dark":   ((14, 58, 34), (78, 150, 70), None),
    "tree_phuong": ((26, 84, 32), (118, 186, 76), (226, 52, 36)),    # phượng vĩ - hoa đỏ
    "tree_banglang": ((24, 80, 36), (112, 180, 82), (176, 112, 214)),  # bằng lăng - hoa tím
}
SPRITE = 512          # vẽ ở độ phân giải cao rồi thu nhỏ để mịn cạnh
SPRITE_OUT = 160


def _mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _shaded_disc(d, cx, cy, r, dark, light):
    """Hình tròn tô chuyển màu: mép tối, sáng dần về phía nguồn sáng (góc trên-trái)."""
    steps = max(int(r), 1)
    for i in range(steps, 0, -1):
        t = 1 - i / steps
        rr = r * i / steps
        ox, oy = cx - r * 0.35 * t, cy - r * 0.35 * t
        d.ellipse([ox - rr, oy - rr, ox + rr, oy + rr], fill=_mix(dark, light, t ** 0.8) + (255,))


def make_tree_png(path, dark, light, flower, seed):
    rnd = random.Random(seed)
    c, R = SPRITE / 2, SPRITE * 0.36
    img = Image.new("RGBA", (SPRITE, SPRITE), (0, 0, 0, 0))

    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))     # bóng đổ lệch xuống dưới-phải, nhoè
    ImageDraw.Draw(shadow).ellipse([c - R + 30, c - R + 36, c + R + 30, c + R + 36], fill=(0, 0, 0, 110))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))

    d = ImageDraw.Draw(img)
    lobes = [(c + R * 0.55 * math.cos(a), c + R * 0.55 * math.sin(a), R * rnd.uniform(0.5, 0.62))
             for a in [i * 2 * math.pi / 7 + rnd.uniform(-0.3, 0.3) for i in range(7)]]
    for x, y, r in lobes:                                   # vòng ngoài: các chùm lá
        _shaded_disc(d, x, y, r, dark, _mix(dark, light, 0.75))
    _shaded_disc(d, c - 8, c - 8, R * 0.62, dark, light)    # chùm giữa, sáng nhất

    for _ in range(260):                                    # lấm tấm lá để tán cây có kết cấu
        a, dist = rnd.uniform(0, 2 * math.pi), R * math.sqrt(rnd.random()) * 0.95
        x, y, r = c + dist * math.cos(a), c + dist * math.sin(a), rnd.uniform(5, 13)
        lit = 0.5 + 0.5 * (-(x - c) - (y - c)) / (2 * R)    # phía trên-trái sáng hơn
        col = _mix(dark, light, max(0, min(1, lit + rnd.uniform(-0.25, 0.2))))
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))

    if flower:
        for _ in range(110):
            a, dist = rnd.uniform(0, 2 * math.pi), R * math.sqrt(rnd.random()) * 0.92
            x, y, r = c + dist * math.cos(a), c + dist * math.sin(a), rnd.uniform(5, 10)
            col = _mix(flower, (255, 255, 255), rnd.uniform(0, 0.35))
            d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))

    img.resize((SPRITE_OUT, SPRITE_OUT), Image.Resampling.LANCZOS).save(path)


def grass_polygons():
    lo, hi = CENTER - ROAD_HALF - GRASS_GAP, CENTER + ROAD_HALF + GRASS_GAP
    a, b = CENTER - ARM, CENTER + ARM
    quads = [(a, a, lo, lo), (hi, a, b, lo), (a, hi, lo, b), (hi, hi, b, b)]
    return [f'    <poly id="grass_{i}" type="grass" color="110,165,80" fill="1" layer="-2" '
            f'shape="{x0},{y0} {x1},{y0} {x1},{y1} {x0},{y1}"/>' for i, (x0, y0, x1, y1) in enumerate(quads)]


def tree_positions():
    """[(x, y, loại cây)] — hàng cây ven đường xen kẽ cây hoa / cây xanh; cây rải rác trên bãi cỏ."""
    pos = []
    for k, dist in enumerate(range(TREE_START, ARM - 5, TREE_STEP)):
        for sign in (1, -1):              # 2 phía tâm giao lộ
            for side in (1, -1):          # 2 bên đường
                pos.append((CENTER + sign * dist, CENTER + side * TREE_OFFSET,      # trục Đông-Tây: phượng
                            "tree_phuong" if k % 2 == 0 else "tree_green"))
                pos.append((CENTER + side * TREE_OFFSET, CENTER + sign * dist,      # trục Bắc-Nam: bằng lăng
                            "tree_banglang" if k % 2 == 0 else "tree_green"))
    rnd = random.Random(7)                # cố định để lần nào sinh ra cũng giống nhau
    for _ in range(40):
        x, y = rnd.uniform(30, ARM - 25), rnd.uniform(30, ARM - 25)
        kind = rnd.choices(list(TREE_KINDS), weights=(4, 4, 1, 1))[0]
        pos.append((CENTER + rnd.choice((1, -1)) * x, CENTER + rnd.choice((1, -1)) * y, kind))
    return pos


def main():
    for seed, (kind, (dark, light, flower)) in enumerate(TREE_KINDS.items()):
        make_tree_png(os.path.join(NET_DIR, f"{kind}.png"), dark, light, flower, seed)
    rnd = random.Random(11)
    trees = []
    for i, (x, y, kind) in enumerate(tree_positions()):
        size = rnd.uniform(*TREE_SIZE)
        trees.append(f'    <poi id="tree_{i}" type="{kind}" x="{x:.1f}" y="{y:.1f}" color="255,255,255" layer="5" '
                     f'imgFile="{kind}.png" width="{size:.1f}" height="{size:.1f}"/>')
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           "<!-- Sinh tự động bởi scripts/generate_decor.py — chỉ để trang trí GUI. -->",
           "<additional>"] + grass_polygons() + trees + ["</additional>", ""]
    with open(os.path.join(NET_DIR, "decor.add.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(xml))
    print(f"Đã tạo {len(trees)} cây ({len(TREE_KINDS)} loại) + 4 bãi cỏ -> network/decor.add.xml")


if __name__ == "__main__":
    main()

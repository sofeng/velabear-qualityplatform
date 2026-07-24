from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH = 2400
HEIGHT = 415

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "frontend" / "public" / "assets"
OUT_PATH = OUT_DIR / "ai-session-fullchain-banner.png"

FONT_REGULAR = Path("C:/Windows/Fonts/msyh.ttc")
FONT_BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold and FONT_BOLD.exists() else FONT_REGULAR
    return ImageFont.truetype(str(path), size=size)


def rounded_rect(draw: ImageDraw.ImageDraw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def add_soft_shadow(base: Image.Image, xy, radius, fill, blur=18, offset=(0, 10), alpha=80):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(shadow)
    x1, y1, x2, y2 = xy
    ox, oy = offset
    d.rounded_rectangle((x1 + ox, y1 + oy, x2 + ox, y2 + oy), radius=radius, fill=(11, 35, 68, alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    layer.alpha_composite(shadow)
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(xy, radius=radius, fill=fill)
    base.alpha_composite(layer)


def gradient_background() -> Image.Image:
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    px = img.load()
    c1 = (246, 249, 252)
    c2 = (226, 238, 246)
    c3 = (240, 245, 238)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            tx = x / (WIDTH - 1)
            ty = y / (HEIGHT - 1)
            mix = min(1.0, max(0.0, 0.75 * tx + 0.25 * ty))
            r = int(c1[0] * (1 - mix) + c2[0] * mix)
            g = int(c1[1] * (1 - mix) + c2[1] * mix)
            b = int(c1[2] * (1 - mix) + c2[2] * mix)
            warm = max(0, 1 - abs(tx - 0.78) * 2.2 - abs(ty - 0.48) * 1.6)
            r = int(r * (1 - 0.18 * warm) + c3[0] * 0.18 * warm)
            g = int(g * (1 - 0.18 * warm) + c3[1] * 0.18 * warm)
            b = int(b * (1 - 0.18 * warm) + c3[2] * 0.18 * warm)
            px[x, y] = (r, g, b, 255)
    return img


def draw_background_details(img: Image.Image):
    draw = ImageDraw.Draw(img, "RGBA")
    for i in range(13):
        x = 1480 + i * 92
        draw.line((x, 18, x - 210, HEIGHT - 18), fill=(118, 144, 166, 28), width=1)
    for i in range(8):
        x = 1450 + i * 128
        y = 56 + (i % 3) * 78
        draw.ellipse((x, y, x + 5, y + 5), fill=(32, 94, 130, 55))
    draw.rounded_rectangle((0, 0, WIDTH - 1, HEIGHT - 1), radius=0, outline=(201, 213, 223, 255), width=1)


def draw_text_block(img: Image.Image):
    draw = ImageDraw.Draw(img, "RGBA")
    badge_font = font(28, True)
    title_font = font(68, True)
    sub_font = font(33)
    small_font = font(24)

    rounded_rect(draw, (92, 58, 338, 102), 22, fill=(25, 111, 147, 255))
    draw.text((122, 63), "AI 会话全链路", font=badge_font, fill=(255, 255, 255, 255))

    draw.text((92, 132), "从对话到交付的", font=title_font, fill=(17, 43, 68, 255))
    draw.text((92, 214), "AI 开发工作台", font=title_font, fill=(17, 43, 68, 255))

    sub = "需求理解、上下文编排、代码生成、验证修复、部署交付，全程在会话中闭环。"
    draw.text((96, 311), sub, font=sub_font, fill=(70, 91, 110, 255))

    pills = ["上下文沉淀", "技能/MCP", "工作区治理", "部署交付"]
    x = 96
    for pill in pills:
        w = int(draw.textlength(pill, font=small_font)) + 38
        rounded_rect(draw, (x, 358, x + w, 392), 17, fill=(255, 255, 255, 190), outline=(203, 216, 225, 255))
        draw.text((x + 19, 361), pill, font=small_font, fill=(42, 78, 103, 255))
        x += w + 14


def draw_flow_cards(img: Image.Image):
    draw = ImageDraw.Draw(img, "RGBA")
    card_font = font(26, True)
    meta_font = font(19)
    tiny_font = font(16)

    panel = (1170, 48, 2304, 366)
    add_soft_shadow(img, panel, 30, fill=(255, 255, 255, 218), blur=22, offset=(0, 12), alpha=48)
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle(panel, radius=30, outline=(198, 213, 225, 210), width=1)

    header_y = 75
    draw.text((1210, header_y), "AI 会话驱动开发链路", font=font(31, True), fill=(22, 47, 68, 255))
    draw.text((1212, header_y + 44), "Conversation-first development pipeline", font=font(18), fill=(93, 113, 130, 255))

    steps = [
        ("01", "需求输入", "业务资料 / 原型 / 任务"),
        ("02", "会话编排", "上下文 / Skill / MCP"),
        ("03", "代码生成", "前端 / 后端 / 测试"),
        ("04", "验证修复", "运行 / 日志 / 迭代"),
        ("05", "部署交付", "镜像 / 环境 / 追踪"),
    ]
    start_x = 1210
    y = 168
    card_w = 196
    card_h = 124
    gap = 19
    for idx, (num, title, meta) in enumerate(steps):
        x = start_x + idx * (card_w + gap)
        fill = (245, 249, 252, 255) if idx % 2 == 0 else (242, 248, 245, 255)
        rounded_rect(draw, (x, y, x + card_w, y + card_h), 18, fill=fill, outline=(207, 219, 229, 255))
        draw.text((x + 20, y + 17), num, font=tiny_font, fill=(25, 111, 147, 255))
        draw.text((x + 20, y + 44), title, font=card_font, fill=(25, 50, 72, 255))
        draw.text((x + 20, y + 82), meta, font=meta_font, fill=(84, 104, 121, 255))
        if idx < len(steps) - 1:
            ax = x + card_w + 4
            ay = y + card_h // 2
            draw.line((ax, ay, ax + gap - 8, ay), fill=(59, 124, 150, 155), width=3)
            draw.polygon([(ax + gap - 8, ay), (ax + gap - 17, ay - 6), (ax + gap - 17, ay + 6)], fill=(59, 124, 150, 170))

    # Mini code/chat pane.
    pane = (1506, 307, 2264, 346)
    rounded_rect(draw, pane, 14, fill=(20, 45, 67, 245), outline=(44, 82, 104, 255))
    draw.text((1530, 315), "AI Session: plan -> code -> test -> deploy", font=font(19), fill=(214, 232, 237, 255))
    for i in range(4):
        x = 1862 + i * 78
        draw.rounded_rectangle((x, 319, x + 50, 326), radius=4, fill=(105, 169, 154, 180))


def draw_nodes(img: Image.Image):
    draw = ImageDraw.Draw(img, "RGBA")
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        cx = 1076 + math.cos(rad) * 76
        cy = 164 + math.sin(rad) * 76
        draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(25, 111, 147, 120))
        draw.line((1076, 164, cx, cy), fill=(25, 111, 147, 30), width=1)
    draw.ellipse((1022, 110, 1130, 218), fill=(255, 255, 255, 188), outline=(183, 204, 214, 210), width=2)
    draw.text((1045, 139), "AI", font=font(41, True), fill=(25, 91, 121, 255))
    draw.text((1038, 186), "Session", font=font(16), fill=(76, 101, 116, 255))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = gradient_background()
    draw_background_details(img)
    draw_text_block(img)
    draw_nodes(img)
    draw_flow_cards(img)
    img = img.convert("RGB")
    img.save(OUT_PATH, "PNG", optimize=True)
    print(OUT_PATH)
    print(f"{img.size[0]}x{img.size[1]}")


if __name__ == "__main__":
    main()

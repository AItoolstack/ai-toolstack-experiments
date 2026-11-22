"""Social cards, 1200x630 (style guide section 6). Same drawing as claude/diagram-kit.md social.py."""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
F = "/usr/share/fonts/opentype/inter/"
PAPER, NAVY, INK_MUTED, AMBER, AMBER_BAR = "#F6F5F1", "#1F2940", "#4A5160", "#8F5A0E", "#E0A946"
S = 3


def font(name, size):
    return ImageFont.truetype(F + name, size * S)


def mark(d, x, y, size):
    k = size / 32 * S
    X, Y = x * S, y * S
    d.rounded_rectangle([X, Y, X + 32 * k, Y + 32 * k], radius=7 * k, fill=NAVY)
    for (rx, ry, rw, col) in [(7, 7.5, 18, "#8A93A8"), (7, 14.5, 11, "#F6F5F1"), (7, 21.5, 18, "#8A93A8")]:
        d.rounded_rectangle([X + rx * k, Y + ry * k, X + (rx + rw) * k, Y + (ry + 3) * k], radius=1.5 * k, fill=col)
    d.ellipse([X + (23.5 - 2.4) * k, Y + (16 - 2.4) * k, X + (23.5 + 2.4) * k, Y + (16 + 2.4) * k], fill=AMBER_BAR)


def wrap(d, text, f, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width * S or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


def card(slug, kicker, title):
    W, H = 1200, 630
    im = Image.new("RGB", (W * S, H * S), PAPER)
    d = ImageDraw.Draw(im)
    mark(d, 72, 66, 52)
    d.text((140 * S, 92 * S), "ai·toolstack", font=font("Inter-Bold.otf", 30), fill="#1A1D24", anchor="lm")
    d.text((72 * S, 196 * S), kicker.upper(), font=font("Inter-SemiBold.otf", 24), fill=AMBER, anchor="ls")
    for size in (68, 62, 56, 50):
        f = font("InterDisplay-Bold.otf", size)
        lines = wrap(d, title, f, 1020)
        if len(lines) <= 3:
            break
    y = 222
    for ln in lines:
        y += int(size * 1.12)
        d.text((72 * S, y * S), ln, font=f, fill=NAVY, anchor="ls")
    d.text((72 * S, 566 * S), "Teja Sagiraju · ai-toolstack.com", font=font("Inter-Regular.otf", 24), fill=INK_MUTED, anchor="ls")
    d.rectangle([(W - 12) * S, 0, W * S, H * S], fill=AMBER_BAR)
    im = im.resize((W, H), Image.LANCZOS).quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    p = os.path.join(OUT, f"social-{slug}.png")
    im.save(p, optimize=True)
    return p


if __name__ == "__main__":
    print(card("chunk-size-rag-retrieval-contracts", "Experiment · Documents", "Half a contract clause reads like a whole one"))
    print(card("improve-rag-retrieval-contract-clauses", "Experiment · Documents", "Most of my missing answers were a vocabulary problem"))

"""Генерує іконку Платівки: платівка на кольоровому квадраті з заокругленням."""
import math, sys
from PIL import Image, ImageDraw, ImageFilter
S = 1024
def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
grad = Image.new("RGB", (S, S))
top, bottom = (24, 168, 160), (31, 64, 150)
gd = ImageDraw.Draw(grad)
for y in range(S):
    gd.line([(0, y), (S, y)], fill=lerp(top, bottom, y / S))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle((40, 40, S - 40, S - 40), radius=210, fill=255)
bg.paste(grad, (0, 0), mask)
# тінь платівки
sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(sh).ellipse((170, 200, S - 150, S - 120), fill=(0, 0, 0, 110))
sh = sh.filter(ImageFilter.GaussianBlur(28))
bg = Image.alpha_composite(bg, sh)
d = ImageDraw.Draw(bg)
c, R = S / 2, 345
d.ellipse((c - R, c - R, c + R, c + R), fill=(22, 24, 30, 255))
for r in range(R - 18, 150, -16):
    d.ellipse((c - r, c - r, c + r, c + r), outline=(48, 52, 62, 255), width=3)
# відблиски
for a0 in (205, 25):
    d.arc((c - R + 40, c - R + 40, c + R - 40, c + R - 40), a0, a0 + 38, fill=(150, 160, 178, 255), width=10)
# етикетка
L = 128
d.ellipse((c - L, c - L, c + L, c + L), fill=(255, 196, 64, 255))
d.ellipse((c - L + 22, c - L + 22, c + L - 22, c + L - 22), outline=(236, 150, 40, 255), width=6)
d.ellipse((c - 20, c - 20, c + 20, c + 20), fill=(22, 24, 30, 255))
bg.save("plativka.png")
bg.resize((256, 256), Image.LANCZOS).save("../../src/plativka/assets/icon.png")
bg.save("plativka.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
bg.save("plativka.icns")
print("ok")

"""Еквалайзер: 10 смуг, готові налаштування й корекція навушників з AutoEQ.

Як звучить: фільтри FFmpeg усередині mpv — ті самі «дзвони» (peaking) і полиці (shelf),
що й у більшості апаратних і програмних еквалайзерів. Обробка — з плаваючою комою,
тож зменшення частот нічого не псує. Щоб підсилення не «рвало» гучні місця (кліпінг),
загальна гучність автоматично зменшується рівно настільки, наскільки піднімається
найвища точка сумарної кривої — її рахуємо тут, за формулами тих самих фільтрів.

Корекція навушників: файл ParametricEQ.txt з проєкту AutoEQ (autoeq.app) —
виміряна різниця між вашими навушниками й нейтральним еталоном, переведена у фільтри.
"""
from __future__ import annotations

import cmath
import math
import re
from dataclasses import dataclass, field

BANDS = (31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)
BAND_Q = 1.41                      # смуги через октаву: сусіди ледь перекриваються
LIMIT = 12.0                       # ±12 дБ на смугу

PRESETS = {
    "flat":       (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    "bass":       (6, 5, 4, 2, 0, 0, 0, 0, 0, 0),
    "treble":     (0, 0, 0, 0, 0, 1, 2, 4, 5, 5),
    "vocal":      (-2, -2, -1, 0, 2, 3, 3, 2, 0, -1),
    "rock":       (4, 3, 2, 0, -1, -1, 1, 2, 3, 3),
    "pop":        (-1, 0, 2, 3, 3, 2, 0, -1, -1, -1),
    "electronic": (5, 4, 1, 0, -2, 1, 0, 1, 4, 5),
    "classical":  (0, 0, 0, 0, 0, 0, -2, -2, -2, -4),
    "quiet":      (5, 4, 2, 0, 0, 0, 0, 1, 3, 4),     # тихе прослуховування: вухо гірше чує краї
}


@dataclass
class Filter:
    kind: str          # PK — дзвін, LSC — нижня полиця, HSC — верхня полиця
    fc: float
    gain: float
    q: float


@dataclass
class Correction:
    name: str
    filters: list[Filter] = field(default_factory=list)
    preamp: float = 0.0

    def to_dict(self) -> dict:
        return {"name": self.name, "preamp": self.preamp,
                "filters": [[f.kind, f.fc, f.gain, f.q] for f in self.filters]}

    @classmethod
    def from_dict(cls, d) -> "Correction | None":
        try:
            return cls(str(d["name"]), [Filter(str(k), float(fc), float(g), float(q)) for k, fc, g, q in d["filters"]],
                       float(d.get("preamp", 0)))
        except (KeyError, TypeError, ValueError):
            return None


_LINE = re.compile(r"Filter\s*\d*\s*:\s*ON\s+(PK|PEQ|LSC|LS|HSC|HS)\s+Fc\s+([\d.]+)\s*Hz\s+Gain\s+(-?[\d.]+)\s*dB"
                   r"(?:\s+Q\s+([\d.]+))?", re.I)
_PRE = re.compile(r"Preamp\s*:\s*(-?[\d.]+)\s*dB", re.I)


def parse_parametric(text: str, name: str = "") -> Correction:
    """ParametricEQ.txt з AutoEQ (той самий формат пише Equalizer APO). ValueError — якщо фільтрів немає."""
    filters = []
    for m in _LINE.finditer(text):
        kind = {"PEQ": "PK", "LS": "LSC", "HS": "HSC"}.get(m.group(1).upper(), m.group(1).upper())
        q = float(m.group(4)) if m.group(4) else (0.71 if kind != "PK" else 1.0)
        fc, gain = float(m.group(2)), float(m.group(3))
        if 10 <= fc <= 22000 and abs(gain) <= 30 and 0.05 <= q <= 20:
            filters.append(Filter(kind, fc, gain, q))
    if not filters:
        raise ValueError("no filters")
    pre = _PRE.search(text)
    return Correction(name, filters, float(pre.group(1)) if pre else 0.0)


def correction_name(filename: str) -> str:
    """«Sennheiser HD 600 ParametricEQ.txt» → «Sennheiser HD 600»."""
    base = re.sub(r"\.txt$", "", filename, flags=re.I)
    return re.sub(r"\s*ParametricEQ$", "", base, flags=re.I).strip() or base


def band_filters(gains) -> list[Filter]:
    return [Filter("PK", f, float(g), BAND_Q) for f, g in zip(BANDS, gains) if abs(float(g)) >= 0.05]


# ── відгук фільтрів (формули RBJ Audio EQ Cookbook — ті самі, що в FFmpeg) ──
def _coefs(f: Filter, fs: float):
    a = 10 ** (f.gain / 40)
    w0 = 2 * math.pi * min(f.fc, fs * 0.49) / fs
    cw, sw = math.cos(w0), math.sin(w0)
    al = sw / (2 * f.q)
    if f.kind == "LSC":
        sa = 2 * math.sqrt(a) * al
        b = (a * ((a + 1) - (a - 1) * cw + sa), 2 * a * ((a - 1) - (a + 1) * cw), a * ((a + 1) - (a - 1) * cw - sa))
        aa = ((a + 1) + (a - 1) * cw + sa, -2 * ((a - 1) + (a + 1) * cw), (a + 1) + (a - 1) * cw - sa)
    elif f.kind == "HSC":
        sa = 2 * math.sqrt(a) * al
        b = (a * ((a + 1) + (a - 1) * cw + sa), -2 * a * ((a - 1) + (a + 1) * cw), a * ((a + 1) + (a - 1) * cw - sa))
        aa = ((a + 1) - (a - 1) * cw + sa, 2 * ((a - 1) - (a + 1) * cw), (a + 1) - (a - 1) * cw - sa)
    else:
        b = (1 + al * a, -2 * cw, 1 - al * a)
        aa = (1 + al / a, -2 * cw, 1 - al / a)
    return b, aa


def response_db(filters, freqs, fs: float = 48000.0) -> list[float]:
    """Сумарна крива (дБ) на заданих частотах."""
    out = [0.0] * len(freqs)
    for f in filters:
        b, a = _coefs(f, fs)
        for i, hz in enumerate(freqs):
            z = cmath.exp(-1j * 2 * math.pi * hz / fs)
            h = (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)
            out[i] += 20 * math.log10(max(abs(h), 1e-9))
    return out


FREQS = [20 * (1000 ** (i / 159)) for i in range(160)]      # 20 Гц … 20 кГц, рівномірно в логарифмі


def headroom(filters) -> float:
    """Наскільки зменшити гучність (дБ, ≤ 0), щоб найвища точка кривої не перевищила 0 дБ."""
    if not filters:
        return 0.0
    peak = max(response_db(filters, FREQS))
    return -round(max(0.0, peak) + (0.3 if peak > 0 else 0.0), 1)


def chain(gains, correction: Correction | None) -> tuple[str | None, float]:
    """Рядок фільтрів для mpv (lavfi) і автоматичний запас гучності. None — нічого не робити."""
    filters = (correction.filters if correction else []) + band_filters(gains)
    if not filters:
        return None, 0.0
    pre = headroom(filters)
    parts = [f"volume={pre}dB"] if pre < 0 else []
    for f in filters:
        name = {"LSC": "lowshelf", "HSC": "highshelf"}.get(f.kind, "equalizer")
        parts.append(f"{name}=f={f.fc:g}:t=q:w={f.q:g}:g={f.gain:g}")
    return ",".join(parts), pre

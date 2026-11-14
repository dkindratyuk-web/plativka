"""Еквалайзер: читання файлів AutoEQ, запас гучності, і що крива справді така, як ми рахуємо."""
import re
import shutil
import subprocess

import pytest

from plativka import eq

AUTOEQ = """Preamp: -6.4 dB
Filter 1: ON LSC Fc 105 Hz Gain 6.0 dB Q 0.70
Filter 2: ON PK Fc 160 Hz Gain -2.4 dB Q 0.58
Filter 3: OFF PK Fc 900 Hz Gain 9.0 dB Q 1.00
Filter 4: ON PK Fc 2700 Hz Gain 3.9 dB Q 2.10
Filter 5: ON HSC Fc 10000 Hz Gain 2.2 dB Q 0.70
"""


def test_parse_autoeq():
    c = eq.parse_parametric(AUTOEQ, eq.correction_name("Sennheiser HD 600 ParametricEQ.txt"))
    assert c.name == "Sennheiser HD 600" and c.preamp == -6.4
    assert [f.kind for f in c.filters] == ["LSC", "PK", "PK", "HSC"]      # вимкнений фільтр пропущено
    assert eq.Correction.from_dict(c.to_dict()) == c
    with pytest.raises(ValueError):
        eq.parse_parametric("not an eq file")


def test_headroom_prevents_clipping():
    assert eq.chain([0] * 10, None) == (None, 0.0)
    ch, pre = eq.chain(eq.PRESETS["bass"], None)
    assert pre <= -6 and ch.startswith(f"volume={pre}dB")
    _ch, pre = eq.chain(eq.PRESETS["classical"], None)      # лише зменшення — гучність не чіпаємо
    assert pre == 0.0


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="потрібен ffmpeg")
def test_curve_matches_ffmpeg():
    """Розрахована крива збігається з тим, що робить FFmpeg (ті самі фільтри, що в mpv)."""
    c = eq.parse_parametric(AUTOEQ)
    ch, pre = eq.chain(eq.PRESETS["vocal"], c)
    filters = c.filters + eq.band_filters(eq.PRESETS["vocal"])

    def level(hz, af):
        out = subprocess.run(["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", f"sine=frequency={hz}:sample_rate=48000:duration=2",
                              "-af", (af + "," if af else "") + "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        return float(re.search(r"mean_volume: (-?[\d.]+)", out).group(1))
    for hz in (60, 1000, 2700, 12000):
        measured = level(hz, ch) - level(hz, "")
        assert abs(measured - (eq.response_db(filters, [hz])[0] + pre)) < 0.3

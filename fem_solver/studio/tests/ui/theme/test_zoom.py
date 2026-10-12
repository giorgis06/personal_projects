import pytest
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom
from femstudio.ui.theme.stylesheet import build_stylesheet
from PySide6.QtCore import QSettings


def test_limits_are_seventy_to_two_hundred_percent_in_steps_of_ten():
    assert (zoom.MINIMUM, zoom.MAXIMUM, zoom.STEP) == (0.7, 2.0, 0.1)


def test_stepping_stays_on_tenths_and_inside_the_limits():
    factor = 1.0
    seen = []
    for _ in range(15):
        factor = zoom.zoomed_in(factor)
        seen.append(factor)
    assert seen[:3] == [1.1, 1.2, 1.3]
    assert seen[-1] == 2.0 and max(seen) == 2.0
    for _ in range(20):
        factor = zoom.zoomed_out(factor)
    assert factor == 0.7


def test_clamp_rounds_and_limits():
    assert zoom.clamp(0.1) == 0.7
    assert zoom.clamp(5.0) == 2.0
    assert zoom.clamp(1.04) == 1.0
    assert zoom.clamp(1.26) == 1.3


def test_pixels_and_points_scale_by_the_factor():
    assert zoom.px(22, 1.0) == 22
    assert zoom.px(22, 1.5) == 33
    assert zoom.px(22, 0.7) == 15
    assert zoom.pt(10, 1.5) == 15.0
    assert zoom.px(0, 1.5) == 0
    assert zoom.px(1, 0.7) == 1


def test_percent_wording():
    assert zoom.percent(1.0) == "100 %"
    assert zoom.percent(1.3) == "130 %"


def test_stylesheet_at_one_hundred_percent_is_made_of_the_token_values():
    sheet = build_stylesheet("Sans", "Mono", 1.0)
    assert f"min-height: {t.ROW_HEIGHT}px" in sheet
    assert f"font-size: {t.BASE_PT}pt" in sheet
    assert f"font-size: {t.TITLE_PT}pt" in sheet


def test_stylesheet_scales_rows_text_and_paddings_but_not_rules():
    sheet = build_stylesheet("Sans", "Mono", 1.5)
    assert f"min-height: {round(t.ROW_HEIGHT * 1.5)}px" in sheet
    assert f"font-size: {t.BASE_PT * 1.5:g}pt" in sheet
    assert f"font-size: {t.TITLE_PT * 1.5:g}pt" in sheet
    assert "padding: 12px 24px" in sheet  # the step tabs: 8 and 16 at 150 %
    assert f"border: {t.RULE_WIDTH}px solid {t.RULE}" in sheet
    assert "1.5px" not in sheet and "1px solid" in sheet


def test_the_choice_is_remembered(tmp_path):
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    assert zoom.load(settings) == 1.0
    zoom.save(settings, 1.3)
    settings.sync()
    again = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    assert zoom.load(again) == 1.3


@pytest.mark.parametrize("value", ["abc", "9.0", "0.1", None])
def test_a_bad_stored_value_falls_back_or_is_clamped(tmp_path, value):
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    if value is not None:
        settings.setValue(zoom.SETTINGS_KEY, value)
    assert zoom.MINIMUM <= zoom.load(settings) <= zoom.MAXIMUM

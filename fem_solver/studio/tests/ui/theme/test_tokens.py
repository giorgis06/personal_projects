import re

import pytest
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme.stylesheet import build_stylesheet

# The table under "Look" in ORCHESTRATOR.md, copied literally.
PLAN = {
    "PANEL": "#eceff2",
    "SURFACE": "#ffffff",
    "STAGE": "#f7f8fa",
    "CHROME": "#dfe4e9",
    "INK": "#1b242d",
    "MUTED": "#647180",
    "RULE": "#c9d1d9",
    "SELECTION": "#dbe8fb",
    "ACCENT": "#1d5fb8",
    "SUCCESS": "#1e7d4b",
    "WARNING": "#a15c00",
    "ERROR": "#b3261e",
}


@pytest.mark.parametrize(("name", "value"), PLAN.items())
def test_colour_tokens_match_the_plan(name, value):
    assert getattr(t, name) == value


def test_type_and_density_match_the_plan():
    assert (t.SANS_FAMILY, t.MONO_FAMILY) == ("IBM Plex Sans", "IBM Plex Mono")
    assert (t.BASE_PT, t.TITLE_PT) == (10, 9)
    assert t.ROW_HEIGHT == 22
    assert t.RADIUS <= 4
    assert t.RULE_WIDTH == 1


def test_data_palettes_are_valid_distinct_hex_colours():
    for palette in (t.REGION_COLOURS, t.BOUNDARY_COLOURS):
        assert all(re.fullmatch(r"#[0-9a-f]{6}", c) for c in palette)
        assert len(set(palette)) == len(palette)


def test_palette_index_wraps_around():
    assert t.region_colour(0) == t.region_colour(len(t.REGION_COLOURS))
    assert t.boundary_colour(1) == t.BOUNDARY_COLOURS[1]


def test_stylesheet_uses_every_interface_token_and_leaves_no_placeholder():
    sheet = build_stylesheet("Sans", "Mono")
    for name in PLAN:
        assert PLAN[name] in sheet, name
    assert "{t." not in sheet and "{{" not in sheet
    assert '"Sans"' in sheet and '"Mono"' in sheet
    assert f"min-height: {t.ROW_HEIGHT}px" in sheet


def test_stylesheet_has_no_corner_radius_above_the_plan_limit():
    sheet = build_stylesheet("Sans", "Mono")
    radii = [int(v) for v in re.findall(r"radius: (\d+)px", sheet)]
    assert radii and max(radii) <= 4

"""Every colour, font and size the interface uses. Nothing else in `ui/` spells one out."""

PANEL = "#eceff2"
SURFACE = "#ffffff"
STAGE = "#f7f8fa"
CHROME = "#dfe4e9"
INK = "#1b242d"
MUTED = "#647180"
RULE = "#c9d1d9"
SELECTION = "#dbe8fb"
ACCENT = "#1d5fb8"
SUCCESS = "#1e7d4b"
WARNING = "#a15c00"
ERROR = "#b3261e"
ON_ACCENT = "#ffffff"

# Data colours for named regions and boundaries, chosen to stay apart for common colour blindness.
REGION_COLOURS = ("#8fb8de", "#f2c28b", "#a6d6a0", "#d9a6cf", "#e6d98a", "#9fd5d1")
BOUNDARY_COLOURS = ("#1d5fb8", "#c4511b", "#2c8a3d", "#8e3b86", "#8a7a0d", "#12807a")
MESH_EDGE = "#4a5866"
SHAPE_OUTLINE = "#8a96a3"
UNNAMED_FILL = "#d5dbe1"

SANS_FAMILY = "IBM Plex Sans"
MONO_FAMILY = "IBM Plex Mono"

BASE_PT = 10
TITLE_PT = 9
SMALL_PT = 9

ROW_HEIGHT = 22
RADIUS = 4
RULE_WIDTH = 1
SWATCH = 10
PAD = 8
GAP = 4
SECTION_GAP = 12
PANEL_PAD = 10
TREE_INDENT = 14
DIALOG_WIDTH = 480
DIALOG_HEIGHT = 260

SCENE_DOCK_WIDTH = 236
PROPERTIES_DOCK_WIDTH = 300
LOG_DOCK_HEIGHT = 96
WINDOW_WIDTH = 1180
WINDOW_HEIGHT = 700

LINE_WIDTH = 2.0
LINE_WIDTH_SELECTED = 5.0
OUTLINE_WIDTH = 1.0
OPACITY = 0.85
OPACITY_DIMMED = 0.35


def region_colour(index: int) -> str:
    return REGION_COLOURS[index % len(REGION_COLOURS)]


def boundary_colour(index: int) -> str:
    return BOUNDARY_COLOURS[index % len(BOUNDARY_COLOURS)]

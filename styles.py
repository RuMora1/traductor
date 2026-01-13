from PyQt6.QtGui import QColor

# Color palette
PANEL_BG = QColor(0, 0, 0, 130)
BORDER_COLOR = "rgba(255,255,255,0.9)"

# Fonts (names only; the app may choose a fallback)
DEFAULT_FONT_FAMILY = "Segoe UI"

# Styles
BTN_MAIN = f"""
QPushButton {{
    background-color: rgba(0, 0, 0, 200);
    color: white;
    font-size: 14px;
    padding: 10px 18px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.45);
}}
QPushButton:hover {{ background-color: rgba(255,255,255,0.08); }}
"""

BTN_TITLE = f"""
QPushButton {{
    color: white;
    background-color: rgba(0,0,0,200);
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.5);
}}
QPushButton:hover {{ background-color: rgba(255,255,255,0.08); }}
"""

PANEL_STYLE = """QWidget { background: transparent; }"""

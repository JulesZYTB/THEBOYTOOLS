from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor
from gui.theme import COLORS

def shadow(blur=18, alpha=60, dy=4):
    """Create a shadow effect."""
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setColor(QColor(0, 0, 0, alpha))
    s.setOffset(0, dy)
    return s

def glass_frame(radius=14):
    """Dark card container with subtle border."""
    card = QFrame()
    card.setObjectName("GlassCard")
    card.setStyleSheet(f"""
        QFrame#GlassCard {{
            background-color: {COLORS['bg_card']};
            border: 1px solid {COLORS['border_light']};
            border-radius: {radius}px;
        }}
    """)
    
    card.setGraphicsEffect(shadow(18, 60, 4))
    
    layout = QVBoxLayout(card)
    layout.setContentsMargins(15, 15, 15, 15)
    
    return card, layout

def page_header(title: str, subtitle: str):
    """Page title + subtitle container."""
    container = QWidget()
    container.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    t = QLabel(title)
    t.setStyleSheet(f"""
        background: transparent; font-size: 22px; font-weight: 900;
        letter-spacing: 2px; color: {COLORS['text_primary']};
    """)
    layout.addWidget(t)
    
    s = QLabel(subtitle)
    s.setStyleSheet(f"""
        background: transparent; font-size: 12px; font-weight: 500;
        color: {COLORS['text_muted']}; margin-bottom: 4px;
    """)
    layout.addWidget(s)
    
    return container

def stat_chip(label: str, color: str):
    """Colored stat label + setter function."""
    lbl = QLabel(f"{label}: 0")
    lbl.setStyleSheet(f"""
        background: transparent; color: {color};
        font-size: 12px; font-weight: 800;
        letter-spacing: 0.5px;
    """)
    
    def setter(val):
        lbl.setText(f"{label}: {val}")
        
    return lbl, setter

def section_label(text: str):
    """Consistent section title (like PASSWORD MODE, TARGET INVITE, etc.)."""
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(f"""
        background: transparent; color: {COLORS['text_secondary']};
        font-size: 10px; font-weight: 800; letter-spacing: 2px;
    """)
    return lbl

def sub_card():
    """Rounded sub-card inside the main glass card."""
    card = QFrame()
    card.setStyleSheet(f"""
        QFrame {{
            background: {COLORS['bg_card_alt']};
            border-radius: 12px;
        }}
    """)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 12, 12, 12)
    return card, layout

def notice_banner(text: str, color: str = None, dim_color: str = None):
    """Warning/info banner — pill-shaped."""
    if color is None: color = COLORS['warning']
    if dim_color is None: dim_color = COLORS['warning_dim']
    
    lbl = QLabel(text)
    lbl.setStyleSheet(f"""
        background: {dim_color}; color: {color};
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 9px 16px;
        font-size: 12px; font-weight: 700;
    """)
    return lbl

INPUT_STYLE = f"""
    QLineEdit {{
        background: {COLORS['bg_input']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border_light']};
        border-radius: 12px;
        padding: 10px 16px;
        font-size: 13px;
        font-family: 'Segoe UI', sans-serif;
    }}
    QLineEdit:hover {{
        border-color: #555;
        background: {COLORS['bg_input']};
    }}
    QLineEdit:focus {{
        border-color: {COLORS['primary']};
        background: {COLORS['bg_darkest']};
    }}
    QLineEdit:disabled {{
        background: {COLORS['bg_dark']};
        color: {COLORS['text_disabled']};
        border-color: {COLORS['border_light']};
    }}
"""

RADIO_STYLE = f"""
    QRadioButton {{
        color: {COLORS['text_primary']};
        font-size: 13px; font-weight: 600;
        spacing: 10px; background: transparent;
    }}
    QRadioButton::indicator {{
        width: 18px; height: 18px; border-radius: 9px;
        border: 2px solid {COLORS['border_light']};
    }}
    QRadioButton::indicator:checked {{
        border: 2px solid {COLORS['primary']};
        background: {COLORS['primary']};
    }}
    QRadioButton:checked {{
        color: {COLORS['primary']};
    }}
"""

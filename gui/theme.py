from typing import Dict

COLORS = {
    'bg_void': '#080808',
    'bg_darkest': '#0a0a0a',
    'bg_dark': '#0e0e0e',
    'bg_main': '#111111',
    'bg_card': '#181818',
    'bg_card_alt': '#1c1c1c',
    'bg_card_hover': '#222222',
    'bg_sidebar': '#0c0c0c',
    'bg_input': '#141414',
    'bg_hover': '#1e1e1e',
    'bg_pressed': '#252525',
    'bg_overlay': 'rgba(8,8,8,0.88)',
    'primary': '#ffffff',
    'primary_hover': '#e0e0e0',
    'primary_dim': 'rgba(255,255,255,0.08)',
    'primary_glow': 'rgba(255,255,255,0.15)',
    'primary_border': 'rgba(255,255,255,0.20)',
    'secondary': '#999999',
    'secondary_dim': 'rgba(153,153,153,0.06)',
    'tertiary': '#666666',
    'tertiary_dim': 'rgba(102,102,102,0.12)',
    'tertiary_border': 'rgba(102,102,102,0.25)',
    'accent_blue': '#888888',
    'accent_blue_dim': 'rgba(136,136,136,0.10)',
    'success': '#4ade80',
    'success_dim': 'rgba(74,222,128,0.10)',
    'warning': '#fbbf24',
    'warning_dim': 'rgba(251,191,36,0.10)',
    'error': '#f87171',
    'error_dim': 'rgba(248,113,113,0.10)',
    'info': '#a0a0a0',
    'text_primary': '#f0f0f0',
    'text_secondary': '#888888',
    'text_muted': '#555555',
    'text_disabled': '#333333',
    'border': '#1e1e1e',
    'border_subtle': '#252525',
    'border_light': '#3a3a3a',
    'border_focus': '#ffffff',
    'border_focus_alt': '#888888',
    'scrollbar': '#2a2a2a',
    'scrollbar_hover': '#444444'
}

def get_stylesheet() -> str:
    c = COLORS
    return f"""
    /* ═══ GLOBAL RESET ═══ */
    * {{ outline: none; }}
    QWidget {{
        background-color: {c['bg_main']};
        color: {c['text_primary']};
        font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif;
        font-size: 13px;
        selection-background-color: {c['primary']};
        selection-color: #000000;
    }}

    /* ═══ SCROLLBARS ═══ */
    QScrollBar:vertical {{
        background: transparent; width: 5px; margin: 2px 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c['scrollbar']}; min-height: 24px; border-radius: 2px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {c['scrollbar_hover']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    
    QScrollBar:horizontal {{
        background: transparent; height: 5px; margin: 0 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['scrollbar']}; min-width: 24px; border-radius: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {c['scrollbar_hover']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    /* ═══ BUTTONS — pill shape, high contrast ═══ */
    QPushButton {{
        background-color: #3a3a3a;
        color: {c['primary']};
        border: none;
        border-radius: 22px;
        padding: 10px 24px;
        font-weight: 700;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: #505050;
        color: #ffffff;
    }}
    QPushButton:pressed {{
        background-color: #606060;
    }}
    QPushButton:disabled {{
        background-color: #1e1e1e;
        color: {c['text_disabled']};
    }}

    /* ═══ INPUTS ═══ */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border_light']};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 13px;
        font-family: 'Segoe UI', 'Inter', sans-serif;
    }}
    QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
        border: 1px solid #555555;
        background-color: {c['bg_card']};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {c['border_focus']};
        background-color: {c['bg_darkest']};
    }}

    /* ═══ LABELS ═══ */
    QLabel {{
        background: transparent;
        color: {c['text_primary']};
    }}

    /* ═══ COMBOBOX ═══ */
    QComboBox {{
        background-color: {c['bg_card_alt']};
        border-radius: 8px;
        padding: 7px 12px;
        min-width: 80px;
        font-weight: 600;
        font-size: 12px;
    }}
    QComboBox:hover {{
        border-color: #555;
        background-color: {c['bg_hover']};
    }}
    QComboBox:focus {{ border-color: {c['border_focus']}; }}
    QComboBox::drop-down {{
        border: none; width: 24px; padding-right: 6px;
    }}
    QComboBox::down-arrow {{
        image: none;
        width: 0; height: 0;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {c['text_secondary']};
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_card_alt']};
        border-radius: 8px;
        selection-background-color: {c['primary_dim']};
        selection-color: {c['primary']};
        outline: none; padding: 4px;
    }}

    /* ═══ SPINBOX — visible arrows ═══ */
    QSpinBox {{
        background-color: {c['bg_card_alt']};
        border-radius: 8px;
        padding: 6px 10px;
        font-weight: 700;
        font-size: 13px;
    }}
    QSpinBox:focus {{
        border-color: {c['border_focus']};
    }}
    QSpinBox:hover {{
        border-color: #555;
        background-color: {c['bg_hover']};
    }}
    QSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 24px; height: 15px;
        background: {c['bg_card_alt']};
        border: none;
        border-left: 1px solid {c['border']};
        border-top-right-radius: 8px;
    }}
    QSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 24px; height: 15px;
        background: {c['bg_card_alt']};
        border-bottom-right-radius: 8px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background: {c['bg_pressed']};
    }}
    QSpinBox::up-arrow {{
        image: none;
        width: 0; height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-bottom: 6px solid {c['text_secondary']};
    }}
    QSpinBox::down-arrow {{
        image: none;
        width: 0; height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {c['text_secondary']};
    }}

    /* ═══ PROGRESS BAR ═══ */
    QProgressBar {{
        background-color: {c['bg_input']};
        border: none; border-radius: 4px;
        height: 8px; text-align: center; color: transparent;
    }}
    QProgressBar::chunk {{
        border-radius: 4px;
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #fff,stop:1 #888);
    }}

    /* ═══ TABS ═══ */
    QTabWidget::pane {{ border: 1px solid {c['border_subtle']}; border-radius: 12px; background: {c['bg_card']}; }}
    QTabBar::tab {{
        background: transparent; color: {c['text_muted']}; border: none;
        padding: 10px 22px; font-weight: 600; font-size: 13px;
        margin-right: 2px; border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:selected {{ color: {c['primary']}; border-bottom: 2px solid {c['primary']}; }}
    QTabBar::tab:hover:!selected {{ color: {c['text_secondary']}; }}

    /* ═══ TOOLTIP ═══ */
    QToolTip {{
        background-color: {c['bg_darkest']}; color: {c['text_primary']}; border-radius: 6px;
        padding: 7px 12px; font-size: 12px;
    }}

    /* ═══ RADIO BUTTON ═══ */
    QRadioButton {{
        color: {c['text_primary']}; font-size: 13px; font-weight: 600;
        spacing: 10px; background: transparent;
    }}
    QRadioButton::indicator {{
        width: 16px; height: 16px; border-radius: 8px;
        border: 2px solid {c['border_light']}; background: {c['bg_input']};
    }}
    QRadioButton::indicator:checked {{
        border: 2px solid {c['primary']};
    }}
    QRadioButton:checked {{ color: {c['primary']}; }}

    /* ═══ CARD FRAME ═══ */
    QFrame#GlassCard {{
        background-color: {c['bg_card']};
        border-radius: 14px;
    }}

    /* ═══ MESSAGE BOX ═══ */
    QMessageBox {{
        background-color: {c['bg_darkest']};
        font-size: 13px;
    }}
    QMessageBox QLabel {{ color: {c['text_primary']}; background: transparent; }}
    QMessageBox QPushButton {{
        min-width: 80px; padding: 8px 20px;
        background-color: {c['bg_card_alt']}; border-radius: 8px;
    }}
    QMessageBox QPushButton:hover {{
        border-color: {c['border_focus']};
    }}
    """

SIDEBAR_BUTTON_STYLE = f"""
    QPushButton {{
        background: transparent;
        color: {COLORS['text_secondary']};
        border: none;
        border-radius: 8px;
        padding: 10px 10px 10px 14px;
        text-align: left;
        font-size: 14px;
        font-weight: 800;
        letter-spacing: 0.5px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['bg_hover']};
    }}
    QPushButton:checked {{
        background-color: {COLORS['bg_pressed']};
        font-weight: 900;
        color: {COLORS['primary']};
    }}
"""

HEADER_STYLE = f"""
    background-color: {COLORS['bg_void']};
    border-bottom: 1px solid {COLORS['border_subtle']};
"""

FOOTER_STYLE = f"""
    QLabel {{
        color: {COLORS['text_muted']};
        font-size: 11px;
        background: transparent;
        letter-spacing: 0.5px;
    }}
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QFrame, QToolButton, QPushButton, QApplication, QScrollArea, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from core.config import Config
from core.sound_manager import SoundManager
from gui.theme import COLORS
from gui.pages.page_helpers import glass_frame, page_header, shadow, sub_card, section_label, INPUT_STYLE
from gui.widgets.toggle_switch import ToggleSwitch

class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = Config.instance()
        self._api_inputs = {} # email service keys
        self._captcha_inputs = {}
        self._sms_inputs = {}
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(36, 32, 36, 32)
        self.main_layout.setSpacing(24)

        # Header
        self.main_layout.addWidget(page_header(
            "SETTINGS",
            "Manage API keys, preferences, and application configuration"
        ))

        # Top Row: General & Actions
        top_row = QHBoxLayout()
        top_row.setSpacing(20)
        
        # General Card
        general_card, g_lay = glass_frame(18)
        g_lay.setContentsMargins(24, 20, 24, 20)
        g_lay.addWidget(self._section_header("GENERAL"))
        
        sound_row = self._setting_row_frame()
        sl = QHBoxLayout(sound_row)
        sl.setContentsMargins(20, 14, 20, 14)
        
        sound_lbl_v = QVBoxLayout()
        sound_lbl = QLabel("Sound Effects")
        sound_lbl.setStyleSheet(f"background:transparent; color:{COLORS['text_primary']}; font-size:13px; font-weight:700;")
        sound_desc = QLabel("Play sounds on actions and completions")
        sound_desc.setStyleSheet(f"background:transparent; color:{COLORS['text_muted']}; font-size:11px; font-weight:500;")
        sound_lbl_v.addWidget(sound_lbl); sound_lbl_v.addWidget(sound_desc)
        
        self._sound_toggle = ToggleSwitch()
        sl.addLayout(sound_lbl_v)
        sl.addStretch()
        sl.addWidget(self._sound_toggle)
        g_lay.addWidget(sound_row)
        g_lay.addStretch()
        
        # Actions Card
        actions_card, a_lay = glass_frame(18)
        a_lay.setContentsMargins(24, 20, 24, 20)
        a_lay.addWidget(self._section_header("ACTIONS"))
        
        save_btn = QPushButton("SAVE ALL SETTINGS")
        save_btn.setFixedHeight(48)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']}; color: #000;
                border: none; border-radius: 14px;
                font-size: 13px; font-weight: 800; letter-spacing: 1.5px;
                padding: 12px 24px;
            }}
            QPushButton:hover {{
                background: {COLORS['primary_hover']};
            }}
        """)
        save_btn.clicked.connect(self._save)
        
        exit_btn = QPushButton("EXIT APPLICATION")
        exit_btn.setFixedHeight(48)
        exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: #ff6b6b;
                border: 2px solid rgba(255,107,107,0.3); border-radius: 14px;
                font-size: 13px; font-weight: 800; letter-spacing: 1.5px;
                padding: 12px 24px;
            }}
            QPushButton:hover {{
                background: rgba(255,107,107,0.1);
                border-color: #ff6b6b;
            }}
        """)
        exit_btn.clicked.connect(self._exit_app)
        
        a_lay.addWidget(save_btn)
        a_lay.addSpacing(10)
        a_lay.addWidget(exit_btn)
        a_lay.addStretch()
        
        top_row.addWidget(general_card, stretch=1)
        top_row.addWidget(actions_card, stretch=1)
        self.main_layout.addLayout(top_row)

        # Email Keys
        email_card, e_lay = glass_frame(18)
        e_lay.setContentsMargins(24, 22, 24, 22)
        e_header = self._section_header("EMAIL SERVICE API KEYS")
        e_hint = QLabel("Used by Unlocker, Changer, and other email-based tools")
        e_hint.setStyleSheet(f"background:transparent; color:{COLORS['text_muted']}; font-size:10px; font-weight:500; font-style:italic;")
        e_lay.addWidget(e_header)
        e_lay.addWidget(e_hint)
        e_lay.addSpacing(12)
        
        email_grid = QGridLayout()
        email_grid.setSpacing(16)
        email_services = ["007hotmail", "zeus", "lution"]
        for i, svc in enumerate(email_services):
            card, inp = self._api_key_card(svc.upper(), f"Enter {svc} API key...")
            self._api_inputs[svc] = inp
            email_grid.addWidget(card, 0, i)
        e_lay.addLayout(email_grid)
        self.main_layout.addWidget(email_card)

        # Captcha & SMS Keys Row
        api_row = QHBoxLayout()
        api_row.setSpacing(20)
        
        # Captcha Keys
        captcha_card, c_lay = glass_frame(18)
        c_lay.setContentsMargins(24, 22, 24, 22)
        c_header = self._section_header("CAPTCHA SOLVER API KEYS")
        c_lay.addWidget(c_header)
        c_lay.addSpacing(12)
        
        captcha_services = [
            ('onyx', 'ONYXSOLVER'), ('hcaptchasolver', 'HCAPTCHASOLVER'), 
            ('voidsolver', 'VOIDSOLVER'), ('anysolver', 'ANYNSOLVER'), 
            ('nopecha', 'NOPECHA'), ('yescaptcha', 'YESCAPTCHA')
        ]
        for key, display in captcha_services:
            row, inp = self._api_key_row(display, "API Key")
            self._captcha_inputs[key] = inp
            c_lay.addLayout(row)
        c_lay.addStretch()
        
        # SMS Keys
        sms_card, s_lay = glass_frame(18)
        s_lay.setContentsMargins(24, 22, 24, 22)
        s_header = self._section_header("SMS SERVICE API KEYS")
        s_hint = QLabel("Used by Phone Verifier")
        s_hint.setStyleSheet(e_hint.styleSheet())
        s_lay.addWidget(s_header)
        s_lay.addWidget(s_hint)
        s_lay.addSpacing(12)
        
        sms_services = [
            ('5sim', '5SIM'), ('smsbower', 'SMSBOWER'), 
            ('herosms', 'HEROSMS'), ('tigersms', 'TIGERSMS')
        ]
        for key, display in sms_services:
            row, inp = self._api_key_row(display, "API Key")
            self._sms_inputs[key] = inp
            s_lay.addLayout(row)
        s_lay.addStretch()
        
        api_row.addWidget(captcha_card, stretch=1)
        api_row.addWidget(sms_card, stretch=1)
        self.main_layout.addLayout(api_row)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _section_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background:transparent; color:{COLORS['text_secondary']}; font-size:11px; font-weight:800; letter-spacing:2.5px;")
        return lbl

    def _setting_row_frame(self):
        f = QFrame()
        f.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_card_alt']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 12px;
            }}
        """)
        return f

    def _api_key_card(self, label, placeholder):
        """Vertical card with label + input + toggle. Used for email keys (grid layout)."""
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {COLORS['bg_input']}; border-radius: 14px; }}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)
        
        svc_lbl = QLabel(label)
        svc_lbl.setStyleSheet(f"background:transparent; color:{COLORS['text_muted']}; font-size:12px; font-weight:800; letter-spacing:1.5px;")
        
        inp_row = QHBoxLayout()
        inp_row.setSpacing(8)
        
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setEchoMode(QLineEdit.EchoMode.Password)
        inp.setFixedHeight(40)
        inp.setStyleSheet(self._input_style())
        
        toggle_btn = QToolButton()
        toggle_btn.setText("◉")
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setStyleSheet(self._eye_style())
        toggle_btn.clicked.connect(lambda: self._toggle_vis(inp, toggle_btn))
        
        inp_row.addWidget(inp)
        inp_row.addWidget(toggle_btn)
        
        lay.addWidget(svc_lbl)
        lay.addLayout(inp_row)
        return card, inp

    def _api_key_row(self, label, placeholder):
        """Horizontal row: LABEL | [input] | [eye]. Used for captcha/SMS keys."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(12)
        
        svc_lbl = QLabel(label)
        svc_lbl.setFixedWidth(140)
        svc_lbl.setStyleSheet(f"background:transparent; color:{COLORS['text_muted']}; font-size:12px; font-weight:700; letter-spacing:1px;")
        
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setEchoMode(QLineEdit.EchoMode.Password)
        inp.setFixedHeight(38)
        inp.setStyleSheet(self._input_style())
        
        toggle_btn = QToolButton()
        toggle_btn.setText("◉")
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setStyleSheet(self._eye_style())
        toggle_btn.clicked.connect(lambda: self._toggle_vis(inp, toggle_btn))
        
        row.addWidget(svc_lbl)
        row.addWidget(inp)
        row.addWidget(toggle_btn)
        return row, inp

    def _input_style(self):
        return f"""
            QLineEdit {{
                background: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 12px; font-weight: 600;
                font-family: 'Consolas', 'Courier New', monospace;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['border_focus']};
            }}
            QLineEdit:hover {{
                border-color: #555;
            }}
        """

    def _eye_style(self):
        return f"""
            QToolButton {{
                background: transparent; border: none;
                color: {COLORS['text_muted']}; font-size: 16px; padding: 4px;
            }}
            QToolButton:hover {{ color: {COLORS['text_primary']}; }}
        """

    def _toggle_vis(self, inp, btn):
        if inp.echoMode() == QLineEdit.EchoMode.Password:
            inp.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("◎")
        else:
            inp.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("◉")

    def _load(self):
        """Load all settings from config into the UI."""
        self._sound_toggle.setChecked(self._config.get('sound_enabled', True))
        
        # Email keys
        for svc, inp in self._api_inputs.items():
            inp.setText(self._config.get(f'email_api_keys.{svc}', ''))
            
        # Captcha keys
        for svc, inp in self._captcha_inputs.items():
            inp.setText(self._config.get(f'phone_verifier.captcha_api_keys.{svc}', ''))
            
        # SMS keys
        for svc, inp in self._sms_inputs.items():
            inp.setText(self._config.get(f'phone_verifier.sms_api_keys.{svc}', ''))

    def reload(self):
        """Public method — reload settings when navigating to this page."""
        self._load()

    def _save(self):
        """Save all settings to config."""
        self._config.set('sound_enabled', self._sound_toggle.isChecked())
        
        # Email keys
        for svc, inp in self._api_inputs.items():
            self._config.set(f'email_api_keys.{svc}', inp.text().strip())
            
        # Captcha keys
        for svc, inp in self._captcha_inputs.items():
            self._config.set(f'phone_verifier.captcha_api_keys.{svc}', inp.text().strip())
            
        # SMS keys
        for svc, inp in self._sms_inputs.items():
            self._config.set(f'phone_verifier.sms_api_keys.{svc}', inp.text().strip())
            
        self._config.save()
        SoundManager.instance().success()

    def _exit_app(self):
        """Save and exit."""
        self._save()
        QApplication.quit()

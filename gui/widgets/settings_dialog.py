from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QFrame, QToolButton, QPushButton, 
    QApplication, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.config import Config
from gui.theme import COLORS
from gui.widgets.toggle_switch import ToggleSwitch

class SettingsDialog(QDialog):
    """
    SettingsDialog — Global settings modal (Sound + Email + Captcha + SMS API keys).
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = Config.instance()
        
        self.setWindowTitle("Settings")
        self.setFixedWidth(540)
        self.setMinimumHeight(500)
        self.setMaximumHeight(860)
        
        self.setStyleSheet(f"""
            QDialog {{
                background: {COLORS['bg_dark']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 14px;
            }}
        """)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        self._api_inputs = {}
        self._captcha_inputs = {}
        self._sms_inputs = {}
        
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        
        # Header
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet(f"background: {COLORS['bg_dark']}; border: none;")
        hdr_row = QHBoxLayout(hdr_frame)
        hdr_row.setContentsMargins(28, 20, 28, 12)
        
        title = QLabel("SETTINGS")
        title.setStyleSheet(f"""
            background: transparent; font-size: 18px; font-weight: 800;
            letter-spacing: 3px; color: {COLORS['primary']};
        """)
        hdr_row.addWidget(title)
        hdr_row.addStretch()
        
        close_btn = QPushButton("X")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setObjectName("SettingsCloseBtn")
        close_btn.setStyleSheet("""
            QPushButton#SettingsCloseBtn {
                background: transparent !important; 
                border: none !important;
                color: #ffffff !important; 
                font-size: 20px !important; 
                font-weight: 900 !important;
                padding: 0 !important;
            }
            QPushButton#SettingsCloseBtn:hover {
                color: #ff4757 !important;
            }
        """)
        close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(close_btn)
        
        outer.addWidget(hdr_frame)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {COLORS['bg_dark']};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {COLORS['bg_card']};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border_light']};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        
        content = QWidget()
        content.setStyleSheet(f"background: {COLORS['bg_dark']};")
        root = QVBoxLayout(content)
        root.setContentsMargins(28, 8, 28, 24)
        root.setSpacing(16)
        
        # Sound Section
        sound_frame = self._section_card(root)
        sl = QVBoxLayout(sound_frame)
        sl.setContentsMargins(20, 14, 20, 14)
        sl.setSpacing(14)
        
        sound_lbl = self._section_title("SOUND EFFECTS")
        sl.addWidget(sound_lbl)
        
        self._sound_toggle = ToggleSwitch()
        sl.addWidget(self._sound_toggle)
        
        root.addWidget(sound_frame)
        
        # Email Section
        root.addWidget(self._separator())
        email_lbl = self._section_title("EMAIL SERVICE API KEYS")
        root.addWidget(email_lbl)
        
        for svc in ['007hotmail', 'zeus', 'lution']:
            self._add_api_key_row(root, svc.upper(), f"Enter {svc} API key...", self._api_inputs, svc)
            
        # Captcha Section
        root.addWidget(self._separator())
        captcha_lbl = self._section_title("CAPTCHA SOLVER API KEYS")
        root.addWidget(captcha_lbl)
        
        captcha_services = [
            ('onyx', 'ONYXSOLVER'), ('hcaptchasolver', 'HCAPTCHASOLVER'), 
            ('voidsolver', 'VOIDSOLVER'), ('anysolver', 'ANYSOLVER'), 
            ('nopecha', 'NOPECHA'), ('yescaptcha', 'YESCAPTCHA')
        ]
        for key, display in captcha_services:
            self._add_api_key_row(root, display, f"Enter {display} key...", self._captcha_inputs, key)
            
        # SMS Section
        root.addWidget(self._separator())
        sms_lbl = self._section_title("SMS SERVICE API KEYS")
        root.addWidget(sms_lbl)
        
        sms_services = [
            ('5sim', '5SIM'), ('smsbower', 'SMSBOWER'), 
            ('herosms', 'HEROSMS'), ('tigersms', 'TIGERSMS')
        ]
        for key, display in sms_services:
            self._add_api_key_row(root, display, f"Enter {display} key...", self._sms_inputs, key)
            
        root.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        
        # Footer
        footer = QFrame()
        footer.setStyleSheet(f"background: {COLORS['bg_dark']}; border-top: 1px solid {COLORS['border_light']};")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(28, 12, 28, 20)
        f_lay.setSpacing(10)
        
        save_btn = QPushButton("SAVE SETTINGS")
        save_btn.setFixedHeight(44)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']}; color: #000;
                border: none; border-radius: 22px;
                font-size: 13px; font-weight: 800; letter-spacing: 1px;
                padding: 10px 24px;
            }}
            QPushButton:hover {{
                background: {COLORS['primary_hover']};
            }}
        """)
        save_btn.clicked.connect(self._save_and_close)
        f_lay.addWidget(save_btn, stretch=1)
        
        exit_btn = QPushButton("EXIT APPLICATION")
        exit_btn.setFixedHeight(44)
        exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_btn.setStyleSheet("""
            QPushButton {
                background: #3d1f1f; color: #ff6b6b;
                border: 2px solid #ff6b6b; border-radius: 22px;
                font-size: 13px; font-weight: 800; letter-spacing: 1px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background: #ff6b6b; color: #000;
            }
        """)
        exit_btn.clicked.connect(self._exit_app)
        f_lay.addWidget(exit_btn)
        
        outer.addWidget(footer)

    def _section_card(self, parent_layout):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_card']};
                border-radius: 12px;
            }}
        """)
        return card

    def _section_title(self, text: str):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            background: transparent; color: {COLORS['text_secondary']};
            font-size: 10px; font-weight: 700; letter-spacing: 2px;
        """)
        return lbl

    def _separator(self):
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {COLORS['border']}; max-height: 1px; border: none;")
        return sep

    def _add_api_key_row(self, parent_layout, label: str, placeholder: str, inputs_dict: dict, key: str):
        row_frame = QFrame()
        row_frame.setFixedHeight(130) # Wait, is it really 130? NBC says 130, let's re-verify logic.
        # Actually, looking at constraints, it's likely smaller for each row. 
        # NBC sometimes has fixed heights for layouts. Let's just use normal layout.
        
        rl = QVBoxLayout(row_frame)
        rl.setContentsMargins(20, 12, 20, 12)
        rl.setSpacing(10)
        
        svc_lbl = QLabel(label)
        svc_lbl.setStyleSheet(f"""
            background: transparent; color: {COLORS['text_primary']};
            font-size: 12px; font-weight: 700; letter-spacing: 1px;
        """)
        rl.addWidget(svc_lbl)
        
        inp_row = QHBoxLayout()
        inp_row.setSpacing(10)
        
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setEchoMode(QLineEdit.EchoMode.Password)
        inp.setFixedHeight(36)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 12px; font-weight: 600;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['border_focus']};
            }}
            QLineEdit:hover {{
                border-color: #555;
            }}
        """)
        inputs_dict[key] = inp
        inp_row.addWidget(inp)
        
        toggle_btn = QToolButton()
        toggle_btn.setText("◉")
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent; border: none;
                color: {COLORS['text_muted']}; font-size: 16px; padding: 4px;
            }}
            QToolButton:hover {{ color: {COLORS['text_primary']}; }}
        """)
        toggle_btn.clicked.connect(lambda: self._toggle_vis(inp, toggle_btn))
        inp_row.addWidget(toggle_btn)
        
        rl.addLayout(inp_row)
        parent_layout.addWidget(row_frame)

    def _toggle_vis(self, inp, btn):
        if inp.echoMode() == QLineEdit.EchoMode.Password:
            inp.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setStyleSheet(f"QToolButton{{background:transparent;border:none;color:{COLORS['primary']};font-size:16px;padding:4px;}}QToolButton:hover{{color:{COLORS['primary']};}}")
        else:
            inp.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setStyleSheet(f"QToolButton{{background:transparent;border:none;color:{COLORS['text_muted']};font-size:16px;padding:4px;}}QToolButton:hover{{color:{COLORS['text_primary']};}}")

    def _load(self):
        self._sound_toggle.setChecked(self._config.get("sound_enabled", False))
        
        # Load Email Keys
        email_keys = self._config.get("email_api_keys", {})
        for k, inp in self._api_inputs.items():
            inp.setText(email_keys.get(k, ""))
            
        # Load Captcha Keys
        captcha_keys = self._config.get("phone_verifier.captcha_api_keys", {})
        for k, inp in self._captcha_inputs.items():
            inp.setText(captcha_keys.get(k, ""))
            
        # Load SMS Keys
        sms_keys = self._config.get("phone_verifier.sms_api_keys", {})
        for k, inp in self._sms_inputs.items():
            inp.setText(sms_keys.get(k, ""))

    def _save_and_close(self):
        self._config.set("sound_enabled", self._sound_toggle.isChecked())
        
        # Save Email Keys
        email_keys = {k: inp.text().strip() for k, inp in self._api_inputs.items()}
        self._config.set("email_api_keys", email_keys)
        
        # Save Captcha Keys
        captcha_keys = {k: inp.text().strip() for k, inp in self._captcha_inputs.items()}
        self._config.set("phone_verifier.captcha_api_keys", captcha_keys)
        
        # Save SMS Keys
        sms_keys = {k: inp.text().strip() for k, inp in self._sms_inputs.items()}
        self._config.set("phone_verifier.sms_api_keys", sms_keys)
        
        self._config.save()
        self.accept()

    def _exit_app(self):
        """Save settings and exit the entire application."""
        self._save_and_close()
        QApplication.quit()

    def get_api_key(self, service: str) -> str:
        if service in self._api_inputs:
            return self._api_inputs[service].text().strip()
        if service in self._captcha_inputs:
            return self._captcha_inputs[service].text().strip()
        if service in self._sms_inputs:
            return self._sms_inputs[service].text().strip()
        return ""

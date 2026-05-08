from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QLineEdit
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import pyqtSignal, Qt
from core.config import Config
from gui.theme import COLORS
from gui.widgets.toggle_switch import ToggleSwitch

class SettingsPanel(QWidget):
    """
    SettingsPanel — Inline tool settings bar.
    Uses custom +/- buttons instead of QSpinBox for reliable arrow rendering.
    Spread layout fills available width for a polished look.
    """
    
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = Config.instance()
        self._thread_count = 5
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        
        row_widget = QFrame()
        row_widget.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_card']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 12px;
            }}
        """)
        
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(24, 12, 24, 12)
        row.setSpacing(16)
        
        # Threads
        thread_lbl = QLabel("THREADS")
        thread_lbl.setStyleSheet(f"""
            background: transparent; color: {COLORS['text_secondary']};
            font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
        """)
        row.addWidget(thread_lbl)
        
        self._minus_btn = QPushButton("▼")
        self._minus_btn.setFixedSize(32, 32)
        self._minus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._minus_btn.setStyleSheet(self._arrow_btn_style())
        self._minus_btn.clicked.connect(self._dec_threads)
        row.addWidget(self._minus_btn)
        
        self._thread_lbl = QLineEdit("5")
        self._thread_lbl.setFixedWidth(48)
        self._thread_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thread_lbl.setValidator(QIntValidator(1, 100))
        self._thread_lbl.setStyleSheet(f"""
            background: {COLORS['bg_card_alt']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border_light']};
            border-radius: 8px;
            padding: 5px 0;
            font-weight: 800; font-size: 14px;
        """)
        self._thread_lbl.editingFinished.connect(self._on_thread_edit)
        row.addWidget(self._thread_lbl)
        
        self._plus_btn = QPushButton("▲")
        self._plus_btn.setFixedSize(32, 32)
        self._plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._plus_btn.setStyleSheet(self._arrow_btn_style())
        self._plus_btn.clicked.connect(self._inc_threads)
        row.addWidget(self._plus_btn)
        
        row.addWidget(self._divider())
        
        # Proxies
        proxy_lbl = QLabel("PROXIES")
        proxy_lbl.setStyleSheet(thread_lbl.styleSheet())
        row.addWidget(proxy_lbl)
        
        self._proxy_check = ToggleSwitch()
        self._proxy_check.stateChanged.connect(self._on_change)
        row.addWidget(self._proxy_check)
        
        row.addWidget(self._divider())
        
        # Save Output
        save_lbl = QLabel("SAVE OUTPUT")
        save_lbl.setStyleSheet(thread_lbl.styleSheet())
        row.addWidget(save_lbl)
        
        self._save_check = ToggleSwitch(checked=True)
        self._save_check.stateChanged.connect(self._on_change)
        row.addWidget(self._save_check)
        
        row.addStretch()
        
        # Warning
        warning_lbl = QLabel("⚠ THEBOY is not responsible for any banned / lost tokens. Running proxyless? Keep threads low.")
        warning_lbl.setWordWrap(True)
        warning_lbl.setStyleSheet(f"""
            color: {COLORS['warning']};
            font-size: 11px;
            font-style: italic;
            font-weight: 600;
            padding-top: 4px;
            padding-left: 8px;
        """)
        
        outer.addWidget(row_widget)
        outer.addWidget(warning_lbl)

    def _arrow_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLORS['bg_card_alt']};
                color: {COLORS['text_secondary']};
                border-radius: 8px;
                font-size: 10px; font-weight: 700;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
                border-color: {COLORS['primary']};
            }}
            QPushButton:pressed {{
                background: {COLORS['bg_pressed']};
            }}
        """

    def _divider(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"background: {COLORS['border']}; max-width: 1px; margin: 2px 8px; border: none;")
        return sep

    def _inc_threads(self):
        self._thread_count = min(100, self._thread_count + 1)
        self._thread_lbl.setText(str(self._thread_count))
        self._on_change()

    def _dec_threads(self):
        self._thread_count = max(1, self._thread_count - 1)
        self._thread_lbl.setText(str(self._thread_count))
        self._on_change()

    def _on_thread_edit(self):
        """Called when user finishes typing a thread count."""
        text = self._thread_lbl.text().strip()
        if text.isdigit():
            val = int(text)
            self._thread_count = max(1, min(100, val))
            self._thread_lbl.setText(str(self._thread_count))
            self._on_change()

    def _load_settings(self):
        # Default thread count from config if available
        self._thread_count = self._config.get("default_threads", 5)
        self._thread_lbl.setText(str(self._thread_count))
        
        # Proxy usage
        self._proxy_check.setChecked(self._config.get("use_proxies", False))
        
        # Output saving
        self._save_check.setChecked(self._config.get("save_output", True))

    def _on_change(self):
        self._config.set("default_threads", self._thread_count)
        self._config.set("use_proxies", self._proxy_check.isChecked())
        self._config.set("save_output", self._save_check.isChecked())
        self.settings_changed.emit()

    @property
    def thread_count(self) -> int:
        return self._thread_count

    @property
    def use_proxies(self) -> bool:
        return self._proxy_check.isChecked()

    @property
    def save_output(self) -> bool:
        return self._save_check.isChecked()

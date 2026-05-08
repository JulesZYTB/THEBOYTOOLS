import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, 
    QLabel, QPushButton, QFileDialog, QComboBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QColor
from core.proxy_manager import parse_proxies, ProxyEntry, ProxyType
from core.config import Config
from gui.theme import COLORS

class ProxyInput(QWidget):
    """ProxyInput — Proxy paste area with visible chrome buttons and combo."""
    
    proxies_changed = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._proxies = []
        self._cfg = Config.instance()
        self._setup_ui()
        
        # Load saved data
        saved_type = self._cfg.get("proxy_input_type", "HTTP")
        self._type_combo.setCurrentText(saved_type)
        
        saved_proxies = self._cfg.get("proxy_input_data", "")
        self._text_edit.setPlainText(saved_proxies)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Header Row
        header = QHBoxLayout()
        header.setSpacing(8)
        
        label = QLabel("PROXIES")
        label.setStyleSheet(f"""
            background: transparent; font-weight: 700; font-size: 11px;
            letter-spacing: 1.5px; color: {COLORS['text_secondary']};
        """)
        header.addWidget(label)
        
        # Count Badge
        self._count_badge = QLabel("0")
        self._count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_badge.setFixedHeight(22)
        self._count_badge.setMinimumWidth(30)
        self._count_badge.setStyleSheet(self._badge_style(False))
        header.addWidget(self._count_badge)
        
        header.addStretch()
        
        # Type Combo
        self._type_combo = QComboBox()
        self._type_combo.addItems(['HTTP', 'HTTPS', 'SOCKS4', 'SOCKS5'])
        self._type_combo.setFixedWidth(95)
        self._type_combo.setFixedHeight(26)
        self._type_combo.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS['bg_card_alt']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11px; font-weight: 700;
            }}
            QComboBox:hover {{
                border-color: #555; background: {COLORS['bg_hover']};
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox::down-arrow {{
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 4px solid {COLORS['text_secondary']};
            }}
            QComboBox QAbstractItemView {{
                background: {COLORS['bg_card_alt']};
                selection-background-color: {COLORS['primary_dim']};
                selection-color: {COLORS['primary']};
                outline: none; padding: 4px;
            }}
        """)
        self._type_combo.currentTextChanged.connect(self._on_text_changed)
        header.addWidget(self._type_combo)
        
        # Buttons
        btn_style = """
            QPushButton {
                background: #3a3a3a;
                color: #ddd;
                border: none;
                border-radius: 12px;
                font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background: #555;
                color: #fff;
            }
        """
        
        load_btn = QPushButton("LOAD FILE")
        load_btn.setFixedHeight(26)
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.setStyleSheet(btn_style)
        load_btn.clicked.connect(self._load_file)
        header.addWidget(load_btn)
        
        clear_btn = QPushButton("CLEAR")
        clear_btn.setFixedHeight(26)
        clear_btn.setFixedWidth(56)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(btn_style)
        clear_btn.clicked.connect(self._clear)
        header.addWidget(clear_btn)
        
        layout.addLayout(header)
        
        # Text Edit
        self._text_edit = QPlainTextEdit()
        self._text_edit.setPlaceholderText(
            "Paste proxies here  --  or drag & drop a file\n\n"
            "Formats:  ip:port  |  user:pass@ip:port  |  ip:port:user:pass"
        )
        self._text_edit.setMinimumHeight(90)
        self._text_edit.setMaximumHeight(150)
        self._text_edit.setAcceptDrops(True)
        self._text_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 10px;
                padding: 10px 12px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px;
            }}
            QPlainTextEdit:hover {{
                border: 1px solid #555;
                background-color: {COLORS['bg_card']};
            }}
            QPlainTextEdit:focus {{
                border: 1px solid {COLORS['border_focus_alt']};
                background-color: {COLORS['bg_darkest']};
            }}
        """)
        self._text_edit.textChanged.connect(self._on_text_changed)
        
        # Overload drag/drop
        self._text_edit.dragEnterEvent = self._drag_enter
        self._text_edit.dropEvent = self._drop
        
        layout.addWidget(self._text_edit)

    def _badge_style(self, active: bool) -> str:
        if active:
            return f"""
                background: {COLORS['primary']}; color: #000;
                border-radius: 11px; padding: 2px 8px;
                font-size: 11px; font-weight: 800;
            """
        return f"""
            background: {COLORS['bg_card_alt']}; color: {COLORS['text_muted']};
            border: 1px solid {COLORS['border_subtle']};
            border-radius: 11px; padding: 2px 8px;
            font-size: 11px; font-weight: 700;
        """

    def _get_proxy_type(self) -> ProxyType:
        txt = self._type_combo.currentText()
        if txt == 'HTTPS': return ProxyType.HTTPS
        if txt == 'SOCKS4': return ProxyType.SOCKS4
        if txt == 'SOCKS5': return ProxyType.SOCKS5
        return ProxyType.HTTP

    def _on_text_changed(self):
        text = self._text_edit.toPlainText()
        ptype = self._get_proxy_type()
        
        self._proxies = parse_proxies(text, ptype)
        
        count = len(self._proxies)
        self._count_badge.setText(str(count))
        self._count_badge.setStyleSheet(self._badge_style(count > 0))
        
        # Save to config
        self._cfg.set("proxy_input_data", text)
        self._cfg.set("proxy_input_type", self._type_combo.currentText())
        
        self.proxies_changed.emit(self._proxies)

    def _load_file(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Load Proxies", "", "Text Files (*.txt);;All Files (*)"
        )
        if fp:
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    self._text_edit.setPlainText(f.read())
            except:
                pass

    def _clear(self):
        self._text_edit.clear()

    def _drag_enter(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            fp = urls[0].toLocalFile()
            if os.path.isfile(fp) and fp.endswith('.txt'):
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        self._text_edit.setPlainText(f.read())
                except:
                    pass

    @property
    def proxies(self) -> list:
        return self._proxies

    def set_text(self, text: str):
        self._text_edit.setPlainText(text)

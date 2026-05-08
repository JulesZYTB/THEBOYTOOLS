from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor, QColor
from gui.theme import COLORS

class ConsoleWidget(QWidget):
    """ConsoleWidget — Seamless terminal. No gap between header and body."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._max_lines = 1000
        self._setup_ui()
        self.append_log("System initialized.", "SUCCESS")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Container with shadow
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_void']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 10px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 3)
        container.setGraphicsEffect(shadow)
        
        clayout = QVBoxLayout(container)
        clayout.setContentsMargins(0, 0, 0, 0)
        clayout.setSpacing(0)
        
        # Header
        header = QWidget()
        header.setFixedHeight(30)
        header.setStyleSheet(f"""
            background: {COLORS['bg_darkest']};
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            border-bottom: 1px solid {COLORS['border']};
        """)
        
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.setSpacing(5)
        
        # Traffic light buttons (purely aesthetic)
        for c in ['#f87171', '#fbbf24', '#4ade80']:
            d = QLabel()
            d.setFixedSize(8, 8)
            d.setStyleSheet(f"background: {c}; border-radius: 4px; border: none;")
            hl.addWidget(d)
        
        hl.addSpacing(6)
        
        title = QLabel("TERMINAL")
        title.setStyleSheet(f"""
            background: transparent; font-weight: 700; font-size: 10px;
            letter-spacing: 2px; color: {COLORS['text_muted']};
        """)
        hl.addWidget(title)
        
        hl.addStretch()
        
        clear_btn = QPushButton("CLEAR")
        clear_btn.setFixedSize(48, 18)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: #222; color: {COLORS['text_muted']}; border-radius: 4px;
                font-size: 9px; font-weight: 700; letter-spacing: 1px; padding: 0;
            }}
            QPushButton:hover {{
                color: {COLORS['primary']}; border-color: {COLORS['primary']};
                background: {COLORS['primary_dim']};
            }}
        """)
        clear_btn.clicked.connect(self.clear)
        hl.addWidget(clear_btn)
        
        clayout.addWidget(header)
        
        # Console Body
        self._console = QTextEdit()
        self._console.setReadOnly(True)
        self._console.setMinimumHeight(100)
        self._console.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_void']};
                color: {COLORS['text_primary']};
                border: none;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                padding: 8px 12px;
                font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        clayout.addWidget(self._console)
        
        layout.addWidget(container)

    @pyqtSlot(str, str)
    def append_log(self, message: str, level: str = 'INFO'):
        level_color_map = {
            'INFO': '#6ea8fe', 
            'SUCCESS': '#4ade80', 
            'WARNING': '#fbbf24', 
            'ERROR': '#f87171', 
            'DEBUG': '#888888'
        }
        msg_color_map = {
            'INFO': COLORS['text_primary'], 
            'SUCCESS': COLORS['success'], 
            'WARNING': COLORS['warning'], 
            'ERROR': COLORS['error'], 
            'DEBUG': COLORS['text_muted']
        }
        
        level_color = level_color_map.get(level, '#6ea8fe')
        msg_color = msg_color_map.get(level, COLORS['text_primary'])
        
        display_msg = message
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # If message already contains a timestamp (from AppLogger), parse it
        if ' > ' in message:
            parts = message.split(' > ', 2)
            if len(parts) >= 3:
                timestamp = parts[0]
                display_msg = parts[2]
            elif len(parts) == 2:
                timestamp = parts[0]
                display_msg = parts[1]

        sep_color = COLORS['text_muted']
        ts_html = f'<span style="color:{COLORS["text_muted"]};">{timestamp}</span> '
        arrow = f'<span style="color:{sep_color};">&#8594;</span> '
        badge = f'<span style="color:{level_color}; font-weight:700;">{level}</span> '
        bullet = f'<span style="color:{sep_color};">&#8226;</span> '
        msg_html = f'<span style="color:{msg_color};">{display_msg}</span>'
        
        html = f'<div style="margin:1px 0;">{ts_html}{arrow}{badge}{bullet}{msg_html}</div>'
        
        scrollbar = self._console.verticalScrollBar()
        was_at_bottom = scrollbar.value() == scrollbar.maximum()
        
        self._console.append(html)
        
        if was_at_bottom:
            cursor = self._console.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self._console.setTextCursor(cursor)
            
        # Line limit
        doc = self._console.document()
        if doc.blockCount() > self._max_lines:
            c = QTextCursor(doc.begin())
            c.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, doc.blockCount() - self._max_lines)
            c.removeSelectedText()

    def clear(self):
        self._console.clear()

    def log_plain(self, msg: str):
        self.append_log(msg, "INFO")

    def log_info(self, msg: str):
        self.append_log(msg, "INFO")

    def log_success(self, msg: str):
        self.append_log(msg, "SUCCESS")

    def log_warning(self, msg: str):
        self.append_log(msg, "WARNING")

    def log_error(self, msg: str):
        self.append_log(msg, "ERROR")

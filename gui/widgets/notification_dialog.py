from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QFont, QColor
from gui.theme import COLORS

class NotificationDialog(QDialog):
    """
    NotificationDialog — Premium 2026 announcement popup.
    Glass-morphism design with bold typography and gradient accents.
    """
    def __init__(self, parent, announcement_text: str):
        super().__init__(parent)
        self._text = announcement_text
        
        self.setWindowTitle("Announcement")
        self.setFixedWidth(520)
        self.setMinimumHeight(260)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._setup_ui()
        self._animate_in()

    def _animate_in(self):
        """Subtle slide-in animation."""
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        curr_pos = self.pos()
        start = QPoint(curr_pos.x(), curr_pos.y() + 30)
        end = curr_pos
        
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        
        container = QFrame()
        container.setObjectName("AnnContainer")
        container.setStyleSheet("""
            QFrame#AnnContainer {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(18, 18, 22, 0.97),
                    stop:0.5 rgba(22, 22, 28, 0.97),
                    stop:1 rgba(16, 16, 20, 0.97)
                );
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 180))
        container.setGraphicsEffect(shadow)
        
        root = QVBoxLayout(container)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(0)
        
        # Header Row
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(12)
        
        dot = QLabel("●")
        dot.setStyleSheet("""
            background: transparent;
            color: #4ade80;
            font-size: 10px;
        """)
        hdr_row.addWidget(dot, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        title = QLabel("ANNOUNCEMENT")
        title_font = QFont("Segoe UI", 13)
        title_font.setWeight(QFont.Weight.Black)
        title.setFont(title_font)
        title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.0)
        title.setStyleSheet("""
            background: transparent;
            color: #ffffff;
        """)
        hdr_row.addWidget(title)
        
        hdr_row.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("AnnCloseBtn")
        close_btn.setFixedSize(34, 34)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton#AnnCloseBtn {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 17px;
                color: rgba(255, 255, 255, 0.5);
                font-size: 14px;
                font-weight: 600;
                padding: 0;
            }
            QPushButton#AnnCloseBtn:hover {
                background: rgba(248, 113, 113, 0.15);
                border-color: rgba(248, 113, 113, 0.3);
                color: #f87171;
            }
        """)
        close_btn.clicked.connect(self.accept)
        hdr_row.addWidget(close_btn)
        
        root.addLayout(hdr_row)
        root.addSpacing(20)
        
        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(255,255,255,0.0),
                stop:0.2 rgba(255,255,255,0.12),
                stop:0.8 rgba(255,255,255,0.12),
                stop:1 rgba(255,255,255,0.0)
            );
        """)
        root.addWidget(divider)
        root.addSpacing(22)
        
        # Content
        content_frame = QFrame()
        content_frame.setObjectName("AnnContent")
        content_frame.setStyleSheet("""
            QFrame#AnnContent {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 14px;
            }
        """)
        content_lay = QVBoxLayout(content_frame)
        content_lay.setContentsMargins(24, 20, 24, 20)
        
        display_text = self._text if self._text else "No announcements at this time."
        msg_label = QLabel(display_text)
        msg_label.setWordWrap(True)
        msg_font = QFont("Segoe UI", 14)
        msg_font.setWeight(QFont.Weight.DemiBold)
        msg_label.setFont(msg_font)
        msg_label.setStyleSheet(f"""
            background: transparent;
            color: {COLORS['text_primary']};
            line-height: 1.7;
            padding: 4px 0;
        """)
        content_lay.addWidget(msg_label)
        
        root.addWidget(content_frame)
        root.addSpacing(24)
        
        # Button Row
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        dismiss_btn = QPushButton("GOT IT")
        dismiss_btn.setObjectName("AnnDismissBtn")
        dismiss_btn.setFixedHeight(44)
        dismiss_btn.setMinimumWidth(160)
        dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dismiss_btn.setStyleSheet("""
            QPushButton#AnnDismissBtn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ffffff,
                    stop:1 #d4d4d4
                );
                color: #0a0a0a;
                border: none;
                border-radius: 22px;
                font-size: 13px;
                font-weight: 800;
                letter-spacing: 2px;
                padding: 10px 28px;
            }
            QPushButton#AnnDismissBtn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e8e8e8,
                    stop:1 #c0c0c0
                );
            }
            QPushButton#AnnDismissBtn:pressed {
                background: #b0b0b0;
            }
        """)
        dismiss_btn.clicked.connect(self.accept)
        btn_row.addWidget(dismiss_btn)
        btn_row.addStretch()
        
        root.addLayout(btn_row)
        
        outer.addWidget(container)

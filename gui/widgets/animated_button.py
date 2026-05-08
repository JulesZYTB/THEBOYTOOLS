from PyQt6.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, Qt
from PyQt6.QtGui import QColor, QFont
from gui.theme import COLORS

class AnimatedButton(QPushButton):
    """
    AnimatedButton — Pill-shaped, high-contrast, bold.
    Matches reference: rounded, clearly visible, premium feel.
    """
    
    def __init__(self, text: str, primary: bool = False, danger: bool = False, success: bool = False, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self.danger = danger
        self.success = success
        
        self._setup_style()
        self._setup_animations()
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        font = QFont("Segoe UI", 12)
        font.setWeight(QFont.Weight.Bold)
        self.setFont(font)

    def _setup_style(self):
        if self.primary:
            style = """
                QPushButton {
                    background: #ffffff;
                    color: #000000;
                    border: none;
                    border-radius: 22px;
                    padding: 11px 32px;
                    font-weight: 800;
                    font-size: 13px;
                    font-family: 'Segoe UI', sans-serif;
                }
                QPushButton:hover { background: #e0e0e0; }
                QPushButton:pressed { background: #cccccc; }
                QPushButton:disabled {
                    background: #2a2a2a;
                    color: #555555;
                }
            """
        elif self.danger:
            style = """
                QPushButton {
                    background: #3d1f1f;
                    color: #ff6b6b;
                    border: 2px solid #ff6b6b;
                    border-radius: 22px;
                    padding: 11px 32px;
                    font-weight: 800;
                    font-size: 13px;
                    font-family: 'Segoe UI', sans-serif;
                }
                QPushButton:hover {
                    background: #ff6b6b;
                    color: #000000;
                }
                QPushButton:pressed { background: #dd5555; color: #000; }
                QPushButton:disabled {
                    background: #1e1e1e;
                    color: #444444;
                    border: 1px solid #333333;
                }
            """
        elif self.success:
            style = """
                QPushButton {
                    background: #1f3d1f;
                    color: #6bff6b;
                    border: 2px solid #6bff6b;
                    border-radius: 22px;
                    padding: 11px 32px;
                    font-weight: 800;
                    font-size: 13px;
                    font-family: 'Segoe UI', sans-serif;
                }
                QPushButton:hover {
                    background: #6bff6b;
                    color: #000000;
                }
                QPushButton:pressed { background: #55dd55; color: #000; }
                QPushButton:disabled {
                    background: #1e1e1e;
                    color: #444444;
                    border: 1px solid #333333;
                }
            """
        else:
            style = f"""
                QPushButton {{
                    background: #3a3a3a;
                    color: #f0f0f0;
                    border: none;
                    border-radius: 22px;
                    padding: 11px 32px;
                    font-weight: 700;
                    font-size: 13px;
                    font-family: 'Segoe UI', sans-serif;
                }}
                QPushButton:hover {{
                    background: #505050;
                    color: #ffffff;
                }}
                QPushButton:pressed {{
                    background: #606060;
                }}
                QPushButton:disabled {{
                    background: #1e1e1e;
                    color: #444444;
                }}
            """
        self.setStyleSheet(style)

    def set_theme(self, theme: str):
        """Dynamically update button theme."""
        self.primary = (theme == "primary")
        self.danger = (theme == "danger")
        self.success = (theme == "success")
        self._setup_style()

    def _setup_animations(self):
        # Shadow effect for glow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 2)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(self.shadow)
        
        # Glow animation
        self._glow = QPropertyAnimation(self.shadow, b"blurRadius")
        self._glow.setDuration(250)
        self._glow.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, e):
        self._glow.stop()
        self._glow.setStartValue(self.shadow.blurRadius())
        self._glow.setEndValue(16)
        self._glow.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._glow.stop()
        self._glow.setStartValue(self.shadow.blurRadius())
        self._glow.setEndValue(0)
        self._glow.start()
        super().leaveEvent(e)

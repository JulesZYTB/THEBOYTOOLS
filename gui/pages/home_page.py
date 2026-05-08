import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, 
    QGraphicsDropShadowEffect, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from gui.theme import COLORS

class HomePage(QWidget):
    """
    Home Page — Compact feature cards, clickable to navigate, no emojis, copyright footer.
    """
    
    navigate_to = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.outer.setSpacing(0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(48, 36, 48, 24)
        self.layout.setSpacing(24)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 1. Hero Card
        self.hero = QFrame()
        self.hero.setObjectName("HeroCard")
        self.hero.setStyleSheet(f"""
            QFrame#HeroCard {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS['bg_card_alt']},
                    stop:0.5 {COLORS['bg_card']},
                    stop:1 {COLORS['bg_darkest']}
                );
                border: 1px solid {COLORS['border_light']};
                border-radius: 14px;
            }}
        """)
        
        _shadow = QGraphicsDropShadowEffect()
        _shadow.setBlurRadius(24)
        _shadow.setColor(QColor(0, 0, 0, 80))
        _shadow.setOffset(0, 4)
        self.hero.setGraphicsEffect(_shadow)
        
        self.hero_inner = QVBoxLayout(self.hero)
        self.hero_inner.setContentsMargins(40, 36, 40, 36)
        self.hero_inner.setSpacing(6)
        self.hero_inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.brand_row = QHBoxLayout()
        self.brand_row.setSpacing(12)
        
        self.t1 = QLabel("THEBOY")
        self.t1.setStyleSheet(f"""
            background: transparent; font-size: 42px; font-weight: 900;
            letter-spacing: 8px; color: {COLORS['primary']};
        """)
        self.t2 = QLabel("TOOLS")
        self.t2.setStyleSheet(f"""
            background: transparent; font-size: 42px; font-weight: 900;
            letter-spacing: 8px; color: {COLORS['text_muted']};
        """)
        self.brand_row.addWidget(self.t1)
        self.brand_row.addWidget(self.t2)
        self.hero_inner.addLayout(self.brand_row)
        
        self.tagline = QLabel("ADVANCED DISCORD MULTI-TOOLKIT")
        self.tagline.setStyleSheet(f"""
            background: transparent; font-size: 11px; font-weight: 700;
            letter-spacing: 3px; color: {COLORS['text_muted']};
        """)
        self.hero_inner.addWidget(self.tagline, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.badge_row = QHBoxLayout()
        self.badge_row.setContentsMargins(0, 8, 0, 0)
        self.discord_badge = QLabel("DISCORD TOOLS")
        self.discord_badge.setStyleSheet(f"""
            background: transparent; color: {COLORS['primary']};
            border: 1px solid {COLORS['primary']};
            border-radius: 10px; padding: 3px 14px;
            font-size: 10px; font-weight: 700; letter-spacing: 1px;
        """)
        self.badge_row.addWidget(self.discord_badge)
        self.hero_inner.addLayout(self.badge_row)
        
        self.layout.addWidget(self.hero)
        self.layout.addSpacing(8)
        
        # 2. Tool Grid
        # We'll use index-based navigation mapping to MainWindow's stacked widget
        # 0=Home, 1=Checker, 2=Joiner, 3=Changer, 4=Humanizer, 5=Unlocker, 
        # 6=CaptchaChecker, 7=Separator, 8=TrialChecker, 9=TokenCleaner, 
        # 10=GetTokenEmail, 11=PhoneVerifier, 12=Settings
        
        tool_cards = [
            ("Token Checker", 1),
            ("Server Joiner", 2),
            ("Account Changer", 3),
            ("Account Humanizer", 4),
            ("Account Unlocker", 5),
            ("Captcha Checker", 6),
            ("Token Separator", 7),
            ("Trial Checker", 8),
            ("Token Cleaner", 9),
            ("Get Token Email", 10),
            ("Phone Verifier", 11),
            ("Application Settings", 12)
        ]
        
        for title, idx in tool_cards:
            card = self._make_card(title, idx)
            self.layout.addWidget(card)
            
        self.layout.addStretch(1)
        
        # 3. Footer
        self.footer = QLabel("made by THEBOY    |    Telegram: @TH2BOY    |    Discord: hetheboy2")
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: 10px; font-weight: 600; letter-spacing: 0.5px;
        """)
        self.layout.addWidget(self.footer)
        
        self.scroll.setWidget(self.container)
        self.outer.addWidget(self.scroll)

    def _make_card(self, title: str, page_index: int):
        """Compact clickable tool card — title only."""
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setFixedHeight(44)
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_input']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 10px;
            }}
            QFrame:hover {{
                background: {COLORS['bg_card_hover']};
                border-color: {COLORS['primary']};
            }}
        """)
        
        inner = QHBoxLayout(card)
        inner.setContentsMargins(20, 0, 20, 0)
        
        t = QLabel(title)
        t.setStyleSheet(f"""
            background: transparent; color: {COLORS['text_primary']};
            font-size: 14px; font-weight: 700; letter-spacing: 0.5px;
        """)
        
        arrow = QLabel("→")
        arrow.setStyleSheet(f"""
            background: transparent; color: {COLORS['text_muted']};
            font-size: 14px; font-weight: 600;
        """)
        
        inner.addWidget(t)
        inner.addStretch(1)
        inner.addWidget(arrow)
        
        card.mousePressEvent = lambda e: self.navigate_to.emit(page_index)
        return card

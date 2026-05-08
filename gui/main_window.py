import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QStackedWidget, QFrame, 
    QButtonGroup, QApplication
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QTimer
from PyQt6.QtGui import QIcon

from gui.theme import COLORS, SIDEBAR_BUTTON_STYLE, get_stylesheet
from gui.pages.home_page import HomePage
from gui.pages.checker_page import CheckerPage
from gui.pages.joiner_page import JoinerPage
from gui.pages.changer_page import ChangerPage
from gui.pages.humanizer_page import HumanizerPage
from gui.pages.unlocker_page import UnlockerPage
from gui.pages.captcha_checker_page import CaptchaCheckerPage
from gui.pages.separator_page import SeparatorPage
from gui.pages.trial_checker_page import TrialCheckerPage
from gui.pages.token_cleaner_page import TokenCleanerPage
from gui.pages.get_token_email_page import GetTokenEmailPage
from gui.pages.phone_verifier_page import PhoneVerifierPage
from gui.pages.settings_page import SettingsPage
from core.config import Config
from core.sound_manager import SoundManager
from core.discord_rpc import DiscordRPCManager
from core.server_manager import ServerManager, APP_VERSION
from gui.widgets.notification_dialog import NotificationDialog

def _get_project_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _get_asset_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(__file__))
    return _get_project_root()

class MainWindow(QMainWindow):
    """
    Main Window — The core shell of THEBOY TOOLS.
    Features a collapsible sidebar, animated page indicator, and premium glass header.
    """
    
    _PAGE_RPC_MAP = {
        0: 'home', 1: 'checker', 2: 'joiner', 3: 'changer', 
        4: 'humanizer', 5: 'unlocker', 6: 'captcha_checker', 
        7: 'token_cleaner', 8: 'trial_checker', 9: 'separator', 
        10: 'get_token_email', 11: 'phone_verifier', 12: 'settings'
    }

    def __init__(self):
        super().__init__()
        self._config = Config.instance()
        self._project_root = _get_project_root()
        self._asset_root = _get_asset_root()
        
        self._current_announcement = None
        self._current_announcement_id = None
        self._read_announcement_ids = self._config.get('_read_announcement_ids', [])
        
        self._setup_window()
        self._setup_ui()
        
        # Connect server signals
        self._server = ServerManager.instance()
        self._server.signals.presence_updated.connect(self._update_presence)
        self._server.signals.announcement_updated.connect(self._on_announcement_updated)

    def _setup_window(self):
        self.setWindowTitle(f"THEBOY TOOLS v{APP_VERSION}")
        self.setMinimumSize(1200, 800)
        self.resize(
            self._config.get('window.width', 1320),
            self._config.get('window.height', 860)
        )
        
        icon_path = os.path.join(self._asset_root, 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.setStyleSheet(get_stylesheet())

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("AppRoot")
        central.setStyleSheet(f"QWidget#AppRoot {{ background-color: {COLORS['bg_dark']}; }}")
        self.setCentralWidget(central)
        
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        # Header
        self._build_header(root)
        
        # Body
        body = QHBoxLayout()
        body.setSpacing(0)
        
        # Sidebar
        self._build_sidebar(body)
        
        # Content
        content_outer = QWidget()
        content_outer.setStyleSheet(f"background-color: {COLORS['bg_main']};")
        content_vbox = QVBoxLayout(content_outer)
        content_vbox.setContentsMargins(0, 0, 0, 0)
        
        self._pages = QStackedWidget()
        self._pages.setStyleSheet("background: transparent;")
        
        # Initialize Pages
        self._home_page = HomePage()
        self._checker_page = CheckerPage()
        self._joiner_page = JoinerPage()
        self._changer_page = ChangerPage()
        self._humanizer_page = HumanizerPage()
        self._unlocker_page = UnlockerPage()
        self._captcha_checker_page = CaptchaCheckerPage()
        self._separator_page = SeparatorPage()
        self._trial_checker_page = TrialCheckerPage()
        self._token_cleaner_page = TokenCleanerPage()
        self._get_token_email_page = GetTokenEmailPage()
        self._phone_verifier_page = PhoneVerifierPage()
        self._settings_page = SettingsPage()
        
        self._pages.addWidget(self._home_page)            # 0
        self._pages.addWidget(self._checker_page)         # 1
        self._pages.addWidget(self._joiner_page)          # 2
        self._pages.addWidget(self._changer_page)         # 3
        self._pages.addWidget(self._humanizer_page)       # 4
        self._pages.addWidget(self._unlocker_page)        # 5
        self._pages.addWidget(self._captcha_checker_page) # 6
        self._pages.addWidget(self._token_cleaner_page)   # 7
        self._pages.addWidget(self._trial_checker_page)   # 8
        self._pages.addWidget(self._separator_page)       # 9
        self._pages.addWidget(self._get_token_email_page) # 10
        self._pages.addWidget(self._phone_verifier_page)  # 11
        self._pages.addWidget(self._settings_page)        # 12
        
        content_vbox.addWidget(self._pages)
        body.addWidget(content_outer, stretch=1)
        
        root.addLayout(body)
        
        # Connections
        self._home_page.navigate_to.connect(self._navigate_from_home)
        
        # Initial RPC
        DiscordRPCManager.instance().update_activity('idle')
        
        # Initial Nav sync
        QTimer.singleShot(50, lambda: self._animate_indicator(self._nav_buttons[0]))

    def _build_header(self, parent_layout):
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_void']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(12, 0, 24, 0)
        lay.setSpacing(8)
        
        # Toggle Sidebar
        self._toggle_btn = QPushButton("≡")
        self._toggle_btn.setFixedSize(36, 36)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_card']};
                border: 1px solid {COLORS['border_light']};
                color: {COLORS['text_secondary']};
                font-size: 20px;
                font-weight: 600;
                border-radius: 8px;
                padding: 0; padding-bottom: 2px;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
                border-color: {COLORS['primary']};
            }}
        """)
        self._toggle_btn.clicked.connect(self._toggle_sidebar)
        lay.addWidget(self._toggle_btn)
        
        lay.addSpacing(8)
        
        # Brand
        brand = QLabel("THEBOY")
        brand.setStyleSheet(f"background: transparent; font-size: 16px; font-weight: 900; letter-spacing: 5px; color: {COLORS['text_primary']};")
        lay.addWidget(brand)
        
        brand2 = QLabel("TOOLS")
        brand2.setStyleSheet(f"background: transparent; color: {COLORS['text_muted']}; font-size: 16px; font-weight: 900; letter-spacing: 5px;")
        lay.addWidget(brand2)
        
        ver_label = QLabel(f"v{APP_VERSION}")
        ver_label.setStyleSheet(f"background: transparent; color: {COLORS['text_disabled']}; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        lay.addWidget(ver_label)
        
        lay.addSpacing(16)
        
        cr = QLabel("made by THEBOY  |  Telegram: @TH2BOY  |  Discord: hetheboy2")
        cr.setStyleSheet(f"background: transparent; color: {COLORS['text_disabled']}; font-size: 10px; font-weight: 600; letter-spacing: 0.3px;")
        lay.addWidget(cr)
        
        lay.addStretch()
        
        # Online Badge
        self._live_label = QLabel("Online : 1")
        self._live_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['success']};
                font-size: 11px;
                font-weight: bold;
                background: {COLORS['bg_card']};
                padding: 4px 12px;
                border-radius: 10px;
                border: 1px solid {COLORS['border_light']};
            }}
        """)
        lay.addWidget(self._live_label)
        
        lay.addSpacing(8)
        
        # Bell
        self._bell_btn = QPushButton("🔔")
        self._bell_btn.setObjectName("BellBtn")
        self._bell_btn.setFixedSize(36, 36)
        self._bell_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bell_btn.setStyleSheet(f"""
            QPushButton#BellBtn {{
                background: {COLORS['bg_card']};
                font-size: 16px;
                border-radius: 18px;
                padding: 0; padding-bottom: 1px;
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border_light']};
            }}
            QPushButton#BellBtn:hover {{
                background: {COLORS['bg_hover']};
                border-color: {COLORS['primary']};
            }}
        """)
        self._bell_btn.clicked.connect(self._open_notification)
        
        self._badge_dot = QLabel(self._bell_btn)
        self._badge_dot.setFixedSize(10, 10)
        self._badge_dot.setStyleSheet("""
            QLabel {
                background: #ff4444;
                border-radius: 5px;
                border: none;
            }
        """)
        self._badge_dot.move(24, 2)
        self._badge_dot.setVisible(False)
        
        lay.addWidget(self._bell_btn)
        
        # Gear
        gear_btn = QPushButton("⚙")
        gear_btn.setFixedSize(36, 36)
        gear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gear_btn.setStyleSheet(self._bell_btn.styleSheet().replace("16px", "17px"))
        gear_btn.clicked.connect(self._open_settings)
        lay.addWidget(gear_btn)
        
        parent_layout.addWidget(header)

    def _build_sidebar(self, parent_layout):
        self._sidebar = QFrame()
        self._sidebar.setFixedWidth(250)
        self._sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)
        lay = QVBoxLayout(self._sidebar)
        lay.setContentsMargins(8, 20, 8, 16)
        lay.setSpacing(2)
        
        nav_header = QHBoxLayout()
        nav_header.setContentsMargins(10, 0, 4, 6)
        self._nav_label = QLabel("NAVIGATION")
        self._nav_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; font-weight: 800; letter-spacing: 2px;")
        nav_header.addWidget(self._nav_label)
        lay.addLayout(nav_header)
        
        # Indicator bar
        self._indicator = QFrame(self._sidebar)
        self._indicator.setFixedSize(3, 30)
        self._indicator.setStyleSheet(f"background: {COLORS['primary']}; border-radius: 2px;")
        self._indicator.move(0, 0)
        
        self._ind_anim = QPropertyAnimation(self._indicator, b"geometry")
        self._ind_anim.setDuration(280)
        self._ind_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Nav items
        nav_items = [
            ('Home', 0), ('Checker', 1), ('Unlocker', 5), 
            ('Password Changer', 3), ('Humanizer', 4), ('Joiner', 2),
            ('Cap Check', 6), ('Cleaner', 7), ('Trial Check', 8), 
            ('Separator', 9), ('Get Email', 10), ('Phone Verify', 11)
        ]
        
        self._nav_buttons = []
        self._nav_labels = []
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        
        _flag_map = {
            'Checker': 'checker', 'Cap Check': 'captcha_checker', 'Trial Check': 'trial_checker',
            'Joiner': 'joiner', 'Password Changer': 'changer', 'Humanizer': 'humanizer',
            'Unlocker': 'unlocker', 'Cleaner': 'token_cleaner', 'Separator': 'separator',
            'Get Email': 'get_token_email', 'Phone Verify': 'phone_verifier'
        }
        
        for name, index in nav_items:
            btn = QPushButton(f"  {name}")
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(SIDEBAR_BUTTON_STYLE)
            
            # Check if tool is disabled server-side
            if name in _flag_map:
                flag_name = _flag_map[name]
                if not ServerManager.instance().is_tool_enabled(flag_name):
                    btn.setEnabled(False)
                    btn.setToolTip("This tool is currently disabled")
                    btn.setStyleSheet(btn.styleSheet() + "\nQPushButton { color: #555 !important; }\nQPushButton:hover { background: transparent !important; }")
            
            btn.clicked.connect(lambda _, idx=index: self._switch_page(idx))
            self._button_group.addButton(btn, index)
            lay.addWidget(btn)
            self._nav_buttons.append(btn)
            
        lay.addStretch()
        
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {COLORS['border_light']}; max-height: 1px; border: none;")
        lay.addWidget(sep)
        
        self._footer_label = QLabel("THEBOY TOOLS")
        self._footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._footer_label.setStyleSheet(f"color: {COLORS['text_disabled']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; margin-top: 8px;")
        lay.addWidget(self._footer_label)
        
        parent_layout.addWidget(self._sidebar)

    def _animate_indicator(self, button):
        rect = button.geometry()
        start = self._indicator.geometry()
        end = QRect(0, rect.y(), 3, rect.height())
        
        self._ind_anim.setStartValue(start)
        self._ind_anim.setEndValue(end)
        self._ind_anim.start()

    def _switch_page(self, index):
        self._pages.setCurrentIndex(index)
        
        # Find button in group
        btn = self._button_group.button(index)
        if btn:
            btn.setChecked(True)
            self._animate_indicator(btn)
            
        # Update RPC
        page_name = self._PAGE_RPC_MAP.get(index, 'idle')
        DiscordRPCManager.instance().update_activity(page_name)
        
        if index == 12: # Settings page
            self._settings_page.reload()

    def _toggle_sidebar(self):
        is_visible = self._sidebar.isVisible()
        self._sidebar.setVisible(not is_visible)
        self._toggle_btn.setText("≡" if is_visible else "✕")
        self._nav_label.setVisible(not is_visible)
        self._footer_label.setVisible(not is_visible)
        self._indicator.setVisible(not is_visible)

    def _update_presence(self, count):
        self._live_label.setText(f"Online : {count}")

    def _on_announcement_updated(self, text, ann_id):
        self._current_announcement = text
        self._current_announcement_id = ann_id
        
        if ann_id not in self._read_announcement_ids:
            self._badge_dot.setVisible(True)
            SoundManager.instance().click()

    def _open_notification(self):
        if not self._current_announcement:
            return
            
        SoundManager.instance().click()
        
        dlg = NotificationDialog(self, self._current_announcement)
        
        # Position below bell
        bell_pos = self._bell_btn.mapToGlobal(self._bell_btn.rect().bottomRight())
        dlg_x = bell_pos.x() - dlg.width() + 20
        dlg_y = bell_pos.y() + 8
        dlg.move(dlg_x, dlg_y)
        
        dlg.exec()
        
        # Mark as read
        if self._current_announcement_id not in self._read_announcement_ids:
            self._read_announcement_ids.append(self._current_announcement_id)
            self._read_announcement_ids = self._read_announcement_ids[-50:] # Keep last 50
            self._config.set('_read_announcement_ids', self._read_announcement_ids)
            self._config.save()
            self._badge_dot.setVisible(False)

    def _navigate_from_home(self, page_index):
        """Called when a home page feature card is clicked."""
        self._switch_page(page_index)
        ServerManager.instance().log_activity('navigate_from_home', {'target': page_index})

    def _open_settings(self):
        """Navigate to the settings page."""
        self._switch_page(12)
        ServerManager.instance().log_activity('settings_open')

    def closeEvent(self, event):
        self._config.set('window.width', self.width())
        self._config.set('window.height', self.height())
        self._config.set('window.x', self.x())
        self._config.set('window.y', self.y())
        self._config.save()
        super().closeEvent(event)

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox, QLineEdit, QScrollArea
from PyQt6.QtCore import Qt, pyqtSlot

from gui.theme import COLORS
from gui.pages.page_helpers import glass_frame, page_header, stat_chip, shadow, sub_card, section_label, INPUT_STYLE
from gui.widgets.token_input import TokenInput
from gui.widgets.proxy_input import ProxyInput
from gui.widgets.console_widget import ConsoleWidget
from gui.widgets.progress_widget import ProgressWidget
from gui.widgets.settings_panel import SettingsPanel
from gui.widgets.animated_button import AnimatedButton
from tools.captcha_checker.captcha_checker import CaptchaChecker
from core.worker import ToolWorker
from core.sound_manager import SoundManager
from core.proxy_manager import ProxyRotator
from core.server_manager import ServerManager
from core.config import Config

class CaptchaCheckerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = CaptchaChecker()
        self._worker = None
        self._is_running = False
        self._total = 0
        self._current = 0
        self._no_captcha = 0
        self._captcha = 0
        self._failed = 0
        self._setup_ui()

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
        self.main_layout.setSpacing(20)

        # Header
        self.main_layout.addWidget(page_header(
            "CAPTCHA CHECKER",
            "Detect join-captcha requirements without actually joining"
        ))

        # Settings Glass Card
        settings_card, settings_lay = glass_frame(18)
        settings_lay.setContentsMargins(24, 22, 24, 22)
        
        self._settings = SettingsPanel()
        
        # Target Invite Card
        inv_card, il = sub_card()
        il.setContentsMargins(20, 12, 20, 12)
        il.setSpacing(14)
        
        il.addWidget(section_label("TARGET INVITE"))
        
        self._invite_input = QLineEdit()
        self._invite_input.setText("midjourney")
        self._invite_input.setPlaceholderText("Invite code to test against (e.g. midjourney)")
        self._invite_input.setFixedHeight(36)
        self._invite_input.setStyleSheet(INPUT_STYLE)
        il.addWidget(self._invite_input)
        
        settings_lay.addWidget(inv_card)
        settings_lay.addWidget(self._settings)
        
        self.main_layout.addWidget(settings_card)

        # Inputs Row
        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(20)
        
        self._token_input = TokenInput()
        self._proxy_input = ProxyInput()
        
        inputs_row.addWidget(self._token_input, stretch=3)
        inputs_row.addWidget(self._proxy_input, stretch=2)
        
        self.main_layout.addLayout(inputs_row)

        # Actions
        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        
        self._start_btn = AnimatedButton("START CHECKING", True)
        self._start_btn.set_theme("primary")
        self._start_btn.setFixedHeight(44)
        self._start_btn.setMinimumWidth(180)
        self._start_btn.clicked.connect(self._start)
        
        self._stop_btn = AnimatedButton("STOP", True)
        self._stop_btn.set_theme("danger")
        self._stop_btn.setFixedHeight(44)
        self._stop_btn.setFixedWidth(110)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop)
        
        self._clean_btn = AnimatedButton("CLEAN OUTPUT")
        self._clean_btn.setFixedHeight(44)
        self._clean_btn.clicked.connect(self._clean_output)
        
        action_row.addWidget(self._start_btn)
        action_row.addWidget(self._stop_btn)
        action_row.addStretch()
        action_row.addWidget(self._clean_btn)
        
        self.main_layout.addLayout(action_row)

        # Stats Card
        stats_f = QFrame()
        stats_f.setStyleSheet(f"QFrame{{background:{COLORS['bg_input']};border:1px solid {COLORS['border_subtle']};border-radius:12px;}}")
        stats_f.setGraphicsEffect(shadow(blur=10, alpha=70, dy=2))
        sl = QHBoxLayout(stats_f)
        sl.setContentsMargins(16, 9, 16, 9)
        
        self._lbl_total, self._set_total = stat_chip("TOTAL", COLORS['text_secondary'])
        self._lbl_no_cap, self._set_no_cap = stat_chip("NO CAPTCHA", COLORS['success'])
        self._lbl_cap, self._set_cap = stat_chip("CAPTCHA", COLORS['warning'])
        self._lbl_fail, self._set_fail = stat_chip("FAILED", COLORS['error'])
        
        sl.addWidget(self._lbl_total)
        sl.addSpacing(20)
        sl.addWidget(self._lbl_no_cap)
        sl.addSpacing(20)
        sl.addWidget(self._lbl_cap)
        sl.addSpacing(20)
        sl.addWidget(self._lbl_fail)
        sl.addStretch()
        
        self.main_layout.addWidget(stats_f)

        # Progress & Console
        self._progress = ProgressWidget()
        self._console = ConsoleWidget()
        
        self.main_layout.addWidget(self._progress)
        self.main_layout.addWidget(self._console)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _clean_output(self):
        reply = QMessageBox.question(
            self, "Clean Output", "Delete all captcha checker results? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._tool.reset()
            self._console.log_warning("Output directory cleaned.")
            SoundManager.instance().click()

    def _start(self):
        tokens = self._token_input.tokens
        if not tokens:
            self._console.log_error("No valid tokens loaded")
            return

        cfg = Config.instance()
        if cfg.get('save_output', True):
            reply = QMessageBox.question(
                self, "Clean Output?", "Clean previous output before starting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._tool.reset()
                self._console.log_info("Previous output cleaned")

        # Reset state
        self._total = len(tokens)
        self._no_captcha = 0
        self._captcha = 0
        self._failed = 0
        self._update_stats()
        self._progress.reset(self._total)
        self._console.clear()
        
        invite_code = self._invite_input.text().strip().split('/')[-1] # Extract code if URL

        proxy_rotator = None
        if cfg.get('use_proxies', False):
            proxies = self._proxy_input.proxies
            if proxies:
                proxy_rotator = ProxyRotator(proxies)

        self._console.log_info(f"Starting check for {self._total} tokens against '{invite_code}'...")

        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._clean_btn.setEnabled(False)
        self._is_running = True

        # Start Worker
        self._worker = ToolWorker(
            task_func=self._tool.process_token,
            items=tokens,
            thread_count=self._settings.thread_count,
            proxy_rotator=proxy_rotator,
            invite_code=invite_code
        )
        
        self._worker.token_result.connect(self._on_token_result)
        self._worker.progress.connect(self._progress.update_progress)
        self._worker.log_message.connect(self._console.append_log)
        self._worker.error_signal.connect(self._on_error)
        self._worker.finished_signal.connect(self._on_finished)

        self._worker.start()
        
        ServerManager.instance().log_activity("captcha_checker_start", {
            "token_count": self._total,
            "threads": self._settings.thread_count,
            "invite": invite_code
        })

    def _stop(self):
        if self._worker:
            self._worker.cancel()
            self._console.log_warning("Stopping...")
            self._stop_btn.setEnabled(False)

    @pyqtSlot(str, dict)
    def _on_token_result(self, token: str, result: dict):
        status = result.get('status')
        message = result.get('message')
        
        if status == 'no_captcha':
            self._no_captcha += 1
            self._console.log_success(message or "No Captcha")
        elif status == 'captcha_detected':
            self._captcha += 1
            self._console.log_warning(message or "Captcha Detected")
        elif status == 'rate_limited':
            self._failed += 1
            self._console.log_warning(message or "Rate Limited")
        elif status == 'invalid':
            self._failed += 1
            self._console.log_error(f"Invalid Token: {message or 'Revoked/Expired'}")
        elif status == 'locked':
            self._failed += 1
            self._console.log_error(f"Locked: {message or 'Verification Required'}")
        else:
            self._failed += 1
            self._console.log_error(f"Failed: {message or 'Unknown Error'}")
            
        self._update_stats()

    def _update_stats(self):
        self._set_total(f"TOTAL: {self._total}")
        self._set_no_cap(str(self._no_captcha))
        self._set_cap(str(self._captcha))
        self._set_fail(str(self._failed))

    @pyqtSlot(dict)
    def _on_finished(self, results: dict):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._is_running = False
        self._progress.set_complete()
        
        self._console.log_info(f"Check complete — {self._total} tokens")
        self._console.log_info(f"Results saved to: output/{self._tool.TOOL_NAME}")
        
        SoundManager.instance().success()
        ServerManager.instance().log_activity("captcha_checker_complete", {
            "no_captcha": self._no_captcha,
            "captcha": self._captcha,
            "failed": self._failed
        })

    @pyqtSlot(str)
    def _on_error(self, error_msg: str):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._is_running = False
        self._progress.set_error(f"Worker Error: {error_msg}")
        self._console.log_error(f"Worker Error: {error_msg}")
        SoundManager.instance().error()


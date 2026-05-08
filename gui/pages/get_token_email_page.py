from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox, QScrollArea
from PyQt6.QtCore import Qt, pyqtSlot

from gui.theme import COLORS
from gui.pages.page_helpers import glass_frame, page_header, stat_chip, shadow, sub_card, section_label
from gui.widgets.token_input import TokenInput
from gui.widgets.proxy_input import ProxyInput
from gui.widgets.console_widget import ConsoleWidget
from gui.widgets.progress_widget import ProgressWidget
from gui.widgets.settings_panel import SettingsPanel
from gui.widgets.animated_button import AnimatedButton
from tools.get_token_email.get_token_email import GetTokenEmail
from core.worker import ToolWorker
from core.sound_manager import SoundManager
from core.proxy_manager import ProxyRotator
from core.server_manager import ServerManager
from core.config import Config

class GetTokenEmailPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = GetTokenEmail()
        self._worker = None
        self._is_running = False
        self._total = 0
        self._current = 0
        self._got_email = 0
        self._skipped = 0
        self._no_email = 0
        self._invalid = 0
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
            "GET TOKEN EMAIL",
            "Fetch the email associated with each token — auto-skips tokens that already have an email"
        ))

        # Info Card
        info_card, info_lay_main = glass_frame(18)
        info_lay_main.setContentsMargins(24, 22, 24, 22)
        
        self._settings = SettingsPanel()
        
        info, info_lay = sub_card()
        info_lay.setContentsMargins(20, 16, 20, 16)
        info_lay.setSpacing(10)
        
        info_title = section_label("HOW IT WORKS")
        desc = QLabel(
            "• Tokens with email already (email:pass:token) are skipped\n"
            "• Bare tokens → output: email:token\n"
            "• pass:token → output: email:pass:token\n"
            "• Results saved to output/get_token_email/"
        )
        desc.setStyleSheet(f"background: transparent; color: {COLORS['text_muted']}; font-size: 12px; font-weight: 500; line-height: 1.6;")
        desc.setWordWrap(True)
        
        info_lay.addWidget(info_title)
        info_lay.addWidget(desc)
        
        info_lay_main.addWidget(info)
        info_lay_main.addWidget(self._settings)
        
        self.main_layout.addWidget(info_card)

        # Inputs
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
        
        self._start_btn = AnimatedButton("START", True)
        self._start_btn.set_theme("danger")
        self._start_btn.setFixedHeight(44)
        self._start_btn.setMinimumWidth(160)
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

        # Stats
        stats_f = QFrame()
        stats_f.setStyleSheet(f"QFrame{{background:{COLORS['bg_input']};border:1px solid {COLORS['border_subtle']};border-radius:12px;}}")
        stats_f.setGraphicsEffect(shadow(blur=10, alpha=70, dy=2))
        sl = QHBoxLayout(stats_f)
        sl.setContentsMargins(16, 9, 16, 9)
        
        self._lbl_total, self._set_total = stat_chip("TOTAL", COLORS['text_secondary'])
        self._lbl_got_email, self._set_got_email = stat_chip("GOT EMAIL", COLORS['success'])
        self._lbl_skipped, self._set_skipped = stat_chip("SKIPPED", COLORS['primary'])
        self._lbl_no_email, self._set_no_email = stat_chip("NO EMAIL", COLORS['warning'])
        self._lbl_invalid, self._set_invalid = stat_chip("INVALID", COLORS['error'])
        
        sl.addWidget(self._lbl_total)
        sl.addSpacing(20)
        sl.addWidget(self._lbl_got_email)
        sl.addSpacing(20)
        sl.addWidget(self._lbl_skipped)
        sl.addSpacing(20)
        sl.addWidget(self._lbl_no_email)
        sl.addSpacing(20)
        sl.addWidget(self._lbl_invalid)
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
            self, "Clean Output", "Delete all Get Token Email results? This cannot be undone.",
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
        self._got_email = 0
        self._skipped = 0
        self._no_email = 0
        self._invalid = 0
        self._failed = 0
        self._update_stats()
        self._progress.reset(self._total)
        self._console.clear()
        
        proxy_rotator = None
        if cfg.get('use_proxies', False):
            proxies = self._proxy_input.proxies
            if proxies:
                proxy_rotator = ProxyRotator(proxies)

        self._console.log_info(f"Starting Get Token Email for {self._total} tokens")

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
            save_output=cfg.get('save_output', True)
        )
        
        self._worker.token_result.connect(self._on_token_result)
        self._worker.progress.connect(self._progress.update_progress)
        self._worker.log_message.connect(self._console.append_log)
        self._worker.error_signal.connect(self._on_error)
        self._worker.finished_signal.connect(self._on_finished)

        self._worker.start()
        
        ServerManager.instance().log_activity("get_token_email_start", {
            "token_count": self._total,
            "threads": self._settings.thread_count
        })

    def _stop(self):
        if self._worker:
            self._worker.cancel()
            self._console.log_warning("Stopping...")
            self._stop_btn.setEnabled(False)

    @pyqtSlot(str, dict)
    def _on_token_result(self, token: str, result: dict):
        status = result.get('status', '')
        if status == 'got_email':
            self._got_email += 1
            self._console.log_success(result.get('message', 'Got email'))
        elif status == 'skipped':
            self._skipped += 1
            self._console.log_warning(result.get('message', 'Skipped'))
        elif status == 'no_email':
            self._no_email += 1
            self._console.log_warning(result.get('message', 'No email'))
        elif status == 'invalid':
            self._invalid += 1
            self._console.log_error(result.get('message', 'Invalid'))
        else:
            self._failed += 1
            self._console.log_error(result.get('message', 'Failed'))
        self._update_stats()

    def _update_stats(self):
        self._set_total(f"TOTAL: {self._total}")
        self._set_got_email(str(self._got_email))
        self._set_skipped(str(self._skipped))
        self._set_no_email(str(self._no_email))
        self._set_invalid(str(self._invalid))

    @pyqtSlot(dict)
    def _on_finished(self, results: dict):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._is_running = False
        self._progress.set_complete()
        
        self._console.log_info(f"Complete — {self._total} tokens processed")
        self._console.log_info(f"Got Email: {self._got_email}  |  Skipped: {self._skipped}  |  No Email: {self._no_email}  |  Invalid: {self._invalid}")
        self._console.log_info("Results saved to: output/get_token_email/")
        
        SoundManager.instance().success()
        ServerManager.instance().log_activity("get_token_email_complete", {
            "got_email": self._got_email,
            "skipped": self._skipped,
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


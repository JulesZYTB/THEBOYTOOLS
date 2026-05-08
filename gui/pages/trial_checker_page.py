from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox, QScrollArea
from PyQt6.QtCore import Qt, pyqtSlot

from gui.theme import COLORS
from gui.pages.page_helpers import glass_frame, page_header, stat_chip, shadow, section_label
from gui.widgets.token_input import TokenInput
from gui.widgets.proxy_input import ProxyInput
from gui.widgets.console_widget import ConsoleWidget
from gui.widgets.progress_widget import ProgressWidget
from gui.widgets.settings_panel import SettingsPanel
from gui.widgets.animated_button import AnimatedButton
from tools.trial_checker.trial_checker import TrialChecker
from core.worker import ToolWorker
from core.sound_manager import SoundManager
from core.proxy_manager import ProxyRotator
from core.server_manager import ServerManager
from core.config import Config

class TrialCheckerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = TrialChecker()
        self._worker = None
        self._is_running = False
        self._total = 0
        self._current = 0
        self._trial_30d = 0
        self._trial_14d = 0
        self._trial = 0
        self._no_trial = 0
        self._invalid = 0
        self._locked = 0
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
            "TRIAL CHECKER",
            "Check tokens for active Nitro trial offers via the billing endpoint"
        ))

        # Settings
        settings_card, settings_lay = glass_frame(18)
        settings_lay.setContentsMargins(24, 22, 24, 22)
        self._settings = SettingsPanel()
        settings_lay.addWidget(self._settings)
        self.main_layout.addWidget(settings_card)

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

        # Stats
        stats_f = QFrame()
        stats_f.setStyleSheet(f"QFrame{{background:{COLORS['bg_input']};border:1px solid {COLORS['border_subtle']};border-radius:12px;}}")
        stats_f.setGraphicsEffect(shadow(blur=10, alpha=70, dy=2))
        sl = QHBoxLayout(stats_f)
        sl.setContentsMargins(16, 9, 16, 9)
        
        self._lbl_total, self._set_total = stat_chip("TOTAL", COLORS['text_secondary'])
        self._lbl_trial_30d, self._set_trial_30d = stat_chip("TRIAL 30D", COLORS['success'])
        self._lbl_trial_14d, self._set_trial_14d = stat_chip("TRIAL 14D", COLORS['success'])
        self._lbl_no_trial, self._set_no_trial = stat_chip("NO TRIAL", COLORS['warning'])
        self._lbl_locked, self._set_locked = stat_chip("LOCKED", COLORS['text_secondary'])
        self._lbl_invalid, self._set_invalid = stat_chip("INVALID", COLORS['error'])
        self._lbl_failed, self._set_failed = stat_chip("FAILED", COLORS['error'])
        
        sl.addWidget(self._lbl_total)
        sl.addSpacing(15)
        sl.addWidget(self._lbl_trial_30d)
        sl.addSpacing(15)
        sl.addWidget(self._lbl_trial_14d)
        sl.addSpacing(15)
        sl.addWidget(self._lbl_no_trial)
        sl.addSpacing(15)
        sl.addWidget(self._lbl_locked)
        sl.addSpacing(15)
        sl.addWidget(self._lbl_invalid)
        sl.addSpacing(15)
        sl.addWidget(self._lbl_failed)
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
            self, "Clean Output", "Delete all trial checker results? This cannot be undone.",
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
        self._trial_30d = 0
        self._trial_14d = 0
        self._trial = 0
        self._no_trial = 0
        self._invalid = 0
        self._locked = 0
        self._failed = 0
        self._update_stats()
        self._progress.reset(self._total)
        self._console.clear()
        
        proxy_rotator = None
        if cfg.get('use_proxies', False):
            proxies = self._proxy_input.proxies
            if proxies:
                proxy_rotator = ProxyRotator(proxies)

        self._console.log_info(f"Starting trial check for {self._total} tokens...")

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
        
        ServerManager.instance().log_activity("trial_checker_start", {
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
        if status == 'trial_30d':
            self._trial_30d += 1
            self._console.log_success(result.get('message', 'Trial 30D Found'))
        elif status == 'trial_14d':
            self._trial_14d += 1
            self._console.log_success(result.get('message', 'Trial 14D Found'))
        elif status == 'trial_other':
            self._trial += 1
            self._console.log_success(result.get('message', 'Trial Found'))
        elif status == 'no_trial':
            self._no_trial += 1
            self._console.log_warning(result.get('message', 'No Trial'))
        elif status == 'locked':
            self._locked += 1
            self._console.log_warning(result.get('message', 'Locked'))
        elif status == 'invalid':
            self._invalid += 1
            self._console.log_error(result.get('message', 'Invalid'))
        elif status == 'rate_limited':
            self._failed += 1
            self._console.log_warning(result.get('message', 'Rate Limited'))
        else:
            self._failed += 1
            self._console.log_error(result.get('message', 'Failed'))
        self._update_stats()

    def _update_stats(self):
        self._set_total(f"TOTAL: {self._total}")
        self._set_trial_30d(str(self._trial_30d))
        self._set_trial_14d(str(self._trial_14d))
        self._set_no_trial(str(self._no_trial))
        self._set_locked(str(self._locked))
        self._set_invalid(str(self._invalid))
        self._set_failed(str(self._failed))

    @pyqtSlot(dict)
    def _on_finished(self, results: dict):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._is_running = False
        
        if results.get('cancelled'):
            self._progress.set_stopped()
        else:
            self._progress.set_complete()
        
        self._console.log_info(f"Check complete — {self._total} tokens processed")
        self._console.log_info(f"Trials found: {self._trial_30d + self._trial_14d + self._trial}")
        self._console.log_info("Results saved to: output/trial_checker/")
        
        SoundManager.instance().success()
        ServerManager.instance().log_activity("trial_checker_complete", {
            "trial_30d": self._trial_30d,
            "trial_14d": self._trial_14d,
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


from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox, QLineEdit, QScrollArea, QRadioButton, QButtonGroup
from PyQt6.QtCore import Qt, pyqtSlot

from gui.theme import COLORS
from gui.pages.page_helpers import glass_frame, page_header, stat_chip, shadow, sub_card, section_label, notice_banner, INPUT_STYLE, RADIO_STYLE
from gui.widgets.token_input import TokenInput
from gui.widgets.proxy_input import ProxyInput
from gui.widgets.console_widget import ConsoleWidget
from gui.widgets.progress_widget import ProgressWidget
from gui.widgets.settings_panel import SettingsPanel
from gui.widgets.animated_button import AnimatedButton
from core.worker import ToolWorker
from core.proxy_manager import ProxyRotator
from core.sound_manager import SoundManager
from core.config import Config
from core.server_manager import ServerManager
from tools.changer.changer import Changer

class ChangerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = Changer()
        self._worker = None
        self._stats = {'changed': 0, 'failed': 0}
        self._cfg = Config.instance()
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
            "PASSWORD CHANGER",
            "Change passwords on tokens — requires email:pass:token format"
        ))

        # Settings Card
        settings_card, settings_lay = glass_frame(18)
        settings_lay.setContentsMargins(24, 22, 24, 22)
        
        self._settings = SettingsPanel()
        
        # Password Mode Card
        pw_card, pw_lay = sub_card()
        pw_lay.setContentsMargins(20, 16, 20, 16)
        pw_lay.setSpacing(14)
        
        pw_lay.addWidget(section_label("PASSWORD MODE"))
        
        mode_group = QButtonGroup(self)
        
        self._radio_fixed = QRadioButton("Fixed password — all tokens get the same password")
        self._radio_fixed.setChecked(True)
        self._radio_fixed.setStyleSheet(RADIO_STYLE)
        self._radio_fixed.toggled.connect(self._on_mode_changed)
        
        self._radio_random = QRadioButton("Random unique password — each token gets a different one")
        self._radio_random.setStyleSheet(RADIO_STYLE)
        
        mode_group.addButton(self._radio_fixed)
        mode_group.addButton(self._radio_random)
        
        pw_lay.addWidget(self._radio_fixed)
        pw_lay.addWidget(self._radio_random)
        
        pw_lay.addSpacing(10)
        
        self._pw_label = section_label("NEW PASSWORD")
        self._password_input = QLineEdit()
        self._password_input.setPlaceholderText("Enter the new password for all tokens")
        self._password_input.setFixedHeight(40)
        self._password_input.setStyleSheet(INPUT_STYLE)
        
        pw_lay.addWidget(self._pw_label)
        pw_lay.addWidget(self._password_input)
        
        settings_lay.addWidget(pw_card)
        
        # Notice Banner
        settings_lay.addWidget(notice_banner(
            "Tokens must be in  email:pass:token  format — current password is required"
        ))
        
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
        
        self._start_btn = AnimatedButton("START CHANGING", True)
        self._start_btn.set_theme("primary")
        self._start_btn.setFixedHeight(44)
        self._start_btn.setMinimumWidth(170)
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
        
        self._changed_lbl, self._set_changed = stat_chip("CHANGED", COLORS['success'])
        self._failed_lbl, self._set_failed = stat_chip("FAILED", COLORS['error'])
        
        sl.addWidget(self._changed_lbl)
        sl.addSpacing(20)
        sl.addWidget(self._failed_lbl)
        sl.addStretch()
        
        self.main_layout.addWidget(stats_f)

        # Progress & Console
        self._progress = ProgressWidget()
        self._console = ConsoleWidget()
        
        self.main_layout.addWidget(self._progress)
        self.main_layout.addWidget(self._console)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _on_mode_changed(self):
        is_fixed = self._radio_fixed.isChecked()
        self._password_input.setEnabled(is_fixed)
        self._pw_label.setEnabled(is_fixed)
        if not is_fixed:
            self._password_input.setPlaceholderText("(Random passwords will be generated)")
            self._pw_label.setStyleSheet(f"background:transparent;color:{COLORS['text_disabled']};font-size:10px;font-weight:800;letter-spacing:2px;")
        else:
            self._password_input.setPlaceholderText("Enter the new password for all tokens")
            self._pw_label.setStyleSheet(f"background:transparent;color:{COLORS['text_secondary']};font-size:10px;font-weight:800;letter-spacing:2px;")

    def _clean_output(self):
        reply = QMessageBox.question(
            self, "Clean Output", "Delete all changer output files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._tool.clear_output()
            self._console.log_info("Output files cleaned")
            SoundManager.instance().click()

    def _start(self):
        tokens = self._token_input.tokens
        if not tokens:
            self._console.log_warning("No tokens loaded.")
            return

        is_fixed = self._radio_fixed.isChecked()
        new_pw = self._password_input.text().strip()
        
        if is_fixed:
            if not new_pw:
                self._console.log_warning("Please enter a new password.")
                return
            if len(new_pw) < 8:
                self._console.log_warning("Password must be at least 8 characters.")
                return

        # Check format
        no_pass = [t for t in tokens if len(t.split(':')) < 3]
        if no_pass:
            self._console.log_warning(f"{len(no_pass)} token(s) missing current password — use email:pass:token format")
            return

        if self._cfg.get('save_output', True):
            reply = QMessageBox.question(
                self, "Clean Output?", "Clean previous output before starting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._tool.clear_output()
                self._console.log_info("Previous output cleaned")

        # Reset state
        self._stats = {'changed': 0, 'failed': 0}
        self._update_stats()
        self._progress.reset(len(tokens))
        self._console.clear()
        
        proxy_rotator = None
        if self._cfg.get('use_proxies', False):
            proxies = self._proxy_input.proxies
            if proxies:
                proxy_rotator = ProxyRotator(proxies)

        mode_str = "random unique passwords" if not is_fixed else "fixed password"
        self._console.log_info(f"Starting password changer — {len(tokens)} tokens — {mode_str}")
        self._console.log_info("Results saving in real-time to output/changer/")

        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._clean_btn.setEnabled(False)

        # Start Worker
        self._worker = ToolWorker(
            task_func=self._tool.process_token,
            items=tokens,
            thread_count=self._settings.thread_count,
            proxy_rotator=proxy_rotator,
            new_password=new_pw if is_fixed else None,
            use_random_password=not is_fixed
        )
        
        self._worker.progress.connect(self._progress.update_progress)
        self._worker.log_message.connect(self._console.append_log)
        self._worker.token_result.connect(self._on_token_result)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.error_signal.connect(self._on_error)

        self._progress.set_status("Changing passwords...")
        self._worker.start()
        
        ServerManager.instance().log_activity("changer_start", {
            "token_count": len(tokens),
            "mode": "random" if not is_fixed else "fixed",
            "threads": self._settings.thread_count
        })

    def _stop(self):
        if self._worker:
            self._worker.cancel()
            self._console.log_warning("Stopping changer...")
            self._stop_btn.setEnabled(False)

    @pyqtSlot(str, dict)
    def _on_token_result(self, token: str, result: dict):
        msg = result.get('message', '')
        status = result.get('status')
        if status == 'changed':
            self._stats['changed'] += 1
            self._console.log_success(msg)
        elif status in ('rate_limited', 'captcha'):
            self._stats['failed'] += 1
            self._console.log_warning(msg)
        else:
            self._stats['failed'] += 1
            self._console.log_error(msg)
        self._update_stats()

    def _update_stats(self):
        self._set_changed(str(self._stats['changed']))
        self._set_failed(str(self._stats['failed']))

    @pyqtSlot(dict)
    def _on_finished(self, results: dict):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._progress.set_complete()
        
        self._console.log_info(f"Changer complete — {self._stats['changed']} changed, {self._stats['failed']} failed")
        self._console.log_info("All results saved to output/changer/")
        
        SoundManager.instance().success()
        ServerManager.instance().log_activity("changer_complete", {
            "changed": self._stats['changed'],
            "failed": self._stats['failed']
        })

    @pyqtSlot(str)
    def _on_error(self, error_msg: str):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._progress.set_error(error_msg)
        self._console.log_error(error_msg)
        SoundManager.instance().error()


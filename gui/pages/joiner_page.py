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
from gui.widgets.toggle_switch import ToggleSwitch
from core.worker import ToolWorker
from core.proxy_manager import ProxyRotator
from core.sound_manager import SoundManager
from core.config import Config
from core.server_manager import ServerManager
from tools.joiner.joiner import Joiner

class JoinerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = Joiner()
        self._worker = None
        self._stats = {'joined': 0, 'failed': 0}
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
            "SERVER JOINER",
            "Join tokens to Discord servers via invite link"
        ))

        # Settings Glass Card
        settings_card, settings_lay = glass_frame(18)
        settings_lay.setContentsMargins(24, 22, 24, 22)
        
        self._settings = SettingsPanel()
        
        # Invite Code Input
        settings_lay.addWidget(section_label("INVITE CODE / URL"))
        self._invite_input = QLineEdit()
        self._invite_input.setPlaceholderText("discord.gg/xxxxx  or  just the invite code")
        self._invite_input.setFixedHeight(42)
        self._invite_input.setStyleSheet(INPUT_STYLE)
        settings_lay.addWidget(self._invite_input)
        
        settings_lay.addSpacing(10)
        
        # Name Change Section
        name_card, name_lay = sub_card()
        name_lay.setContentsMargins(16, 10, 16, 10)
        name_lay.setSpacing(14)
        
        name_title = QLabel("CHANGE NAME AFTER JOINING")
        name_title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        
        self._check_change_name = ToggleSwitch()
        self._new_name_input = QLineEdit()
        self._new_name_input.setPlaceholderText("New display name (optional)")
        self._new_name_input.setFixedHeight(34)
        self._new_name_input.setStyleSheet(INPUT_STYLE)
        self._new_name_input.setEnabled(False)
        
        self._check_change_name.stateChanged.connect(lambda s: self._new_name_input.setEnabled(s == 2))
        
        name_lay.addWidget(name_title)
        name_lay.addWidget(self._check_change_name)
        name_lay.addWidget(self._new_name_input)
        name_lay.addStretch(1)
        
        settings_lay.addWidget(name_card)
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
        
        self._start_btn = AnimatedButton("START JOINING", True)
        self._start_btn.set_theme("success")
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

        # Stats Card
        stats_f = QFrame()
        stats_f.setStyleSheet(f"QFrame{{background:{COLORS['bg_input']};border:1px solid {COLORS['border_subtle']};border-radius:12px;}}")
        stats_f.setGraphicsEffect(shadow(blur=10, alpha=70, dy=2))
        sl = QHBoxLayout(stats_f)
        sl.setContentsMargins(16, 9, 16, 9)
        
        self._joined_lbl, self._set_joined = stat_chip("JOINED", COLORS['success'])
        self._failed_lbl, self._set_failed = stat_chip("FAILED", COLORS['error'])
        
        sl.addWidget(self._joined_lbl)
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

    def _clean_output(self):
        reply = QMessageBox.question(
            self, "Clean Output", "Delete all joiner output files?",
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

        invite = self._invite_input.text().strip()
        if not invite:
            self._console.log_warning("Please enter an invite code or URL.")
            return

        if self._cfg.get('save_output', True):
            reply = QMessageBox.question(
                self, "Clean Output?", "Clean previous output files before starting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._tool.clear_output()
                self._console.log_info("Previous output cleaned")

        # Reset state
        self._stats = {'joined': 0, 'failed': 0}
        self._update_stats()
        self._progress.reset(len(tokens))
        self._console.clear()
        
        # Setup Proxy Rotator
        proxy_rotator = None
        if self._cfg.get('use_proxies', False):
            proxies = self._proxy_input.proxies
            if proxies:
                proxy_rotator = ProxyRotator(proxies)

        self._console.log_info(f"Starting joiner — {len(tokens)} tokens → {invite}")
        self._console.log_info("Results saving in real-time to output/joiner/")

        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._clean_btn.setEnabled(False)

        # Start Worker
        self._worker = ToolWorker(
            task_func=self._tool.process_token,
            items=tokens,
            thread_count=self._settings.thread_count,
            proxy_rotator=proxy_rotator,
            invite_code=invite,
            change_name=self._check_change_name.isChecked(),
            new_name=self._new_name_input.text().strip()
        )
        
        self._worker.progress.connect(self._progress.update_progress)
        self._worker.log_message.connect(self._console.append_log)
        self._worker.token_result.connect(self._on_token_result)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.error_signal.connect(self._on_error)

        self._progress.set_status("Joining tokens to server...")
        self._worker.start()
        
        ServerManager.instance().log_activity("joiner_start", {
            "token_count": len(tokens),
            "threads": self._settings.thread_count,
            "invite": invite
        })

    def _stop(self):
        if self._worker:
            self._worker.cancel()
            self._console.log_warning("Stopping joiner...")
            self._stop_btn.setEnabled(False)

    @pyqtSlot(str, dict)
    def _on_token_result(self, token: str, result: dict):
        msg = result.get('message', '')
        status = result.get('status')
        if status == 'joined':
            self._stats['joined'] += 1
            self._console.log_success(msg)
        elif status == 'rate_limited':
            self._stats['failed'] += 1
            self._console.log_warning(msg)
        else:
            self._stats['failed'] += 1
            self._console.log_error(msg)
        self._update_stats()

    def _update_stats(self):
        self._set_joined(str(self._stats['joined']))
        self._set_failed(str(self._stats['failed']))

    @pyqtSlot(dict)
    def _on_finished(self, results: dict):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._progress.set_complete()
        
        self._console.log_info(f"Joiner complete — {results.get('total', 0)} tokens: {self._stats['joined']} joined, {self._stats['failed']} failed")
        self._console.log_info("All results saved to output/joiner/")
        
        SoundManager.instance().success()
        ServerManager.instance().log_activity("joiner_complete", {
            "joined": self._stats['joined'],
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


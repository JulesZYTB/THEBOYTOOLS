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
from tools.token_cleaner.token_cleaner import TokenCleaner
from core.worker import ToolWorker
from core.sound_manager import SoundManager
from core.proxy_manager import ProxyRotator
from core.server_manager import ServerManager
from core.config import Config

class TokenCleanerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = TokenCleaner()
        self._worker = None
        self._is_running = False
        self._total = 0
        self._current = 0
        self._cleaned = 0
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
            "TOKEN CLEANER",
            "Leave all servers & close DMs — make tokens look brand new"
        ))

        # Settings Card
        settings_card, settings_lay = glass_frame(18)
        settings_lay.setContentsMargins(24, 22, 24, 22)
        
        self._settings = SettingsPanel()
        
        # Options Card
        opts_card, opts_lay = sub_card()
        opts_lay.setContentsMargins(20, 16, 20, 16)
        opts_lay.setSpacing(14)
        
        opts_lay.addWidget(section_label("CLEANING OPTIONS"))
        
        toggles_row = QHBoxLayout()
        toggles_row.setSpacing(28)
        
        # Leave Servers Toggle
        leave_grp = QHBoxLayout(); leave_grp.setSpacing(10)
        self._check_leave = ToggleSwitch()
        self._check_leave.setChecked(True)
        leave_lbl = QLabel("Leave All Servers")
        leave_lbl.setStyleSheet(f"background:transparent;color:{COLORS['text_secondary']};font-size:13px;font-weight:600;")
        leave_grp.addWidget(self._check_leave); leave_grp.addWidget(leave_lbl)
        toggles_row.addLayout(leave_grp)
        
        # Close DMs Toggle
        dm_grp = QHBoxLayout(); dm_grp.setSpacing(10)
        self._check_dms = ToggleSwitch()
        self._check_dms.setChecked(True)
        dm_lbl = QLabel("Close All DMs")
        dm_lbl.setStyleSheet(leave_lbl.styleSheet())
        dm_grp.addWidget(self._check_dms); dm_grp.addWidget(dm_lbl)
        toggles_row.addLayout(dm_grp)
        
        toggles_row.addStretch()
        opts_lay.addLayout(toggles_row)
        
        # Specific Guild Input
        guild_row = QVBoxLayout(); guild_row.setSpacing(8)
        guild_row.addWidget(section_label("SPECIFIC GUILD ID (OPTIONAL)"))
        self._guild_input = QLineEdit()
        self._guild_input.setPlaceholderText("Leave empty to leave ALL servers")
        self._guild_input.setFixedHeight(34)
        self._guild_input.setStyleSheet(INPUT_STYLE)
        guild_row.addWidget(self._guild_input)
        opts_lay.addLayout(guild_row)
        
        settings_lay.addWidget(opts_card)
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
        
        self._start_btn = AnimatedButton("START CLEANING", True)
        self._start_btn.set_theme("danger")
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
        self._lbl_cleaned, self._set_cleaned = stat_chip("CLEANED", COLORS['success'])
        self._lbl_invalid, self._set_invalid = stat_chip("INVALID", COLORS['warning'])
        self._lbl_failed, self._set_failed = stat_chip("FAILED", COLORS['error'])
        
        sl.addWidget(self._lbl_total)
        sl.addSpacing(20)
        sl.addWidget(self._lbl_cleaned)
        sl.addSpacing(20)
        sl.addWidget(self._lbl_invalid)
        sl.addSpacing(20)
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
            self, "Clean Output", "Delete all token cleaner results? This cannot be undone.",
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

        leave_servers = self._check_leave.isChecked()
        close_dms = self._check_dms.isChecked()
        
        if not leave_servers and not close_dms:
            self._console.log_error("Enable at least one option: Leave Servers or Close DMs")
            return

        cfg = Config.instance()
        
        # Confirmation
        actions = []
        if leave_servers: actions.append("leave ALL servers" if not self._guild_input.text().strip() else f"leave guild {self._guild_input.text().strip()}")
        if close_dms: actions.append("close ALL DMs")
        
        confirm_msg = f"This will {' and '.join(actions)} on {len(tokens)} tokens.\n\nThis action CANNOT be undone. Continue?"
        reply = QMessageBox.question(self, "Confirm Cleaning", confirm_msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            self._console.log_info("Cleaning cancelled")
            return

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
        self._cleaned = 0
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

        target_guild = self._guild_input.text().strip()
        self._console.log_info(f"Starting cleaner for {self._total} tokens — {'leave ' + (target_guild if target_guild else 'ALL servers') if leave_servers else ''}{', ' if leave_servers and close_dms else ''}{'close all DMs' if close_dms else ''}")

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
            save_output=cfg.get('save_output', True),
            leave_servers=leave_servers,
            close_dms=close_dms,
            target_guild_id=target_guild
        )
        
        self._worker.token_result.connect(self._on_token_result)
        self._worker.progress.connect(self._progress.update_progress)
        self._worker.log_message.connect(self._console.append_log)
        self._worker.error_signal.connect(self._on_error)
        self._worker.finished_signal.connect(self._on_finished)

        self._worker.start()
        
        ServerManager.instance().log_activity("cleaner_start", {
            "token_count": self._total,
            "threads": self._settings.thread_count,
            "leave_servers": leave_servers,
            "close_dms": close_dms
        })

    def _stop(self):
        if self._worker:
            self._worker.cancel()
            self._console.log_warning("Stopping...")
            self._stop_btn.setEnabled(False)

    @pyqtSlot(str, dict)
    def _on_token_result(self, token: str, result: dict):
        status = result.get('status', '')
        if status == 'cleaned':
            self._cleaned += 1
            self._console.log_success(result.get('message', 'Cleaned'))
        elif status == 'invalid':
            self._invalid += 1
            self._console.log_warning(result.get('message', 'Invalid'))
        else:
            self._failed += 1
            self._console.log_error(result.get('message', 'Failed'))
        self._update_stats()

    def _update_stats(self):
        self._set_total(f"TOTAL: {self._total}")
        self._set_cleaned(str(self._cleaned))
        self._set_invalid(str(self._invalid))
        self._set_failed(str(self._failed))

    @pyqtSlot(dict)
    def _on_finished(self, results: dict):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._is_running = False
        self._progress.set_complete()
        
        self._console.log_info(f"Cleaning complete — {self._total} tokens processed")
        self._console.log_info(f"Cleaned: {self._cleaned}")
        self._console.log_info("Results saved to: output/token_cleaner/")
        
        SoundManager.instance().success()
        ServerManager.instance().log_activity("cleaner_complete", {
            "cleaned": self._cleaned,
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


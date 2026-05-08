import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox, QFileDialog, QScrollArea, QLineEdit
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
from core.server_manager import ServerManager
from tools.humanizer.humanizer import Humanizer

class HumanizerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = Humanizer()
        self._worker = None
        self._pfp_folder = ""
        self._stats = {'success': 0, 'failed': 0}
        self._setup_ui()
        self._load_default_pfps()

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
            "TOKEN HUMANIZER",
            "Add PFP, display name & bio to make tokens appear human"
        ))

        # Settings Card
        settings_card, settings_lay = glass_frame(18)
        settings_lay.setContentsMargins(24, 22, 24, 22)
        
        self._settings = SettingsPanel()
        
        # Humanization Options
        opts_card, opts_lay = sub_card()
        opts_lay.setContentsMargins(20, 16, 20, 16)
        opts_lay.setSpacing(14)
        
        opts_lay.addWidget(section_label("HUMANIZATION OPTIONS"))
        
        checks_row = QHBoxLayout()
        checks_row.setSpacing(28)
        
        def _toggle_group(label):
            grp = QVBoxLayout()
            grp.setSpacing(10)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1.5px;")
            sw = ToggleSwitch()
            sw.setChecked(True)
            grp.addWidget(lbl)
            grp.addWidget(sw)
            return sw, grp
            
        self._check_avatar, ag = _toggle_group("Profile Picture")
        self._check_name, ng = _toggle_group("Display Name")
        self._check_bio, bg = _toggle_group("Bio")
        self._check_single_pfp, spg = _toggle_group("Use Single PFP")
        self._check_single_pfp.setChecked(False)
        
        checks_row.addLayout(ag)
        checks_row.addLayout(ng)
        checks_row.addLayout(bg)
        checks_row.addLayout(spg)
        
        checks_row.addStretch()
        opts_lay.addLayout(checks_row)
        
        opts_lay.addSpacing(16)
        
        # Fixed Row
        fixed_row = QHBoxLayout()
        fixed_row.setSpacing(20)
        
        g = QVBoxLayout(); g.setSpacing(8)
        fn_lbl = QLabel("FIXED NAME")
        fn_lbl.setStyleSheet(f"background:transparent;color:{COLORS['text_secondary']};font-size:11px;font-weight:700;letter-spacing:1.5px;")
        self._fixed_name_input = QLineEdit()
        self._fixed_name_input.setPlaceholderText("Leave empty for random")
        self._fixed_name_input.setFixedHeight(30)
        self._fixed_name_input.setMaximumWidth(200)
        self._fixed_name_input.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['bg_card_alt']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
            }}
        """)
        g.addWidget(fn_lbl); g.addWidget(self._fixed_name_input); fixed_row.addLayout(g)
        
        g = QVBoxLayout(); g.setSpacing(8)
        fb_lbl = QLabel("FIXED BIO")
        fb_lbl.setStyleSheet(f"background:transparent;color:{COLORS['text_secondary']};font-size:11px;font-weight:700;letter-spacing:1.5px;")
        self._fixed_bio_input = QLineEdit()
        self._fixed_bio_input.setPlaceholderText("Leave empty for random")
        self._fixed_bio_input.setFixedHeight(30)
        self._fixed_bio_input.setMaximumWidth(280)
        self._fixed_bio_input.setStyleSheet(self._fixed_name_input.styleSheet())
        g.addWidget(fb_lbl); g.addWidget(self._fixed_bio_input); fixed_row.addLayout(g)
        fixed_row.addStretch()
        opts_lay.addLayout(fixed_row)
        
        opts_lay.addSpacing(12)
        
        # PFP Folder Row
        pfp_row = QHBoxLayout()
        pfp_row.setSpacing(12)
        
        g = QVBoxLayout(); g.setSpacing(8)
        pfp_lbl = QLabel("PFP FOLDER")
        pfp_lbl.setStyleSheet(fn_lbl.styleSheet())
        
        inner_row = QHBoxLayout()
        inner_row.setSpacing(10)
        
        self._pfp_path_label = QLabel("humanizer_pfps")
        self._pfp_path_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        
        self._pfp_count_label = QLabel("0 images")
        self._pfp_count_label.setStyleSheet(f"""
            background: {COLORS['tertiary_dim']};
            color: {COLORS['tertiary']};
            border: 1px solid {COLORS['tertiary_border']};
            border-radius: 8px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 800;
        """)
        
        browse_btn = AnimatedButton("BROWSE")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._browse_pfp_folder)
        
        inner_row.addWidget(self._pfp_path_label)
        inner_row.addWidget(self._pfp_count_label)
        inner_row.addWidget(browse_btn)
        inner_row.addStretch()
        
        g.addWidget(pfp_lbl); g.addLayout(inner_row)
        opts_lay.addLayout(g)
        
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
        
        self._start_btn = AnimatedButton("START HUMANIZING", True)
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
        
        self._succ_lbl, self._set_succ = stat_chip("SUCCESS", COLORS['success'])
        self._fail_lbl, self._set_fail = stat_chip("FAILED", COLORS['error'])
        
        sl.addWidget(self._succ_lbl)
        sl.addSpacing(20)
        sl.addWidget(self._fail_lbl)
        sl.addStretch()
        
        self.main_layout.addWidget(stats_f)

        # Progress & Console
        self._progress = ProgressWidget()
        self._console = ConsoleWidget()
        
        self.main_layout.addWidget(self._progress)
        self.main_layout.addWidget(self._console)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _load_default_pfps(self):
        root = os.getcwd()
        folder = os.path.join(root, "humanizer_pfps")
        if os.path.exists(folder):
            self._set_pfp_folder(folder)

    def _browse_pfp_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select PFP Folder")
        if folder:
            self._set_pfp_folder(folder)

    def _set_pfp_folder(self, folder):
        self._pfp_folder = folder
        self._pfp_path_label.setText(os.path.basename(folder))
        images = self._tool.load_pfp_images(folder)
        self._pfp_count_label.setText(f"{len(images)} images")

    def _clean_output(self):
        reply = QMessageBox.question(
            self, "Clean Output", "Delete all humanizer output files?",
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

        if self._check_avatar.isChecked():
            images = self._tool.load_pfp_images(self._pfp_folder)
            if not images:
                self._console.log_warning("No PFP images found. Add images to the folder or disable avatar.")
                return

        cfg = Config.instance()
        if cfg.get('save_output', True):
            reply = QMessageBox.question(
                self, "Clean Output?", "Clean previous output before starting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._tool.clear_output()
                self._console.log_info("Previous output cleaned")

        # Reset state
        self._stats = {'success': 0, 'failed': 0}
        self._update_stats()
        self._progress.reset(len(tokens))
        self._console.clear()
        
        proxy_rotator = None
        if cfg.get('use_proxies', False):
            proxies = self._proxy_input.proxies
            if proxies:
                proxy_rotator = ProxyRotator(proxies)

        self._console.log_info(f"Starting humanizer — {len(tokens)} tokens")
        if not cfg.get('save_output', True):
            self._console.log_info(" — Output saving DISABLED")
        else:
            self._console.log_info("Results saving in real-time to output/humanizer/")

        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._clean_btn.setEnabled(False)

        # Start Worker
        self._worker = ToolWorker(
            task_func=self._tool.process_token,
            items=tokens,
            thread_count=self._settings.thread_count,
            proxy_rotator=proxy_rotator,
            set_avatar=self._check_avatar.isChecked(),
            set_display_name=self._check_name.isChecked(),
            set_bio=self._check_bio.isChecked(),
            fixed_name=self._fixed_name_input.text().strip(),
            fixed_bio=self._fixed_bio_input.text().strip(),
            use_single_pfp=self._check_single_pfp.isChecked()
        )
        
        self._worker.progress.connect(self._progress.update_progress)
        self._worker.log_message.connect(self._console.append_log)
        self._worker.token_result.connect(self._on_token_result)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.error_signal.connect(self._on_error)

        self._progress.set_status("Humanizing tokens...")
        self._worker.start()
        
        ServerManager.instance().log_activity("humanizer_start", {
            "token_count": len(tokens),
            "threads": self._settings.thread_count,
            "avatar": self._check_avatar.isChecked(),
            "bio": self._check_bio.isChecked()
        })

    def _stop(self):
        if self._worker:
            self._worker.cancel()
            self._console.log_warning("Stopping humanizer...")
            self._stop_btn.setEnabled(False)

    @pyqtSlot(str, dict)
    def _on_token_result(self, token: str, result: dict):
        msg = result.get('message', '')
        status = result.get('status')
        if status == 'humanized':
            self._stats['success'] += 1
            self._console.log_success(msg)
        elif status == 'rate_limited':
            self._stats['failed'] += 1
            self._console.log_warning(msg)
        else:
            self._stats['failed'] += 1
            self._console.log_error(msg)
        self._update_stats()

    def _update_stats(self):
        self._set_succ(str(self._stats['success']))
        self._set_fail(str(self._stats['failed']))

    @pyqtSlot(dict)
    def _on_finished(self, results: dict):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._progress.set_complete()
        
        self._console.log_info(f"Humanizer complete — {self._stats['success']} humanized, {self._stats['failed']} failed")
        self._console.log_info("All results saved to output/humanizer/")
        
        SoundManager.instance().success()
        ServerManager.instance().log_activity("humanizer_complete", {
            "success": self._stats['success'],
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


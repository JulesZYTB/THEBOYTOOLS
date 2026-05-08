from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox, QLineEdit, QComboBox, QScrollArea
from PyQt6.QtCore import Qt, pyqtSlot, QMetaObject, Q_ARG
import threading

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
from core.logger import AppLogger
from core.server_manager import ServerManager
from tools.unlocker.email_service import get_catalog, fetch_stock
from tools.unlocker.unlocker import Unlocker

class UnlockerPage(QWidget):
    _CAPTCHA_PROVIDERS = [
        ('OnyxSolver', 'onyx'),
        ('hCaptchaSolver', 'hcaptchasolver'),
        ('VoidSolver', 'voidsolver'),
        ('AnySolver', 'anysolver'),
        ('NoPeCHA', 'nopecha'),
        ('YesCaptcha', 'yescaptcha')
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = Unlocker()
        self._worker = None
        self._stats = {'unlocked': 0, 'claimed': 0, 'failed': 0, 'invalid': 0, 'captcha': 0}
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
            "TOKEN UNLOCKER",
            "Verify unclaimed & locked tokens using an email service"
        ))

        # Settings Card
        settings_card, settings_lay = glass_frame(18)
        settings_lay.setContentsMargins(24, 22, 24, 22)
        
        self._settings = SettingsPanel()
        
        # Email Service Card
        svc_card, sl = sub_card()
        sl.setContentsMargins(20, 14, 20, 14)
        sl.setSpacing(12)
        
        row1 = QHBoxLayout()
        row1.addWidget(section_label("EMAIL SERVICE"))
        
        self._service_combo = QComboBox()
        self._service_combo.addItems(["007hotmail", "zeus", "lution"])
        self._service_combo.setFixedWidth(140)
        self._service_combo.setFixedHeight(36)
        row1.addWidget(self._service_combo)
        row1.addSpacing(10)
        
        row1.addWidget(section_label("TOKEN TYPE"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(["Unclaimed", "Locked Mail"])
        self._type_combo.setFixedWidth(140)
        self._type_combo.setFixedHeight(36)
        row1.addWidget(self._type_combo)
        
        row1.addStretch()
        
        api_hint = QLabel("Configure API keys in Settings")
        api_hint.setStyleSheet(f"background: transparent; color: {COLORS['text_muted']}; font-size: 11px; font-weight: 600; font-style: italic;")
        row1.addWidget(api_hint)
        sl.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.addWidget(section_label("EMAIL TYPE"))
        self._email_type_combo = QComboBox()
        self._email_type_combo.setMinimumWidth(340)
        self._email_type_combo.setFixedHeight(36)
        row2.addWidget(self._email_type_combo, stretch=1)
        
        self._stock_label = QLabel("")
        self._stock_label.setStyleSheet("font-size: 11px; font-weight: 600; padding: 0 6px;")
        row2.addWidget(self._stock_label)
        
        self._refresh_stock_btn = AnimatedButton("REFRESH STOCK")
        self._refresh_stock_btn.setFixedWidth(110)
        self._refresh_stock_btn.setFixedHeight(32)
        self._refresh_stock_btn.clicked.connect(self._refresh_stock)
        row2.addWidget(self._refresh_stock_btn)
        sl.addLayout(row2)
        
        settings_lay.addWidget(svc_card)
        
        # Populate email types
        saved_svc = self._cfg.get('unlocker_email_service', 0)
        self._service_combo.setCurrentIndex(saved_svc)
        self._populate_email_types()
        self._service_combo.currentIndexChanged.connect(self._on_service_changed)
        
        # Custom PW & Toggle Row
        pw_card, pl = sub_card()
        pl.setContentsMargins(20, 12, 20, 12)
        pl.setSpacing(14)
        
        row = QHBoxLayout()
        g = QVBoxLayout(); g.setSpacing(6)
        g.addWidget(section_label("CUSTOM PASSWORD (OPTIONAL)"))
        self._custom_password_input = QLineEdit()
        self._custom_password_input.setPlaceholderText("Leave empty for random password")
        self._custom_password_input.setFixedHeight(36)
        self._custom_password_input.setStyleSheet(INPUT_STYLE)
        g.addWidget(self._custom_password_input)
        row.addLayout(g)
        
        g = QVBoxLayout(); g.setSpacing(6)
        g.addWidget(section_label("TOKEN PASS = EMAIL PASS"))
        self._token_pass_eq_email_toggle = ToggleSwitch()
        self._token_pass_eq_email_toggle.setChecked(self._cfg.get('unlocker_token_pass_equals_email_pass', False))
        self._token_pass_eq_email_toggle.setToolTip("Set token password to the purchased email password")
        g.addWidget(self._token_pass_eq_email_toggle)
        row.addLayout(g)
        pl.addLayout(row)
        settings_lay.addWidget(pw_card)
        
        # Captcha Card
        cap_card, cap_lay = sub_card()
        cap_lay.setContentsMargins(16, 10, 16, 10)
        cap_lay.setSpacing(12)
        
        row = QHBoxLayout()
        cap_title = section_label("USE CAPTCHA SOLVER")
        self._captcha_toggle = ToggleSwitch()
        row.addWidget(cap_title)
        row.addWidget(self._captcha_toggle)
        row.addSpacing(20)
        
        cap_provider_lbl = QLabel("PROVIDER")
        cap_provider_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        self._captcha_combo = QComboBox()
        self._captcha_combo.setFixedWidth(150)
        self._captcha_combo.setFixedHeight(34)
        for display, key in self._CAPTCHA_PROVIDERS:
            self._captcha_combo.addItem(display, key)
        
        saved_cap = self._cfg.get('unlocker_captcha_provider', 0)
        self._captcha_combo.setCurrentIndex(saved_cap)
        
        row.addWidget(cap_provider_lbl)
        row.addWidget(self._captcha_combo)
        row.addStretch()
        
        self._captcha_combo.setEnabled(False)
        self._captcha_toggle.stateChanged.connect(lambda s: self._captcha_combo.setEnabled(s == 2))
        
        cap_lay.addLayout(row)
        settings_lay.addWidget(cap_card)
        
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
        
        self._start_btn = AnimatedButton("START UNLOCKER", True)
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
        sl2 = QHBoxLayout(stats_f)
        sl2.setContentsMargins(16, 9, 16, 9)
        
        self._unlocked_lbl, self._set_unlocked = stat_chip("UNLOCKED", COLORS['success'])
        self._claimed_lbl, self._set_claimed = stat_chip("CLAIMED", "#60a5fa")
        self._failed_lbl, self._set_failed = stat_chip("FAILED", COLORS['error'])
        self._invalid_lbl, self._set_invalid = stat_chip("INVALID", COLORS['warning'])
        
        sl2.addWidget(self._unlocked_lbl)
        sl2.addSpacing(20)
        sl2.addWidget(self._claimed_lbl)
        sl2.addSpacing(20)
        sl2.addWidget(self._failed_lbl)
        sl2.addSpacing(20)
        sl2.addWidget(self._invalid_lbl)
        sl2.addStretch()
        
        self.main_layout.addWidget(stats_f)

        # Progress & Console
        self._progress = ProgressWidget()
        self._console = ConsoleWidget()
        
        self.main_layout.addWidget(self._progress)
        self.main_layout.addWidget(self._console)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _on_service_changed(self):
        self._populate_email_types()
        self._cfg.set('unlocker_email_service', self._service_combo.currentIndex())

    def _populate_email_types(self):
        service = self._service_combo.currentText()
        catalog = get_catalog(service)
        self._email_type_combo.clear()
        for item in catalog:
            label = f"{item['display']}  —  ${item['price']}  —  {item['lifetime']}"
            self._email_type_combo.addItem(label, item['api_param'])

    def _refresh_stock(self):
        service = self._service_combo.currentText()
        api_key = self._cfg.get(f'email_api_keys.{service}', '')
        
        if not api_key:
            self._console.log_error(f"No API key configured for {service}. Open Settings to add it.")
            return

        self._refresh_stock_btn.setEnabled(False)
        self._stock_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self._stock_label.setText("Fetching stock...")

        def _fetch():
            stock = fetch_stock(service, api_key)
            # Use QMetaObject.invokeMethod to update UI from thread
            QMetaObject.invokeMethod(self, "_apply_stock", Qt.ConnectionType.QueuedConnection, Q_ARG(str, str(stock)))

        threading.Thread(target=_fetch, daemon=True).start()

    @pyqtSlot(str)
    def _apply_stock(self, stock_str: str):
        import ast
        try:
            stock_map = ast.literal_eval(stock_str)
        except:
            stock_map = {}
            
        self._refresh_stock_btn.setEnabled(True)
        if not stock_map:
            self._stock_label.setStyleSheet(f"color: {COLORS['error']};")
            self._stock_label.setText("Failed to fetch")
            return
            
        service = self._service_combo.currentText()
        catalog = get_catalog(service)
        current_idx = self._email_type_combo.currentIndex()
        
        self._email_type_combo.blockSignals(True)
        self._email_type_combo.clear()
        for item in catalog:
            count = stock_map.get(item['api_param'], '?')
            label = f"{item['display']}  —  ${item['price']}  —  {item['lifetime']}  ({count} in stock)"
            self._email_type_combo.addItem(label, item['api_param'])
            
        if 0 <= current_idx < self._email_type_combo.count():
            self._email_type_combo.setCurrentIndex(current_idx)
        self._email_type_combo.blockSignals(False)
        
        self._stock_label.setStyleSheet(f"color: {COLORS['success']};")
        self._stock_label.setText("Stock updated")

    def _clean_output(self):
        reply = QMessageBox.question(
            self, "Clean Output", "Delete all unlocker output files?",
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

        service = self._service_combo.currentText()
        api_key = self._cfg.get(f'email_api_keys.{service}', '')
        if not api_key:
            self._console.log_error(f"No API key configured for {service}. Open Settings (gear icon) to add your API key.")
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
        self._stats = {'unlocked': 0, 'claimed': 0, 'failed': 0, 'invalid': 0, 'captcha': 0}
        self._update_stats()
        self._progress.reset(len(tokens))
        self._console.clear()
        
        proxy_rotator = None
        use_proxies = self._cfg.get('use_proxies', False)
        thread_count = self._settings.thread_count
        
        if use_proxies:
            proxies = self._proxy_input.proxies
            if proxies:
                proxy_rotator = ProxyRotator(proxies)
        else:
            if thread_count > 15:
                thread_count = 15
                self._console.log_warning("⚠ Proxyless mode: threads capped to 15.")

        email_category = self._email_type_combo.currentData()
        email_type_display = self._email_type_combo.currentText().split('—')[0].strip()

        self._console.log_info(f"Starting Unlocker — {len(tokens)} tokens, Service: {service} ({email_type_display}), Threads: {thread_count}")
        
        # Captcha Config
        captcha_kwargs = {}
        if self._captcha_toggle.isChecked():
            provider_key = self._captcha_combo.currentData()
            cap_api_key = self._cfg.get(f'phone_verifier.captcha_api_keys.{provider_key}', '')
            if not cap_api_key:
                self._console.log_error(f"No API key for {provider_key}. Open Settings to add your captcha solver API key.")
                return
            captcha_kwargs = {'captcha_solver': provider_key, 'captcha_api_key': cap_api_key}
            self._console.log_info(f"Captcha solver: {provider_key}")

        token_pass_eq = self._token_pass_eq_email_toggle.isChecked()
        if token_pass_eq:
            self._console.log_info("Token password = Email password: ON")

        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._clean_btn.setEnabled(False)

        # Start Worker
        self._worker = ToolWorker(
            task_func=self._tool.process_token,
            items=tokens,
            thread_count=thread_count,
            proxy_rotator=proxy_rotator,
            email_service=service,
            api_key=api_key,
            email_category=email_category,
            token_type=self._type_combo.currentText(),
            custom_password=self._custom_password_input.text().strip(),
            token_pass_eq_email_pass=token_pass_eq,
            captcha_kwargs=captcha_kwargs
        )
        
        self._worker.progress.connect(self._progress.update_progress)
        self._worker.log_message.connect(self._console.append_log)
        self._worker.token_result.connect(self._on_token_result)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.error_signal.connect(self._on_error)

        self._progress.set_status("Unlocking tokens...")
        self._worker.start()
        
        ServerManager.instance().log_activity("unlocker_start", {
            "token_count": len(tokens),
            "email_service": service,
            "email_type": email_type_display,
            "threads": thread_count,
            "token_type": self._type_combo.currentText()
        })

    def _stop(self):
        if self._worker:
            self._worker.cancel()
            self._console.log_warning("Stopping unlocker...")
            self._stop_btn.setEnabled(False)

    @pyqtSlot(str, dict)
    def _on_token_result(self, token: str, result: dict):
        status = result.get('status', 'error')
        msg = result.get('message', '')
        if status == 'unlocked':
            self._stats['unlocked'] += 1
            self._console.log_success(msg)
        elif status == 'claimed':
            self._stats['claimed'] += 1
            self._console.log_success(msg)
        elif status == 'manual_action':
            self._stats['unlocked'] += 1
            self._console.log_success(f"✅ {msg}")
        elif status == 'invalid':
            self._stats['invalid'] += 1
            self._console.log_warning(msg)
        elif status == 'captcha':
            self._stats['captcha'] += 1
            self._console.log_warning(msg)
        else:
            self._stats['failed'] += 1
            self._console.log_error(msg)
        self._update_stats()

    def _update_stats(self):
        self._set_unlocked(str(self._stats['unlocked']))
        self._set_claimed(str(self._stats['claimed']))
        self._set_failed(str(self._stats['failed']))
        self._set_invalid(str(self._stats['invalid']))

    @pyqtSlot(dict)
    def _on_finished(self, results: dict):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._progress.set_complete()
        
        total_success = self._stats['unlocked'] + self._stats['claimed']
        self._console.log_info(f"Unlocker complete — {results.get('total', 0)} tokens processed. ({total_success} success, {self._stats['failed']} failed)")
        
        SoundManager.instance().success()
        ServerManager.instance().log_activity("unlocker_complete", {
            "unlocked": self._stats['unlocked'],
            "claimed": self._stats['claimed'],
            "failed": self._stats['failed'],
            "invalid": self._stats['invalid']
        })

    @pyqtSlot(str)
    def _on_error(self, error_msg: str):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._progress.set_error(error_msg)
        self._console.log_error(error_msg)
        SoundManager.instance().error()


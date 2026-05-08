from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox, 
                             QScrollArea, QComboBox, QPushButton, QTreeWidget, QTreeWidgetItem, 
                             QHeaderView, QAbstractItemView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer

from gui.theme import COLORS
from gui.pages.page_helpers import glass_frame, page_header, stat_chip, shadow, sub_card, section_label
from gui.widgets.token_input import TokenInput
from gui.widgets.proxy_input import ProxyInput
from gui.widgets.console_widget import ConsoleWidget
from gui.widgets.progress_widget import ProgressWidget
from gui.widgets.settings_panel import SettingsPanel
from gui.widgets.animated_button import AnimatedButton
from tools.phone_verifier.phone_verifier import PhoneVerifier
from tools.phone_verifier.sms_service import fetch_countries, fetch_operators
from core.worker import ToolWorker
from core.sound_manager import SoundManager
from core.proxy_manager import ProxyRotator
from core.server_manager import ServerManager
from core.config import Config

class _CountryWorker(QThread):
    result = pyqtSignal(list, str)
    def __init__(self, service, api_key):
        super().__init__()
        self._service = service
        self._api_key = api_key
    def run(self):
        try:
            countries = fetch_countries(self._service, self._api_key)
            self.result.emit(countries, "")
        except Exception as e:
            self.result.emit([], str(e))

class _OperatorWorker(QThread):
    result = pyqtSignal(list, str)
    def __init__(self, service, api_key, country_id):
        super().__init__()
        self._service = service
        self._api_key = api_key
        self._country_id = country_id
    def run(self):
        try:
            operators = fetch_operators(self._service, self._api_key, self._country_id)
            self.result.emit(operators, "")
        except Exception as e:
            self.result.emit([], str(e))

class PhoneVerifierPage(QWidget):
    _CAPTCHA_PROVIDERS = [
        ('OnyxSolver', 'onyx'),
        ('hCaptchaSolver', 'hcaptchasolver'),
        ('VoidSolver', 'voidsolver'),
        ('AnySolver', 'anysolver'),
        ('NoPeCHA', 'nopecha'),
        ('YesCaptcha', 'yescaptcha')
    ]
    
    _SMS_PROVIDERS = [
        ('5sim', '5sim'),
        ('SMSBower', 'smsbower'),
        ('HeroSMS', 'herosms'),
        ('TigerSMS', 'tigersms')
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = PhoneVerifier()
        self._worker = None
        self._is_running = False
        self._config = Config.instance()
        self._total = 0
        self._current = 0
        self._verified = 0
        self._already = 0
        self._skipped = 0
        self._invalid = 0
        self._failed = 0
        
        self._selected_country_id = ""
        self._selected_operator_id = "any"
        self._country_sort = "price" # "price" or "stock"
        self._cached_countries = []
        
        self._country_worker = None
        self._operator_worker = None
        
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
            "PHONE VERIFIER",
            "Add phone numbers to Discord accounts — requires email:pass:token format"
        ))

        # Top Settings Card
        settings_card, settings_lay = glass_frame(18)
        settings_lay.setContentsMargins(24, 22, 24, 22)
        
        self._settings = SettingsPanel()
        
        # Captcha Select
        settings_row = QHBoxLayout()
        settings_row.setSpacing(12)
        
        cap_lbl = QLabel("CAPTCHA")
        cap_lbl.setStyleSheet(f"background: transparent; color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1.5px;")
        
        self._captcha_combo = QComboBox()
        self._captcha_combo.setFixedWidth(150)
        self._captcha_combo.setFixedHeight(28)
        for display, key in self._CAPTCHA_PROVIDERS:
            self._captcha_combo.addItem(display, key)
            
        saved_solver = self._config.get('phone_verifier.captcha_solver', 'onyx')
        for i in range(self._captcha_combo.count()):
            if self._captcha_combo.itemData(i) == saved_solver:
                self._captcha_combo.setCurrentIndex(i)
                break
        self._captcha_combo.currentIndexChanged.connect(self._on_captcha_provider_changed)
        
        settings_row.addWidget(cap_lbl)
        settings_row.addWidget(self._captcha_combo)
        settings_row.addStretch()
        settings_lay.addLayout(settings_row)
        settings_lay.addWidget(self._settings)
        self.main_layout.addWidget(settings_card)

        # SMS Service Card
        sms_card, sms_lay = sub_card()
        sms_lay.setContentsMargins(20, 16, 20, 16)
        sms_lay.setSpacing(12)
        
        sms_lay.addWidget(section_label("SMS SERVICE"))
        
        # Provider & Country Row
        sms_sel_row = QHBoxLayout()
        sms_sel_row.setSpacing(10)
        
        lbl_sms = QLabel("Provider")
        lbl_sms.setStyleSheet(f"background:transparent; color:{COLORS['text_muted']}; font-size:12px; font-weight:600;")
        self._sms_combo = QComboBox()
        self._sms_combo.setFixedWidth(120)
        for display, key in self._SMS_PROVIDERS:
            self._sms_combo.addItem(display, key)
        
        saved_sms = self._config.get('phone_verifier.sms_service', '5sim')
        for i in range(self._sms_combo.count()):
            if self._sms_combo.itemData(i) == saved_sms:
                self._sms_combo.setCurrentIndex(i)
                break
        self._sms_combo.currentIndexChanged.connect(self._on_sms_provider_changed)
        
        lbl_country = QLabel("Country")
        lbl_country.setStyleSheet(lbl_sms.styleSheet())
        self._country_combo = QComboBox()
        self._country_combo.setMinimumWidth(220)
        self._country_combo.setMaxVisibleItems(15)
        self._country_combo.addItem("🌍  Click 'Load' to fetch countries…", "")
        self._country_combo.currentIndexChanged.connect(self._on_country_changed)
        
        self._load_countries_btn = QPushButton("↻  Load")
        self._load_countries_btn.setFixedWidth(70)
        self._load_countries_btn.setFixedHeight(30)
        self._load_countries_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_countries_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 8px;
                font-size: 11px; font-weight: 600;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
                border-color: {COLORS['primary']};
            }}
        """)
        self._load_countries_btn.clicked.connect(self._load_countries)
        
        self._sort_btn = QPushButton("💲 Price ↑")
        self._sort_btn.setFixedWidth(90)
        self._sort_btn.setFixedHeight(30)
        self._sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sort_btn.setStyleSheet(self._load_countries_btn.styleSheet())
        self._sort_btn.setToolTip("Toggle sort: lowest price / highest stock")
        self._sort_btn.clicked.connect(self._toggle_country_sort)
        
        sms_sel_row.addWidget(lbl_sms); sms_sel_row.addWidget(self._sms_combo)
        sms_sel_row.addSpacing(8)
        sms_sel_row.addWidget(lbl_country); sms_sel_row.addWidget(self._country_combo)
        sms_sel_row.addWidget(self._load_countries_btn)
        sms_sel_row.addWidget(self._sort_btn)
        sms_sel_row.addStretch()
        sms_lay.addLayout(sms_sel_row)
        
        # Operators Tree
        op_header = QHBoxLayout()
        op_lbl = section_label("PROVIDERS / OPERATORS")
        self._op_status = QLabel("")
        self._op_status.setStyleSheet(f"color:{COLORS['text_muted']}; font-size:11px; font-weight:500;")
        op_header.addWidget(op_lbl)
        op_header.addSpacing(8)
        op_header.addWidget(self._op_status)
        op_header.addStretch()
        sms_lay.addLayout(op_header)
        
        self._op_tree = QTreeWidget()
        self._op_tree.setHeaderLabels(["ID", "Count", "Price", "Info"])
        self._op_tree.setColumnCount(4)
        self._op_tree.setRootIsDecorated(False)
        self._op_tree.setAlternatingRowColors(False)
        self._op_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._op_tree.setFixedHeight(160)
        self._op_tree.itemClicked.connect(self._on_operator_selected)
        
        hdr = self._op_tree.header()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._op_tree.setColumnWidth(0, 120)
        self._op_tree.setColumnWidth(1, 90)
        self._op_tree.setColumnWidth(2, 80)
        
        self._op_tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {COLORS['bg_input']};
                border-radius: 8px;
                color: {COLORS['text_primary']};
                font-size: 11px;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 4px 6px;
                border-bottom: 1px solid {COLORS['border_subtle']};
                border-left: 3px solid transparent;
            }}
            QTreeWidget::item:selected {{
                background: rgba(255,255,255,0.12);
                color: #fff;
                border-left: 3px solid {COLORS['primary']};
                font-weight: 700;
            }}
            QTreeWidget::item:hover {{
                background: rgba(255,255,255,0.06);
            }}
            QHeaderView::section {{
                background: {COLORS['bg_card']};
                border: none;
                border-bottom: 1px solid {COLORS['border_subtle']};
                padding: 5px 8px;
                font-size: 10px; font-weight: 700;
                text-transform: uppercase;
            }}
        """)
        sms_lay.addWidget(self._op_tree)
        
        self._selected_op_label = QLabel("No operator selected")
        self._selected_op_label.setStyleSheet(f"color:{COLORS['primary']}; font-size:11px; font-weight:600;")
        sms_lay.addWidget(self._selected_op_label)
        
        self.main_layout.addWidget(sms_card)

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
        self._lbl_verified, self._set_verified = stat_chip("VERIFIED", COLORS['success'])
        self._lbl_already, self._set_already = stat_chip("ALREADY", COLORS['primary'])
        self._lbl_skipped, self._set_skipped = stat_chip("SKIPPED", COLORS['warning'])
        self._lbl_invalid, self._set_invalid = stat_chip("INVALID", COLORS['error'])
        
        sl.addWidget(self._lbl_total)
        sl.addSpacing(18)
        sl.addWidget(self._lbl_verified)
        sl.addSpacing(18)
        sl.addWidget(self._lbl_already)
        sl.addSpacing(18)
        sl.addWidget(self._lbl_skipped)
        sl.addSpacing(18)
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

    def _on_captcha_provider_changed(self):
        solver = self._captcha_combo.currentData()
        self._config.set('phone_verifier.captcha_solver', solver)
        self._config.save()

    def _on_sms_provider_changed(self):
        service = self._sms_combo.currentData()
        self._config.set('phone_verifier.sms_service', service)
        self._config.save()
        
        # Reset country/operator UI
        self._country_combo.blockSignals(True)
        self._country_combo.clear()
        self._country_combo.addItem("🌍  Click 'Load' to fetch countries…", "")
        self._country_combo.blockSignals(False)
        self._op_tree.clear()
        self._op_status.setText("")
        self._selected_op_label.setText("Save selected SMS provider & reset country/operator lists.")
        self._cached_countries = []

    def _on_country_changed(self):
        cid = self._country_combo.currentData()
        if not cid: return
        
        self._selected_country_id = cid
        self._config.set('phone_verifier.sms_country_id', cid)
        self._config.save()
        self._load_operators()

    def _load_countries(self):
        service = self._sms_combo.currentData()
        api_key = self._config.get(f'phone_verifier.sms_api_keys.{service}', '')
        
        if not api_key:
            self._console.log_error(f"⚠  API key required for {service} — set in Settings")
            return

        self._load_countries_btn.setEnabled(False)
        self._load_countries_btn.setText("⏳ …")
        self._op_status.setText("Loading countries…")

        self._country_worker = _CountryWorker(service, api_key)
        self._country_worker.result.connect(self._on_countries_loaded)
        self._country_worker.start()

    def _on_countries_loaded(self, countries, err):
        self._load_countries_btn.setEnabled(True)
        self._load_countries_btn.setText("↻  Load")
        
        if err:
            self._console.log_error(f"Error loading countries: {err}")
            self._op_status.setText(f"⚠  Error")
            return
            
        if not countries:
            self._op_status.setText("⚠  No data")
            return
            
        self._cached_countries = countries
        self._populate_country_combo()

    def _populate_country_combo(self):
        # Sort logic
        if self._country_sort == "price":
            sorted_list = sorted(self._cached_countries, key=lambda x: float(x.get('price', 99999)))
        else:
            sorted_list = sorted(self._cached_countries, key=lambda x: int(x.get('count', 0)), reverse=True)
            
        self._country_combo.blockSignals(True)
        self._country_combo.clear()
        self._country_combo.addItem("Any Country", "0")
        
        count_with_stock = 0
        saved_id = self._config.get('phone_verifier.sms_country_id', '')
        
        for c in sorted_list:
            cid = str(c.get('id', ''))
            name = c.get('name', '?')
            count = c.get('count', 0)
            price = c.get('price', 0)
            curr = c.get('currency', '$')
            
            if count > 0: count_with_stock += 1
            
            label = f"{name}  —  {curr}{price}  •  {count} nums"
            self._country_combo.addItem(label, cid)
            
        # Try to restore selection
        for i in range(self._country_combo.count()):
            if self._country_combo.itemData(i) == saved_id:
                self._country_combo.setCurrentIndex(i)
                break
                
        self._country_combo.blockSignals(False)
        
        sort_label = "price ↑" if self._country_sort == "price" else "stock ↓"
        self._op_status.setText(f"✓  {len(self._cached_countries)} countries loaded  •  {count_with_stock} with stock  •  sorted by {sort_label}")
        self._selected_op_label.setStyleSheet(f"color:{COLORS['text_muted']}; font-size:11px; font-weight:600;")
        self._selected_op_label.setText("When a country is selected, fetch its operators.")

    def _toggle_country_sort(self):
        if not self._cached_countries: return
        self._country_sort = "stock" if self._country_sort == "price" else "price"
        self._sort_btn.setText("📦 Stock ↓" if self._country_sort == "stock" else "💲 Price ↑")
        self._populate_country_combo()

    def _load_operators(self):
        service = self._sms_combo.currentData()
        api_key = self._config.get(f'phone_verifier.sms_api_keys.{service}', '')
        cid = self._country_combo.currentData()
        
        if not api_key or not cid: return

        self._op_status.setText("Loading operators…")
        self._op_tree.clear()

        self._operator_worker = _OperatorWorker(service, api_key, cid)
        self._operator_worker.result.connect(self._on_operators_loaded)
        self._operator_worker.start()

    def _on_operators_loaded(self, operators, err):
        if err:
            self._console.log_error(f"Error loading operators: {err}")
            self._op_status.setText("⚠  Error")
            return
            
        if not operators:
            self._op_status.setText("⚠  No data")
            return
            
        self._op_tree.blockSignals(True)
        total_count = 0
        
        # Add "Any" operator first
        any_item = QTreeWidgetItem(["any", "Any", "?", "Best Stock"])
        any_item.setData(0, Qt.ItemDataRole.UserRole, "any")
        self._op_tree.addTopLevelItem(any_item)
        
        for op in operators:
            oid = str(op.get('id', '?'))
            name = op.get('name', 'Unknown')
            count = int(op.get('count', 0))
            price = op.get('price', '?')
            curr = op.get('currency', '$')
            extra = op.get('extra', '')
            
            total_count += count
            
            item = QTreeWidgetItem([oid, str(count), f"{curr}{price}", name + (" (" + extra + ")" if extra else "")])
            item.setData(0, Qt.ItemDataRole.UserRole, oid)
            if count == 0:
                item.setForeground(0, Qt.GlobalColor.red)
            else:
                item.setForeground(1, Qt.GlobalColor.green)
            self._op_tree.addTopLevelItem(item)
            
        self._op_tree.blockSignals(False)
        self._op_status.setText(f"✓  {self._op_tree.topLevelItemCount()} operators  •  {total_count} total nums")
        
        # Select first item
        self._op_tree.setCurrentItem(self._op_tree.topLevelItem(0))
        self._on_operator_selected(self._op_tree.topLevelItem(0), 0)

    def _on_operator_selected(self, item, column):
        if not item: return
        oid = item.data(0, Qt.ItemDataRole.UserRole)
        name = item.text(3)
        count = item.text(1)
        price = item.text(2)
        
        self._selected_operator_id = oid
        self._config.set('phone_verifier.sms_operator_id', oid)
        self._config.save()
        
        self._selected_op_label.setStyleSheet(f"color:{COLORS['primary']}; font-size:11px; font-weight:600;")
        self._selected_op_label.setText(f"✓  Selected: {name}  •  {count} nums  •  {price}/num")

    def _clean_output(self):
        reply = QMessageBox.question(
            self, "Clean Output", "Delete all Phone Verifier results? This cannot be undone.",
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

        service = self._sms_combo.currentData()
        sms_key = self._config.get(f'phone_verifier.sms_api_keys.{service}', '')
        if not sms_key:
            self._console.log_error(f"{service} — set it in Settings → SMS Service API Keys")
            return
            
        solver = self._captcha_combo.currentData()
        cap_key = self._config.get(f'phone_verifier.captcha_api_keys.{solver}', '')
        if not cap_key:
            self._console.log_error(f"{self._captcha_combo.currentText()} — set it in Settings → Captcha Solver API Keys")
            return

        cid = self._country_combo.currentData()
        if not cid:
            self._console.log_error("No country selected")
            return

        # Reset state
        self._total = len(tokens)
        self._verified = 0
        self._already = 0
        self._skipped = 0
        self._invalid = 0
        self._failed = 0
        self._update_stats()
        self._progress.reset(self._total)
        self._console.clear()
        
        cfg = Config.instance()
        proxy_rotator = None
        if cfg.get('use_proxies', False):
            proxies = self._proxy_input.proxies
            if proxies:
                proxy_rotator = ProxyRotator(proxies)

        self._console.log_info(f"Starting Phone Verifier for {self._total} tokens")
        self._console.log_info(f"  |  Captcha: {self._captcha_combo.currentText()}  |  SMS: {service}")
        self._console.log_info(f"  |  Country: {self._country_combo.currentText()}  |  Operator: {self._selected_operator_id}")

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
            captcha_solver=solver,
            captcha_api_key=cap_key,
            sms_service=service,
            sms_api_key=sms_key,
            sms_country=cid,
            sms_operator=self._selected_operator_id
        )
        
        self._worker.token_result.connect(self._on_token_result)
        self._worker.progress.connect(self._progress.update_progress)
        self._worker.log_message.connect(self._console.append_log)
        self._worker.error_signal.connect(self._on_error)
        self._worker.finished_signal.connect(self._on_finished)

        self._worker.start()
        
        ServerManager.instance().log_activity("phone_verifier_start", {
            "token_count": self._total,
            "threads": self._settings.thread_count,
            "captcha": solver,
            "sms": service
        })

    def _stop(self):
        if self._worker:
            self._worker.cancel()
            self._console.log_warning("Stopping...")
            self._stop_btn.setEnabled(False)

    @pyqtSlot(str, dict)
    def _on_token_result(self, token: str, result: dict):
        status = result.get('status', '')
        if status == 'verified':
            self._verified += 1
            self._console.log_success(result.get('message', 'Verified'))
        elif status == 'already_verified':
            self._already += 1
            self._console.log_warning(result.get('message', 'Already verified'))
        elif status == 'skipped':
            self._skipped += 1
            self._console.log_warning(result.get('message', 'Skipped'))
        elif status == 'invalid':
            self._invalid += 1
            self._console.log_error(result.get('message', 'Invalid'))
        else:
            self._failed += 1
            self._console.log_error(result.get('message', 'Failed'))
        self._update_stats()

    def _update_stats(self):
        self._set_total(f"TOTAL: {self._total}")
        self._set_verified(str(self._verified))
        self._set_already(str(self._already))
        self._set_skipped(str(self._skipped))
        self._set_invalid(str(self._invalid))

    @pyqtSlot(dict)
    def _on_finished(self, results: dict):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._is_running = False
        self._progress.set_complete()
        
        self._console.log_info(f"Complete — {self._total} tokens processed")
        self._console.log_info(f"Verified: {self._verified}  |  Already: {self._already}  |  Skipped: {self._skipped}  |  Invalid: {self._invalid}")
        self._console.log_info("Results saved to: output/phone_verifier/")
        
        SoundManager.instance().success()
        ServerManager.instance().log_activity("phone_verifier_complete", {
            "verified": self._verified,
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


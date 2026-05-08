from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox, 
                             QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QStackedWidget, QPushButton, QAbstractItemView, QSizePolicy, 
                             QStyledItemDelegate, QMenu, QApplication, QStyleOptionViewItem, QStyle)
from PyQt6.QtCore import Qt, pyqtSlot, QRect, QSize, QPoint, QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QBrush, QPainter, QPen, QKeySequence

from gui.theme import COLORS
from gui.pages.page_helpers import glass_frame, page_header, stat_chip, shadow
from gui.widgets.token_input import TokenInput
from gui.widgets.proxy_input import ProxyInput
from gui.widgets.console_widget import ConsoleWidget
from gui.widgets.progress_widget import ProgressWidget
from gui.widgets.settings_panel import SettingsPanel
from gui.widgets.animated_button import AnimatedButton
from core.worker import ToolWorker
from core.proxy_manager import ProxyRotator
from core.sound_manager import SoundManager
from core.server_manager import ServerManager
from tools.checker.checker import Checker

# Constants for Table
_HEADER = COLORS['bg_card']
_BG = COLORS['bg_input']
_BG_ALT = COLORS['bg_main']
_TEXT = COLORS['text_primary']
_DIM = COLORS['text_muted']
_BORDER = COLORS['border_subtle']
_ACCENT = COLORS['primary']
_GREEN = COLORS['success']
_RED = COLORS['error']
_GREY = COLORS['text_disabled']

class _TwoLineDelegate(QStyledItemDelegate):
    """
    Renders two lines of text in a single cell: bold name + dim sub-text.
    Used for the Username column. Zero widget overhead — pure QPainter.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._name_font = QFont()
        self._name_font.setPointSize(11)
        self._name_font.setWeight(QFont.Weight.DemiBold)
        self._sub_font = QFont()
        self._sub_font.setPointSize(9)

    def paint(self, painter, option, index):
        painter.save()
        
        # Background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#1e1e2e"))
        else:
            bg = _BG if index.row() % 2 == 0 else _BG_ALT
            painter.fillRect(option.rect, QColor(bg))
            
        rect = option.rect.adjusted(8, 4, -8, -4)
        half = rect.height() // 2
        
        # Name
        name = index.data(Qt.ItemDataRole.DisplayRole)
        painter.setFont(self._name_font)
        painter.setPen(QColor(_TEXT))
        painter.drawText(QRect(rect.x(), rect.y(), rect.width(), half), 
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        
        # ID/Sub
        sub = index.data(Qt.ItemDataRole.UserRole + 1) # _ROLE_SUB
        if sub:
            painter.setFont(self._sub_font)
            painter.setPen(QColor(_DIM))
            painter.drawText(QRect(rect.x(), rect.y() + half, rect.width(), half), 
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(sub))
            
        # Border
        painter.setPen(QColor(_BORDER))
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(200, 50)

class _VerifiedDelegate(QStyledItemDelegate):
    """Renders 'Email Verified: true/false' + 'Phone Verified: true/false' stacked."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._label_font = QFont()
        self._label_font.setPointSize(9)
        self._label_font.setWeight(QFont.Weight.Bold)
        self._val_font = QFont()
        self._val_font.setPointSize(9)

    def paint(self, painter, option, index):
        painter.save()
        
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#1e1e2e"))
        else:
            bg = _BG if index.row() % 2 == 0 else _BG_ALT
            painter.fillRect(option.rect, QColor(bg))
            
        data = index.data(Qt.ItemDataRole.UserRole + 2) # _ROLE_VER
        if not data: data = "0|0"
        
        email_v, phone_v = data.split('|')
        
        rect = option.rect.adjusted(10, 4, -10, -4)
        half = rect.height() // 2
        
        # Row 1: Email
        painter.setFont(self._label_font)
        painter.setPen(QColor(_GREY))
        painter.drawText(QRect(rect.x(), rect.y(), 90, half), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Email Verified:")
        
        painter.setFont(self._val_font)
        painter.setPen(QColor(_GREEN if email_v == '1' else _RED))
        painter.drawText(QRect(rect.x() + 90, rect.y(), 40, half), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "true" if email_v == '1' else "false")
        
        # Row 2: Phone
        painter.setFont(self._label_font)
        painter.setPen(QColor(_GREY))
        painter.drawText(QRect(rect.x(), rect.y() + half, 90, half), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Phone Verified:")
        
        painter.setFont(self._val_font)
        painter.setPen(QColor(_GREEN if phone_v == '1' else _RED))
        painter.drawText(QRect(rect.x() + 90, rect.y() + half, 40, half), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "true" if phone_v == '1' else "false")
        
        painter.setPen(QColor(_BORDER))
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(150, 50)

class CheckerTable(QTableWidget):
    """
    High-performance dark table — plain QTableWidgetItem, custom delegates, 60fps batching.
    """
    COLUMNS = ["Username", "Created Date", "Verified", "Guilds", "Info", "Token"]
    _ROLE_SUB = Qt.ItemDataRole.UserRole + 1
    _ROLE_VER = Qt.ItemDataRole.UserRole + 2
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending = []
        self._user_scrolled = False
        self._setup()
        
        # Flush timer to prevent UI lockup on mass insert
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(16) # ~60fps
        self._flush_timer.timeout.connect(self._flush_rows)
        self._flush_timer.start()

    def _setup(self):
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.verticalHeader().hide()
        self.setShowGrid(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False) # Too slow for large sets
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        
        self.setItemDelegateForColumn(0, _TwoLineDelegate(self))
        self.setItemDelegateForColumn(2, _VerifiedDelegate(self))
        
        hdr = self.horizontalHeader()
        hdr.setSectionsMovable(True)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setColumnWidth(0, 200) # User
        self.setColumnWidth(1, 155) # Date
        self.setColumnWidth(2, 190) # Verified
        self.setColumnWidth(3, 55)  # Guilds
        self.setColumnWidth(4, 170) # Info
        self.setColumnWidth(5, 330) # Token
        hdr.setStretchLastSection(True)
        hdr.setDefaultSectionSize(50)
        
        self._mono = QFont("Cascadia Code, Consolas, Courier New")
        self._mono.setPointSize(10)
        self._info_font = QFont()
        self._info_font.setPointSize(9)
        
        # Scroll tracking
        self.verticalScrollBar().sliderPressed.connect(self._on_slider_pressed)
        self.verticalScrollBar().sliderReleased.connect(self._on_slider_released)
        
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {_BG};
                alternate-background-color: {_BG_ALT};
                color: {_TEXT};
                border: none;
                font-size: 11px;
                outline: none;
            }}
            QHeaderView::section {{
                background-color: {_HEADER};
                border: none;
                border-bottom: 1px solid {_BORDER};
                border-right: 1px solid {_BORDER};
                padding: 6px 10px;
                font-size: 10px; font-weight: 700;
                letter-spacing: 1.5px;
                text-transform: uppercase;
            }}
            QHeaderView::section:last {{ border-right: none; }}
            QHeaderView::section:hover {{ background-color: #22222e; color: {_ACCENT}; }}
            QTableWidget::item {{
                border-bottom: 1px solid {_BORDER};
                padding: 0 6px;
            }}
            QTableWidget::item:selected {{
                background-color: #1e1e2e;
                color: {_ACCENT};
                border: 1px solid #3a3a5c;
            }}
            QScrollBar:vertical {{
                background: {_BG};
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #2e2e3e;
                border-radius: 4px;
                min-height: 24px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{
                background: {_BG};
                height: 8px;
            }}
            QScrollBar::handle:horizontal {{
                background: #2e2e3e;
                border-radius: 4px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        """)

    def _on_slider_pressed(self): self._user_scrolled = True
    def _on_slider_released(self):
        val = self.verticalScrollBar().value()
        max_val = self.verticalScrollBar().maximum()
        if val >= max_val - 30:
            self._user_scrolled = False

    def add_row(self, result: dict):
        """Queue a row for insertion — actual insert happens in _flush_rows at 60fps."""
        self._pending.append(result)

    def _flush_rows(self):
        """Drain up to 20 queued rows per timer tick with updates suspended."""
        if not self._pending: return
        
        batch = self._pending[:20]
        self._pending = self._pending[20:]
        
        self.setUpdatesEnabled(False)
        for row in batch:
            self._insert_one(row)
        self.setUpdatesEnabled(True)
        
        if not self._user_scrolled:
            self.scrollToBottom()

    def _insert_one(self, res: dict):
        row = self.rowCount()
        self.insertRow(row)
        
        token = res.get('token', '')
        user = res.get('username', '—')
        user_raw = res.get('username_raw', '')
        date = res.get('created_at', '—')
        email_v = res.get('has_email', False)
        phone_v = res.get('has_phone', False)
        nitro = res.get('nitro_type', 'None')
        age = res.get('account_age_days', 0)
        guilds = res.get('guild_count', -1)
        v_status = res.get('verification_status', '') # full_verified, email_verified, phone_verified, unclaimed
        status_lbl = res.get('status_label', '—')
        
        # 0: User
        u_item = QTableWidgetItem(user)
        u_item.setData(self._ROLE_SUB, user_raw)
        self.setItem(row, 0, u_item)
        
        # 1: Date
        d_item = QTableWidgetItem(date)
        d_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, 1, d_item)
        
        # 2: Verified
        v_item = QTableWidgetItem("")
        v_item.setData(self._ROLE_VER, f"{1 if email_v else 0}|{1 if phone_v else 0}")
        self.setItem(row, 2, v_item)
        
        # 3: Guilds
        g_text = str(guilds) if guilds >= 0 else '—'
        g_item = QTableWidgetItem(g_text)
        g_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if guilds >= 0: g_item.setForeground(QBrush(QColor(_ACCENT)))
        else: g_item.setForeground(QBrush(QColor(_GREY)))
        self.setItem(row, 3, g_item)
        
        # 4: Info
        info_str = ""
        if nitro != 'None' and nitro: info_str += f"Nitro: {nitro}  "
        if age > 0: info_str += f"Age: {age}d  "
        
        if status_lbl and status_lbl != '—':
            info_str += f"[{status_lbl}]"
            
        i_item = QTableWidgetItem(info_str or "...")
        i_item.setFont(self._info_font)
        i_item.setForeground(QBrush(QColor(_DIM)))
        self.setItem(row, 4, i_item)
        
        # 5: Token
        t_item = QTableWidgetItem(token)
        t_item.setFont(self._mono)
        t_item.setToolTip(token)
        self.setItem(row, 5, t_item)

    def clear_rows(self):
        self._pending.clear()
        self.setRowCount(0)

    def _context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: #1a1a24;
                color: {_TEXT};
                border: 1px solid {_BORDER};
                border-radius: 6px;
                padding: 4px;
                font-size: 12px;
            }}
            QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}
            QMenu::item:selected {{ background: #2a2a3e; }}
            QMenu::separator {{ background: {_BORDER}; height: 1px; margin: 4px 10px; }}
        """)
        
        sel = self.selectedIndexes()
        if sel:
            menu.addAction("Copy Token", self._copy_tokens)
            menu.addAction("Copy Full Line(s)", self._copy_full_lines)
            menu.addSeparator()
            
        menu.addAction("Select All  (Ctrl+A)", self.selectAll)
        menu.addAction("Clear Table", self.clear_rows)
        menu.exec(self.viewport().mapToGlobal(pos))

    def _copy_tokens(self):
        rows = sorted(list(set(i.row() for i in self.selectedIndexes())))
        tokens = [self.item(r, 5).text() for r in rows if self.item(r, 5)]
        QApplication.clipboard().setText("\n".join(tokens))

    def _copy_full_lines(self):
        rows = sorted(list(set(i.row() for i in self.selectedIndexes())))
        lines = []
        for r in rows:
            parts = []
            for c in range(self.columnCount()):
                item = self.item(r, c)
                if item: parts.append(item.text())
            lines.append(" | ".join(parts))
        QApplication.clipboard().setText("\n".join(lines))

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.SelectAll):
            self.selectAll()
        elif event.matches(QKeySequence.StandardKey.Copy):
            self._copy_tokens()
        else:
            super().keyPressEvent(event)

class CheckerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = Checker()
        self._worker = None
        self._stats = {'valid': 0, 'invalid': 0, 'locked': 0, 'nitro': 0, 'errors': 0}
        self._total_loaded = 0
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
            "TOKEN CHECKER",
            "Validate tokens → check Nitro status & account creation date"
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
        stats_f.setStyleSheet(f"QFrame {{ background: {COLORS['bg_input']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 12px; }}")
        stats_f.setGraphicsEffect(shadow(blur=10, alpha=70, dy=2))
        stats_lay = QHBoxLayout(stats_f)
        stats_lay.setContentsMargins(16, 9, 16, 9)
        
        self._valid_lbl, self._set_valid = stat_chip("VALID", COLORS['success'])
        self._invalid_lbl, self._set_invalid = stat_chip("INVALID", COLORS['error'])
        self._locked_lbl, self._set_locked = stat_chip("LOCKED", COLORS['warning'])
        self._nitro_lbl, self._set_nitro = stat_chip("NITRO", COLORS['tertiary'])
        self._errors_lbl, self._set_errors = stat_chip("ERRORS", COLORS['secondary'])
        
        stats_lay.addWidget(self._valid_lbl); stats_lay.addSpacing(20)
        stats_lay.addWidget(self._invalid_lbl); stats_lay.addSpacing(20)
        stats_lay.addWidget(self._locked_lbl); stats_lay.addSpacing(20)
        stats_lay.addWidget(self._nitro_lbl); stats_lay.addSpacing(20)
        stats_lay.addWidget(self._errors_lbl)
        stats_lay.addStretch()
        self.main_layout.addWidget(stats_f)

        # Progress
        self._progress = ProgressWidget()
        self.main_layout.addWidget(self._progress)

        # Output View (Terminal / Table)
        output_frame = QFrame()
        output_frame.setMinimumHeight(440)
        output_frame.setStyleSheet(f"background: {COLORS['bg_card']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 14px;")
        output_frame.setGraphicsEffect(shadow(blur=18, alpha=80, dy=4))
        
        out_lay = QVBoxLayout(output_frame)
        out_lay.setContentsMargins(0, 0, 0, 0)
        out_lay.setSpacing(0)
        
        # Toggle Bar
        toggle_bar = QFrame()
        toggle_bar.setFixedHeight(38)
        toggle_bar.setStyleSheet(f"background: {COLORS['bg_void']}; border-bottom: 1px solid {COLORS['border_subtle']}; border-top-left-radius: 14px; border-top-right-radius: 14px;")
        tb_lay = QHBoxLayout(toggle_bar)
        tb_lay.setContentsMargins(16, 0, 12, 0)
        
        self._count_lbl = QLabel("0")
        self._count_lbl.setStyleSheet(f"color: {COLORS['primary']}; font-size: 11px; font-weight: 700; background: transparent;")
        self._total_lbl = QLabel("/ 0")
        self._total_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; background: transparent; padding-left: 5px;")
        
        tb_lay.addWidget(self._count_lbl)
        tb_lay.addWidget(self._total_lbl)
        tb_lay.addStretch()
        
        # Mode buttons
        self._btn_terminal = self._make_toggle_btn("TERMINAL")
        self._btn_table = self._make_toggle_btn("TABLE")
        self._btn_table.setChecked(True)
        
        self._btn_terminal.clicked.connect(lambda: self._switch_view(0))
        self._btn_table.clicked.connect(lambda: self._switch_view(1))
        
        tb_lay.addWidget(self._btn_terminal)
        tb_lay.addWidget(self._btn_table)
        out_lay.addWidget(toggle_bar)
        
        self._stack = QStackedWidget()
        self._console = ConsoleWidget()
        self._console.setStyleSheet("border: none; border-bottom-left-radius: 14px; border-bottom-right-radius: 14px;")
        self._table = CheckerTable()
        
        self._stack.addWidget(self._console)
        self._stack.addWidget(self._table)
        self._stack.setCurrentIndex(1)
        
        out_lay.addWidget(self._stack)
        self.main_layout.addWidget(output_frame)

        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # UI refresh timer for stats
        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(32) # ~30fps
        self._stats_timer.timeout.connect(self._update_stats_ui)

    def _make_toggle_btn(self, text):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(26)
        btn.setMinimumWidth(80)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_muted']};
                border: none;
                font-size: 10px; font-weight: 700;
                letter-spacing: 1px;
                padding: 0 14px;
            }}
            QPushButton:checked {{
                background: {COLORS['primary']};
                color: #000;
                border-radius: 4px;
            }}
            QPushButton:hover:!checked {{ color: {COLORS['text_primary']}; }}
        """)
        return btn

    def _switch_view(self, idx):
        self._stack.setCurrentIndex(idx)
        self._btn_terminal.setChecked(idx == 0)
        self._btn_table.setChecked(idx == 1)

    def _clean_output(self):
        reply = QMessageBox.question(
            self, "Clean Output", "Delete all checker output files in output/checker/?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._tool.reset()
            self._console.log_info("Output files cleaned")
            SoundManager.instance().click()

    def _start(self):
        tokens = self._token_input.tokens
        if not tokens:
            self._console.log_warning("No tokens loaded.")
            return

        cfg = Config.instance()
        save_output = cfg.get('save_output', True)
        
        if save_output:
            reply = QMessageBox.question(self, "Clean Output?", "Clean previous output files before starting?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._tool.reset()
                self._console.log_info("Previous output cleaned")

        # Reset state
        self._total_loaded = len(tokens)
        self._stats = {'valid': 0, 'invalid': 0, 'locked': 0, 'nitro': 0, 'errors': 0}
        self._update_stats_ui()
        self._count_lbl.setText("0")
        self._total_lbl.setText(f"/ {self._total_loaded}")
        
        self._progress.reset(self._total_loaded)
        self._console.clear()
        self._table.clear_rows()
        
        proxy_rotator = None
        if cfg.get('use_proxies', False):
            proxies = self._proxy_input.proxies
            if proxies:
                proxy_rotator = ProxyRotator(proxies)

        self._console.log_info(f"Starting checker → {self._total_loaded} tokens → {self._settings.thread_count} threads" + (" → Output saving DISABLED" if not save_output else ""))
        if save_output: self._console.log_info("Results saving in real-time to output/checker/")

        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._clean_btn.setEnabled(False)
        self._stats_timer.start()

        # Start Worker
        self._worker = ToolWorker(
            task_func=self._tool.process_token,
            items=tokens,
            thread_count=self._settings.thread_count,
            proxy_rotator=proxy_rotator,
            save_output=save_output
        )
        
        self._worker.token_result.connect(self._on_token_result)
        self._worker.progress.connect(self._progress.update_progress)
        self._worker.log_message.connect(self._console.append_log)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.error_signal.connect(self._on_error)

        self._progress.set_status("Checking tokens...")
        self._worker.start()
        
        ServerManager.instance().log_activity('checker_start', {
            'token_count': self._total_loaded,
            'threads': self._settings.thread_count
        })

    def _stop(self):
        if self._worker:
            self._worker.cancel()
            self._console.log_warning("Stopping...")
            self._stop_btn.setEnabled(False)

    @pyqtSlot(str, dict)
    def _on_token_result(self, token: str, result: dict):
        status = result.get('status', 'error')
        msg = result.get('message', '')
        
        if status == 'valid':
            self._stats['valid'] += 1
            if result.get('has_nitro'):
                self._stats['nitro'] += 1
            self._console.log_plain(msg)
            self._table.add_row(result)
        elif status == 'invalid':
            self._stats['invalid'] += 1
            self._console.log_error(msg)
        elif status in ('locked_phone', 'locked_mail'):
            self._stats['locked'] += 1
            self._console.log_plain(msg)
            # Update result for table display
            result['verification_status'] = 'locked'
            result['status_label'] = 'Locked'
            self._table.add_row(result)
        elif status == 'rate_limited':
            self._stats['errors'] += 1
            self._console.log_error(msg)
        else:
            self._stats['errors'] += 1
            self._console.log_error(msg)

    def _update_stats_ui(self):
        """Called at 30fps to flush stat totals to screen without locking UI thread."""
        self._set_valid(str(self._stats['valid']))
        self._set_invalid(str(self._stats['invalid']))
        self._set_locked(str(self._stats['locked']))
        self._set_nitro(str(self._stats['nitro']))
        self._set_errors(str(self._stats['errors']))
        
        processed = self._stats['valid'] + self._stats['invalid'] + self._stats['locked'] + self._stats['errors']
        self._count_lbl.setText(str(processed))

    @pyqtSlot(dict)
    def _on_finished(self, results: dict):
        self._stats_timer.stop()
        self._update_stats_ui()
        
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._progress.set_complete()
        
        total = results.get('total', 0)
        errs = self._stats['errors']
        self._console.log_info(f"Done → {total} tokens → {self._stats['valid']} valid → {self._stats['invalid']} invalid → {self._stats['locked']} locked → {self._stats['nitro']} nitro" + (f" → {errs} errors" if errs else ""))
        
        SoundManager.instance().success()
        ServerManager.instance().log_activity('checker_complete', self._stats)

    @pyqtSlot(str)
    def _on_error(self, error_msg: str):
        self._stats_timer.stop()
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._clean_btn.setEnabled(True)
        self._progress.set_error(error_msg)
        self._console.log_error(error_msg)
        SoundManager.instance().error()


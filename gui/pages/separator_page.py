from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox, QScrollArea, QComboBox
from PyQt6.QtCore import Qt, pyqtSlot

from gui.theme import COLORS
from gui.pages.page_helpers import glass_frame, page_header, stat_chip, shadow, sub_card, section_label
from gui.widgets.token_input import TokenInput
from gui.widgets.console_widget import ConsoleWidget
from gui.widgets.animated_button import AnimatedButton
from core.sound_manager import SoundManager
from core.server_manager import ServerManager
from tools.separator.separator import Separator

class SeparatorPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = Separator()
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
            "TOKEN SEPARATOR",
            "Remove duplicated/intersecting tokens between definitions"
        ))

        # Mode Selection
        mode_card, mode_lay = glass_frame(18)
        mode_lay.setContentsMargins(24, 22, 24, 22)
        
        mode_frame, mode_lay_inner = sub_card()
        mode_lay_inner.setContentsMargins(16, 12, 16, 12)
        mode_lay_inner.setSpacing(8)
        
        mode_lay_inner.addWidget(section_label("SEPARATION MODE"))
        
        self._mode_combo = QComboBox()
        self._mode_combo.setFixedHeight(38)
        self._mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
                padding-left: 14px;
                font-size: 13px; font-weight: 600;
            }}
            QComboBox::drop-down {{
                border: none; width: 34px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_card_alt']};
                selection-background-color: {COLORS['primary']};
                selection-color: #000;
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 4px; outline: none;
            }}
        """)
        self._mode_combo.addItem("Remove Tokens 1 from Tokens 2", "1_from_2")
        self._mode_combo.addItem("Remove Tokens 2 from Tokens 1", "2_from_1")
        mode_lay_inner.addWidget(self._mode_combo)
        
        mode_lay.addWidget(mode_frame)
        self.main_layout.addWidget(mode_card)

        # Dual Token Inputs
        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(16)
        
        t1_layout = QVBoxLayout()
        t1_label = section_label("TOKENS 1")
        self._token_input_1 = TokenInput()
        t1_layout.addWidget(t1_label)
        t1_layout.addWidget(self._token_input_1)
        inputs_row.addLayout(t1_layout, stretch=1)
        
        t2_layout = QVBoxLayout()
        t2_label = section_label("TOKENS 2")
        self._token_input_2 = TokenInput()
        t2_layout.addWidget(t2_label)
        t2_layout.addWidget(self._token_input_2)
        inputs_row.addLayout(t2_layout, stretch=1)
        
        self.main_layout.addLayout(inputs_row)

        # Actions
        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        
        self._start_btn = AnimatedButton("START SEPARATING", True)
        self._start_btn.set_theme("danger")
        self._start_btn.setFixedHeight(44)
        self._start_btn.setMinimumWidth(180)
        self._start_btn.clicked.connect(self._start)
        
        self._clean_btn = AnimatedButton("CLEAN OUTPUT")
        self._clean_btn.setFixedHeight(44)
        self._clean_btn.clicked.connect(self._clean_output)
        
        action_row.addWidget(self._start_btn)
        action_row.addStretch()
        action_row.addWidget(self._clean_btn)
        
        self.main_layout.addLayout(action_row)

        # Stats
        stats_f = QFrame()
        stats_f.setStyleSheet(f"QFrame{{background:{COLORS['bg_input']};border:1px solid {COLORS['border_subtle']};border-radius:12px;}}")
        stats_f.setGraphicsEffect(shadow(blur=10, alpha=70, dy=2))
        sl = QHBoxLayout(stats_f)
        sl.setContentsMargins(16, 9, 16, 9)
        
        self._original_lbl, self._set_original = stat_chip("ORIGINAL", COLORS['text_secondary'])
        self._removed_lbl, self._set_removed = stat_chip("REMOVED", COLORS['error'])
        self._separated_lbl, self._set_separated = stat_chip("SEPARATED", COLORS['success'])
        
        sl.addWidget(self._original_lbl)
        sl.addSpacing(20)
        sl.addWidget(self._removed_lbl)
        sl.addSpacing(20)
        sl.addWidget(self._separated_lbl)
        sl.addStretch()
        
        self.main_layout.addWidget(stats_f)

        # Console
        self._console = ConsoleWidget()
        self.main_layout.addWidget(self._console)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _clean_output(self):
        reply = QMessageBox.question(
            self, "Clean Output", "Delete all separator output files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._tool.clear_output()
            self._console.log_info("Output files cleaned")
            SoundManager.instance().click()

    def _start(self):
        tokens_1 = self._token_input_1.tokens
        tokens_2 = self._token_input_2.tokens
        
        if not tokens_1 or not tokens_2:
            self._console.log_warning("Both Tokens 1 and Tokens 2 must be loaded.")
            return

        mode = self._mode_combo.currentData()
        self._console.log_info(f"Starting separation logic: {self._mode_combo.currentText()}")
        
        try:
            res = self._tool.separate_tokens(tokens_1, tokens_2, mode)
            
            self._set_original(str(res['original_count']))
            self._set_removed(str(res['removed_count']))
            self._set_separated(str(res['separated_count']))
            
            self._console.log_success(f"Separation complete: {res['separated_count']} tokens extracted.")
            self._console.log_info("Results saved to: output/separator/separated_tokens.txt")
            
            SoundManager.instance().success()
            ServerManager.instance().log_activity("separator_run", {
                "tokens_1": len(tokens_1),
                "tokens_2": len(tokens_2),
                "mode": mode,
                "separated": res['separated_count'],
                "removed": res['removed_count']
            })
            
        except Exception as e:
            self._console.log_error(f"Failed to separate tokens: {str(e)}")
            SoundManager.instance().error()

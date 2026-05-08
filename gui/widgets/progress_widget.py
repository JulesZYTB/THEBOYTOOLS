from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel
from PyQt6.QtCore import pyqtSlot
from gui.theme import COLORS

class ProgressWidget(QWidget):
    """
    ProgressWidget — Animated progress bar with status, count, and percentage labels.
    White gradient fill, slim modern design, monochrome.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_max = 100
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Labels Row
        labels = QHBoxLayout()
        labels.setSpacing(12)
        
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 600; background: transparent;")
        labels.addWidget(self._status_label)
        
        labels.addStretch()
        
        self._duplicates_label = QLabel("")
        self._duplicates_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 11px; font-weight: 700; background: transparent;")
        self._duplicates_label.hide()
        labels.addWidget(self._duplicates_label)
        
        self._count_label = QLabel("0 / 0")
        self._count_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; background: transparent;")
        labels.addWidget(self._count_label)
        
        self._percent_label = QLabel("0%")
        self._percent_label.setFixedWidth(42)
        self._percent_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px; font-weight: 800; background: transparent;")
        labels.addWidget(self._percent_label)
        
        layout.addLayout(labels)
        
        # Progress Bar
        self._bar = QProgressBar()
        self._bar.setMinimum(0)
        self._bar.setMaximum(100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background: {COLORS['bg_input']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ffffff,
                    stop:1 #666666
                );
            }}
        """)
        layout.addWidget(self._bar)

    @pyqtSlot(int, int)
    @pyqtSlot(int, int, int)
    def update_progress(self, current: int, total: int, duplicates: int = 0):
        if total <= 0:
            return
            
        if total != self._current_max:
            self._current_max = total
            self._bar.setMaximum(total)
            
        self._bar.setValue(current)
        pct = int((current / total) * 100) if total > 0 else 0
        
        self._count_label.setText(f"{current} / {total}")
        self._percent_label.setText(f"{pct}%")
        
        if duplicates > 0:
            self._duplicates_label.setText(f"({duplicates} Skipped)")
            self._duplicates_label.show()
        else:
            self._duplicates_label.hide()

    def set_status(self, text: str):
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 600; background: transparent;")

    def reset(self, total: int = 0):
        self._current_max = total if total > 0 else 100
        self._bar.setMaximum(self._current_max)
        self._bar.setValue(0)
        self._count_label.setText(f"0 / {total}" if total > 0 else "0 / 0")
        self._percent_label.setText("0%")
        self._duplicates_label.hide()
        self.set_status("Ready")

    def set_complete(self):
        self._status_label.setText("Complete")
        self._status_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; font-weight: 700; background: transparent;")

    def set_stopped(self):
        self._status_label.setText("Stopped")
        self._status_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 11px; font-weight: 700; background: transparent;")

    def set_error(self, message: str):
        self._status_label.setText(f"Error — {message}")
        self._status_label.setStyleSheet(f"color: {COLORS['error']}; font-size: 11px; font-weight: 700; background: transparent;")

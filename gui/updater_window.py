import os
import sys
import subprocess
import requests
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, 
    QProgressBar, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from gui.theme import COLORS

class DownloadThread(QThread):
    """Handles the actual file download in a background thread."""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, download_url: str, dest_path: str):
        super().__init__()
        self.download_url = download_url
        self.dest_path = dest_path

    def run(self):
        try:
            self.status_updated.emit("Connecting to server...")
            response = requests.get(self.download_url, stream=True, timeout=10)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            self.status_updated.emit("Downloading update...")
            
            with open(self.dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percentage = int((downloaded / total_size) * 100)
                            self.progress_updated.emit(percentage)
                            self.status_updated.emit(f"Downloading... {percentage}%")
            
            self.status_updated.emit("Download complete. Installing...")
            self.finished.emit(True, "Success")
            
        except requests.RequestException as e:
            self.finished.emit(False, f"Network error during download: {str(e)}")
        except IOError as e:
            self.finished.emit(False, f"File write error: {str(e)}")
        except Exception as e:
            self.finished.emit(False, f"Unexpected error: {str(e)}")

class UpdaterWindow(QMainWindow):
    """
    UpdaterWindow — Mandatory Update Screen.
    Simple, focused window that downloads and installs the latest version.
    """
    def __init__(self, download_url: str):
        super().__init__()
        self.download_url = download_url
        self.dest_path = "update_new.exe"
        
        self.setWindowTitle("THEBOY TOOLS - Mandatory Update")
        self.setFixedSize(450, 200)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        self._setup_ui()
        self._start_download()

    def _setup_ui(self):
        central = QWidget()
        central.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_darkest']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
            }}
        """)
        self.setCentralWidget(central)
        
        lay = QVBoxLayout(central)
        lay.setContentsMargins(30, 30, 30, 30)
        lay.setSpacing(15)
        
        title = QLabel("Software Update Required")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 18px; font-weight: bold;
            border: none; background: transparent;
        """)
        lay.addWidget(title)
        
        lay.addStretch()
        
        self.status_label = QLabel("Initializing download...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 13px;
            border: none; background: transparent;
        """)
        lay.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_card']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['success']};
                border-radius: 3px;
            }}
        """)
        lay.addWidget(self.progress_bar)

    def _start_download(self):
        self.thread = DownloadThread(self.download_url, self.dest_path)
        self.thread.progress_updated.connect(self.progress_bar.setValue)
        self.thread.status_updated.connect(self.status_label.setText)
        self.thread.finished.connect(self._on_download_finished)
        self.thread.start()

    def _on_download_finished(self, success: bool, message: str):
        if not success:
            QMessageBox.critical(self, "Update Failed", f"Failed to download the update:\n{message}\n\nPlease check your connection and restart the app.")
            sys.exit(1)
        else:
            self._execute_file_swap()

    def _execute_file_swap(self):
        """Generates a batch script to swap the executable and exits python immediately."""
        is_frozen = getattr(sys, 'frozen', False)
        current_exe = sys.executable if is_frozen else sys.argv[0]
        
        # Batch script content
        # 1. Wait a bit for this process to exit
        # 2. Delete the old exe
        # 3. Rename the new one to the old name
        # 4. Start the new one
        # 5. Delete self (the bat file)
        
        exe_name = os.path.basename(current_exe)
        if not exe_name.endswith(".exe"):
            exe_name = "THEBOY_TOOLS.exe"

        bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
del /f /q "{current_exe}"
ren "update_new.exe" "{exe_name}"
start "" "{exe_name}"
del "%~f0"
"""
        bat_path = "updater.bat"
        try:
            with open(bat_path, "w") as f:
                f.write(bat_content)
            
            # Use Popen to launch it detached
            subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
            QApplication.quit()
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Failed to create updater script:\n{str(e)}")
            sys.exit(1)

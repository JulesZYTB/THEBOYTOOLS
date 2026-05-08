import sys
import os
import traceback
import ctypes
from PyQt6.QtWidgets import QApplication, QMessageBox, QInputDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

from core.server_manager import ServerManager, APP_VERSION
from gui.main_window import MainWindow, _get_asset_root
from gui.updater_window import UpdaterWindow
from core.discord_rpc import DiscordRPCManager
from core.protection import initialize_protection
from gui.theme import get_stylesheet
from core.config import Config
from core.logger import AppLogger

def _show_error(title, msg):
    """Show a blocking error dialog and quit."""
    app = QApplication.instance() or QApplication(sys.argv)
    dlg = QMessageBox()
    dlg.setWindowTitle(title)
    dlg.setText(msg)
    dlg.setIcon(QMessageBox.Icon.Critical)
    dlg.setStyleSheet("""
        QMessageBox { background: #111; }
        QLabel { color: #fff; font-size: 13px; }
        QPushButton { background: #333; color: #fff; border: none; padding: 8px 24px; border-radius: 8px; font-weight: 700; }
        QPushButton:hover { background: #444; }
    """)
    dlg.exec()
    sys.exit(1)

def _show_update(latest, download_url):
    """Show a non-blocking update notification."""
    # Note: In the NBC, it seems to use a dialog or a window.
    # We'll use the UpdaterWindow for mandatory updates.
    pass

def main():
    # 1. Initialize Protection (Anti-Debug, Anti-VM, etc.)
    initialize_protection()

    # 2. Setup Application
    # Enable software OpenGL if needed for stability
    os.environ["QT_OPENGL"] = "software"
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("THEBOY TOOLS")
    app.setOrganizationName("theboy")
    
    # Global Font
    app.setFont(QFont("Segoe UI", 10))
    
    # Global Style
    app.setStyleSheet(get_stylesheet())
    
    # Asset Root & Icon
    asset_root = _get_asset_root()
    icon_path = os.path.join(asset_root, 'assets', 'icon.ico')
    
    # Windows Taskbar Icon Fix
    try:
        myappid = 'theboy.theboytools.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass
        
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 3. Server Check & Auth
    server = ServerManager.instance()
    status = server.check_app_status()
    
    if not status.get('allowed', True):
        _show_error("Application Disabled", status.get('message', 'Disabled by admin'))
        
    if status.get('update_available', False):
        download_url = status.get('download_url', '')
        if download_url:
            updater = UpdaterWindow(download_url)
            updater.show()
            return app.exec()
        else:
            # Fallback if no URL but update required
            _show_error("Update Available", "An update is available but no download URL was provided by the server.")

    # 4. User Registration (HWID)
    if status.get('needs_username', False):
        username, ok = QInputDialog.getText(None, "THEBOY TOOLS", "Welcome! Please enter your username to register this device:")
        if ok and username.strip():
            result = server.register_user(username.strip())
            if not result.get('valid', False):
                _show_error("Registration Failed", result.get('message', 'An error occurred.'))
        else:
            _show_error("Access Denied", "Hardware ID blocked or server error")

    # 5. Load Feature Flags & Start Services
    server.get_feature_flags()
    
    rpc = DiscordRPCManager.instance()
    rpc.start()

    # 6. Ensure Directories
    _exe_root = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
    os.makedirs(os.path.join(_exe_root, 'humanizer_pfps'), exist_ok=True)
    os.makedirs(os.path.join(_exe_root, 'output'), exist_ok=True)

    # 7. Launch Main Window
    window = MainWindow()
    window.show()
    
    AppLogger.instance().info("THEBOY TOOLS started successfully")
    
    exit_code = app.exec()
    
    # Cleanup
    rpc.stop()
    sys.exit(exit_code)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Global Crash Handler
        traceback.print_exc()
        crash_tb = traceback.format_exc()
        
        _root = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        crash_path = os.path.join(_root, 'crash.log')
        
        try:
            with open(crash_path, 'w', encoding='utf-8') as f:
                f.write(crash_tb)
        except:
            pass
            
        # Stylized Crash Dialog
        _app = QApplication.instance() or QApplication(sys.argv)
        dlg = QMessageBox()
        dlg.setWindowTitle("THEBOY TOOLS — Crash Report")
        dlg.setText("The application encountered an unexpected error and needs to close.")
        dlg.setInformativeText(f"A crash log has been saved to:\n{crash_path}\n\nPlease send this file to support.")
        dlg.setDetailedText(crash_tb)
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.setStyleSheet("""
                QMessageBox { background: #111; }
                QLabel { color: #fff; font-size: 13px; }
                QPushButton {
                    background: #333; color: #fff; border: none;
                    padding: 8px 24px; border-radius: 8px; font-weight: 700;
                }
                QPushButton:hover { background: #444; }
                QTextEdit { background: #1a1a1a; color: #e74c3c; font-family: Consolas; font-size: 11px; border: 1px solid #333; }
            """)
        dlg.exec()
        sys.exit(1)

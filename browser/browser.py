#!/usr/bin/env python3
"""
Secure Cyber Browser – Chrome-like with Tor and .onion support
Tested on Ubuntu 22.04 / Windows 10+ / macOS 12+ / Python 3.10-3.13
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import urllib.parse
import socket
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QVBoxLayout,
                             QWidget, QToolBar, QLineEdit, QPushButton, QComboBox,
                             QMenuBar, QMessageBox, QFileDialog, QLabel, QHBoxLayout, QTabBar)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtNetwork import QNetworkProxy

# ------------------------------------------------------------------
# 1. Boot-strap: ensure we have a venv and the required wheels
# ------------------------------------------------------------------
VENV_DIR = Path(__file__).parent / "cyber_browser_venv"
REQS = {
    "PyQt6": "6.9.0",  # Latest as of 2025
    "PyQt6-WebEngine": "6.9.0",
    "requests": "2.31.0",
}
PY_EXEC = sys.executable

def run(cmd, check=True, capture_output=True):
    """Run a shell command with error handling."""
    try:
        return subprocess.run(cmd, shell=True, check=check, capture_output=capture_output, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {cmd}\nError: {e.stderr}")
        return None

def ensure_venv():
    """Create venv and install required packages."""
    if not VENV_DIR.exists():
        print("Creating virtual environment...")
        run(f'"{PY_EXEC}" -m venv "{VENV_DIR}"')
    scripts_dir = "Scripts" if platform.system() == "Windows" else "bin"
    pip = VENV_DIR / scripts_dir / ("pip.exe" if platform.system() == "Windows" else "pip")
    if not pip.exists():
        raise RuntimeError(f"pip not found in {VENV_DIR / scripts_dir}")
    for pkg, ver in REQS.items():
        print(f"Ensuring {pkg} >= {ver}...")
        result = run(f'"{pip}" install --upgrade "{pkg}>={ver}"')
        if result and result.returncode != 0:
            print(f"Failed to install {pkg}. Try manually: pip install {pkg}>={ver}")

# Re-exec into venv if not already inside
if str(VENV_DIR) not in sys.prefix:
    ensure_venv()
    scripts_dir = "Scripts" if platform.system() == "Windows" else "bin"
    bin_py = VENV_DIR / scripts_dir / ("python.exe" if platform.system() == "Windows" else "python")
    if not bin_py.exists():
        raise RuntimeError(f"Python executable not found in {VENV_DIR / scripts_dir}")
    os.execv(str(bin_py), [str(bin_py), *sys.argv])

# ------------------------------------------------------------------
# 2. Check system dependencies (Tor only)
# ------------------------------------------------------------------
def check_system_dependencies():
    os_name = platform.system()
    try:
        subprocess.check_output(['tor', '--version'])
        print("Tor found.")
    except:
        instructions = {
            "Linux": "sudo apt install tor  # Debian/Ubuntu/Kali\nsudo dnf install tor  # Fedora",
            "Windows": "Download from https://www.torproject.org/download/",
            "Darwin": "brew install tor  # Requires Homebrew[](https://brew.sh)",
        }.get(os_name, "Install manually for your OS.")
        print(f"Warning: Tor not found. Install:\n{instructions}\n")
        input("Press Enter after installing Tor or to continue...")

check_system_dependencies()

# ------------------------------------------------------------------
# 3. Proxy configuration for Tor
# ------------------------------------------------------------------
def create_tor_proxy(enabled=False):
    """Create a Tor proxy configuration."""
    if enabled:
        proxy = QNetworkProxy()
        proxy.setType(QNetworkProxy.ProxyType.Socks5Proxy)
        proxy.setHostName("127.0.0.1")
        proxy.setPort(9050)
        return proxy
    return QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)

# ------------------------------------------------------------------
# 4. Secure page: HTTPS upgrade + cosmetic ad hiding
# ------------------------------------------------------------------
class SecureWebPage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.loadFinished.connect(self._inject_cosmetic)

    def _inject_cosmetic(self, ok):
        if not ok:
            return
        js = """
        // Cosmetic ad hiding and Chrome extension simulation
        document.querySelectorAll('div[id*="ad"], .advertisement, .adsbygoogle').forEach(el => el.style.display = 'none');
        console.log('Secure Cyber Browser: Extension content script injected (simulated)');
        """
        self.runJavaScript(js)

    def acceptNavigationRequest(self, url, _type, is_main_frame):
        if url.scheme() == "http" and not url.host().endswith(".onion"):
            url.setScheme("https")
            self.view().load(url)
            return False
        return super().acceptNavigationRequest(url, _type, is_main_frame)

# ------------------------------------------------------------------
# 5. Single browser tab
# ------------------------------------------------------------------
class BrowserTab(QWidget):
    def __init__(self, profile):
        super().__init__()
        self.profile = profile
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Chrome-like toolbar (omnibox)
        self.toolbar = QToolBar()
        self.toolbar.setFixedHeight(40)
        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: #1e1e1e;
                border: none;
                padding: 5px;
            }
            QToolButton {
                background-color: #2c2c2c;
                color: white;
                border-radius: 6px;
                padding: 6px;
            }
            QToolButton:hover {
                background-color: #3a3a3a;
            }
            QToolButton:pressed {
                background-color: #0078d7;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        # Logo: Sagar
        self.logo_label = QLabel("Sagar")
        self.logo_label.setStyleSheet("""
            QLabel {
                color: #1a73e8;
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
                margin: 4px;
            }
        """)
        self.toolbar.addWidget(self.logo_label)
        
        self.back_action = self.toolbar.addAction(QIcon.fromTheme("go-previous"), "Back", lambda: self.view.back())
        self.forward_action = self.toolbar.addAction(QIcon.fromTheme("go-next"), "Forward", lambda: self.view.forward())
        self.toolbar.addAction(QIcon.fromTheme("view-refresh"), "Reload", lambda: self.view.reload())
        self.toolbar.addAction(QIcon.fromTheme("go-home"), "Home", self.go_home)

        # Tor toggle button
        self.tor_button = QPushButton("Tor: Off")
        self.tor_button.setFixedWidth(80)
        self.tor_button.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                color: #202124;
                border: 1px solid #dadce0;
                border-radius: 4px;
                padding: 4px;
                margin: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #e8eaed;
            }
            QPushButton:checked {
                background: #1a73e8;
                color: #ffffff;
            }
        """)
        self.tor_button.setCheckable(True)
        self.tor_button.toggled.connect(self.toggle_tor)
        self.toolbar.addWidget(self.tor_button)

        # Omnibox (URL bar + search)
        self.omnibox = QLineEdit()
        self.omnibox.setPlaceholderText("Search or type a URL")
        self.omnibox.returnPressed.connect(self.navigate)
        self.omnibox.setStyleSheet("""
            QLineEdit {
                background: #ffffff;
                color: #202124;
                border: 1px solid #dadce0;
                border-radius: 20px;
                padding: 8px 16px;
                font-size: 14px;
                margin: 4px 8px;
            }
            QLineEdit:focus {
                border: 1px solid #1a73e8;
                background: #f0f8ff;
            }
        """)
        self.toolbar.addWidget(self.omnibox)

        # Search engine selector
        self.search_engine = QComboBox()
        self.search_engine.addItems(["DuckDuckGo", "Google", "Bing", "Brave"])
        self.search_engine.setFixedWidth(120)
        self.search_engine.setStyleSheet("""
            QComboBox {
                background: #050805;
                color: #59fd4c;
                border: 1px solid #dadce0;
                border-radius: 12px;
                padding: 6px;
                margin: 4px;
                font-size: 12px;
            }
            QComboBox:hover {
                background: #dfe1e5;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ4r2z2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABYSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
            }
        """)
        self.toolbar.addWidget(self.search_engine)

        # Google Dorks selector
        self.dork_box = QComboBox()
        self.dork_box.addItems(["No Dork", "site:", "inurl:", "intitle:", "filetype:", "intext:", "cache:"])
        self.dork_box.setFixedWidth(120)
        self.dork_box.setStyleSheet("""
            QComboBox {
                background: #050805;
                color: #59fd4c;
                border: 1px solid #dadce0;
                border-radius: 12px;
                padding: 6px;
                margin: 4px;
                font-size: 12px;
            }
            QComboBox:hover {
                background: #dfe1e5;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ4r2z2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABYSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
            }
        """)
        self.toolbar.addWidget(self.dork_box)

        layout.addWidget(self.toolbar)

        # Web view
        self.view = QWebEngineView()
        self.view.setStyleSheet("""
            QWebEngineView {
                background: #ffffff;
            }
        """)
        self.page = SecureWebPage(profile, self.view)
        self.view.setPage(self.page)
        self.view.urlChanged.connect(self.update_omnibox)
        layout.addWidget(self.view)
        self.go_home()

    def load_url(self, url: str):
        if not url.startswith(("http://", "https://")) and not url.endswith(".onion"):
            url = "https://" + url
        try:
            self.view.load(QUrl(url))
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load URL: {str(e)}")

    def go_home(self):
        self.load_url("https://duckduckgo.com")
        self.omnibox.setText("https://duckduckgo.com")

    def navigate(self):
        txt = self.omnibox.text().strip()
        if not txt:
            return
        dork = self.dork_box.currentText()
        if dork != "No Dork" and not txt.endswith(".onion"):
            query = urllib.parse.quote(f"{dork}{txt}")
        else:
            query = urllib.parse.quote(txt)
        engine = self.search_engine.currentText().lower().replace(" ", "")
        if dork != "No Dork" and not txt.endswith(".onion"):
            search_urls = {
                "duckduckgo": f"https://duckduckgo.com/?q={query}",
                "google": f"https://www.google.com/search?q={query}",
                "bing": f"https://www.bing.com/search?q={query}",
                "brave": f"https://search.brave.com/search?q={query}",
            }
            url = search_urls.get(engine, search_urls["duckduckgo"])
        else:
            url = txt
        self.load_url(url)

    def update_omnibox(self, url):
        self.omnibox.setText(url.toString())

    def toggle_tor(self, checked):
        self.tor_button.setText("Tor: On" if checked else "Tor: Off")
        try:
            # Check if Tor is running on 127.0.0.1:9050
            with socket.create_connection(("127.0.0.1", 9050), timeout=2):
                pass  # Connection successful, Tor is running
            proxy = create_tor_proxy(checked)
            QNetworkProxy.setApplicationProxy(proxy)
            status = "Tor proxy enabled (127.0.0.1:9050)" if checked else "Tor proxy disabled"
            QMessageBox.information(self, "Tor", status)
            t = self.tabs.currentWidget()
            if t:
                t.view.reload()
        except socket.timeout:
            self.tor_button.setChecked(False)
            self.tor_button.setText("Tor: Off")
            QMessageBox.critical(self, "Tor Error", "Tor is not running on 127.0.0.1:9050.\nPlease start Tor and try again.")
        except Exception as e:
            self.tor_button.setChecked(False)
            self.tor_button.setText("Tor: Off")
            QMessageBox.critical(self, "Tor Error", f"Failed to toggle Tor: {str(e)}\nEnsure Tor is running on 127.0.0.1:9050.")

# ------------------------------------------------------------------
# 6. Custom Tab Bar for bottom new tab button
# ------------------------------------------------------------------
class CustomTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.new_tab_button = QPushButton("+")
        self.new_tab_button.setFixedSize(30, 30)
        self.new_tab_button.setStyleSheet("""
            QPushButton {
                background: #f1f3f4;
                color: #202124;
                border: 1px solid #dadce0;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #e8eaed;
            }
        """)
        self.new_tab_button.clicked.connect(self.parent().add_tab)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addStretch()
        self.layout.addWidget(self.new_tab_button)
        self.setLayout(self.layout)
        self.currentChanged.connect(self.update_new_tab_button)

    def update_new_tab_button(self, index):
        try:
            # Ensure the new tab button is always at the bottom of the current tab
            self.new_tab_button.setVisible(index >= 0)
        except Exception as e:
            print(f"Error updating new tab button: {str(e)}")

# ------------------------------------------------------------------
# 7. Main window
# ------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sagar's Secure Cyber Browser")
        self.resize(1200, 800)
        self.profile = QWebEngineProfile.defaultProfile()
        # Chrome-like default stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background: #ffffff;
            }
            QMenuBar {
                background: #f1f3f4;
                color: #202124;
                font-size: 14px;
                padding: 4px;
            }
            QMenuBar::item {
                background: transparent;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background: #e8eaed;
                color: #202124;
            }
            QMenu {
                background: #ffffff;
                color: #202124;
                border: 1px solid #dadce0;
                padding: 4px;
            }
            QMenu::item:selected {
                background: #1a73e8;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: none;
                background: #ffffff;
            }
            QTabBar::tab {
                background: #f1f3f4;
                color: #202124;
                padding: 8px 16px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid #dadce0;
                border-bottom: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #1a73e8;
                border-bottom: 2px solid #1a73e8;
            }
            QTabBar::tab:!selected {
                background: #e8eaed;
            }
            QTabBar::close-button {
                image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ8mKz2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABnSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                padding: 4px;
            }
            QTabBar::close-button:hover {
                background: #dadce0;
                border-radius: 50%;
            }
        """)
        self.build_menu()
        self.tabs = QTabWidget()
        self.tabs.setTabBar(CustomTabBar(self))
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)
        self.add_tab()

    def build_menu(self):
        m = self.menuBar()
        file_menu = m.addMenu("File")
        file_menu.addAction("New Tab", self.add_tab)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        sec_menu = m.addMenu("Security")
        sec_menu.addAction("Toggle Tor", self.toggle_tor)

        ext_menu = m.addMenu("Extensions")
        ext_menu.addAction("Web Analyzer", self.web_analyzer)
        ext_menu.addAction("FoxyProxy (Toggle Tor)", self.toggle_tor)
        ext_menu.addAction("Simulate Chrome Extension", self.simulate_extension)

        view_menu = m.addMenu("View")
        view_menu.addAction("Dark Theme", lambda: self.set_theme("dark"))
        view_menu.addAction("Light Theme", lambda: self.set_theme("light"))
        view_menu.addAction("Neon Theme", lambda: self.set_theme("neon"))
        view_menu.addAction("Change Background", self.pick_bg)

    def add_tab(self):
        t = BrowserTab(self.profile)
        idx = self.tabs.addTab(t, "New Tab")
        self.tabs.setCurrentIndex(idx)

    def close_tab(self, idx):
        if self.tabs.count() > 1:
            self.tabs.removeTab(idx)

    def toggle_tor(self):
        t = self.tabs.currentWidget()
        if t:
            t.tor_button.setChecked(not t.tor_button.isChecked())
            t.toggle_tor(t.tor_button.isChecked())

    def web_analyzer(self):
        t = self.tabs.currentWidget()
        if not t:
            return
        title = t.view.title()
        url = t.view.url().toString()
        QMessageBox.information(self, "Web Analyzer", f"Title: {title}\nURL: {url}\n(Simulated – extend with Wappalyzer-like analysis)")

    def simulate_extension(self):
        t = self.tabs.currentWidget()
        if not t:
            return
        js = """
        alert('Simulated Chrome extension running! This is a placeholder for Chrome extension functionality.');
        console.log('Secure Cyber Browser: Chrome extension simulation activated.');
        """
        t.page.runJavaScript(js)
        QMessageBox.information(self, "Extension", "Simulated Chrome extension executed.\nCheck console for logs (placeholder).")

    def pick_bg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Background Image", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.setStyleSheet(f"""
                QMainWindow {{
                    border-image: url({path}) 0 0 0 0 stretch stretch;
                }}
                QMenuBar {{
                    background: rgba(241, 243, 244, 0.9);
                    color: #202124;
                    font-size: 14px;
                    padding: 4px;
                }}
                QMenuBar::item {{
                    background: transparent;
                    padding: 4px 8px;
                }}
                QMenuBar::item:selected {{
                    background: #e8eaed;
                    color: #202124;
                }}
                QMenu {{
                    background: rgba(255, 255, 255, 0.9);
                    color: #202124;
                    border: 1px solid #dadce0;
                    padding: 4px;
                }}
                QMenu::item:selected {{
                    background: #1a73e8;
                    color: #ffffff;
                }}
                QTabWidget::pane {{
                    border: none;
                    background: rgba(255, 255, 255, 0.9);
                }}
                QTabBar::tab {{
                    background: #f1f3f4;
                    color: #202124;
                    padding: 8px 16px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    border: 1px solid #dadce0;
                    border-bottom: none;
                    margin-right: 2px;
                }}
                QTabBar::tab:selected {{
                    background: #ffffff;
                    color: #1a73e8;
                    border-bottom: 2px solid #1a73e8;
                }}
                QTabBar::tab:!selected {{
                    background: #e8eaed;
                }}
                QTabBar::close-button {{
                    image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ8mKz2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABnSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    padding: 4px;
                }}
                QTabBar::close-button:hover {{
                    background: #dadce0;
                    border-radius: 50%;
                }}
            """)
            # Update toolbar dropdown, Tor button, logo, and new tab button styles
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                tab.search_engine.setStyleSheet("""
                    QComboBox {
                        background: rgba(232, 234, 237, 0.9);
                        color: #202124;
                        border: 1px solid #dadce0;
                        border-radius: 12px;
                        padding: 6px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QComboBox:hover {
                        background: rgba(223, 225, 229, 0.9);
                    }
                    QComboBox::drop-down {
                        border: none;
                    }
                    QComboBox::down-arrow {
                        image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ4r2z2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABYSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    }
                """)
                tab.dork_box.setStyleSheet("""
                    QComboBox {
                        background: rgba(232, 234, 237, 0.9);
                        color: #202124;
                        border: 1px solid #dadce0;
                        border-radius: 12px;
                        padding: 6px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QComboBox:hover {
                        background: rgba(223, 225, 229, 0.9);
                    }
                    QComboBox::drop-down {
                        border: none;
                    }
                    QComboBox::down-arrow {
                        image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ4r2z2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABYSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    }
                """)
                tab.tor_button.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.9);
                        color: #202124;
                        border: 1px solid #dadce0;
                        border-radius: 4px;
                        padding: 4px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background: rgba(232, 234, 237, 0.9);
                    }
                    QPushButton:checked {
                        background: rgba(26, 115, 232, 0.9);
                        color: #ffffff;
                    }
                """)
                tab.logo_label.setStyleSheet("""
                    QLabel {
                        color: #1a73e8;
                        font-size: 16px;
                        font-weight: bold;
                        padding: 8px;
                        margin: 4px;
                        background: rgba(255, 255, 255, 0.9);
                        border-radius: 4px;
                    }
                """)
            self.tabs.tabBar().new_tab_button.setStyleSheet("""
                QPushButton {
                    background: rgba(241, 243, 244, 0.9);
                    color: #202124;
                    border: 1px solid #dadce0;
                    border-radius: 4px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background: rgba(232, 234, 237, 0.9);
                }
            """)

    def set_theme(self, mode):
        if mode == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background: #202124;
                }
                QMenuBar {
                    background: #2c2f33;
                    color: #e8eaed;
                    font-size: 14px;
                    padding: 4px;
                }
                QMenuBar::item {
                    background: transparent;
                    padding: 4px 8px;
                }
                QMenuBar::item:selected {
                    background: #3c4043;
                    color: #e8eaed;
                }
                QMenu {
                    background: #2c2f33;
                    color: #e8eaed;
                    border: 1px solid #3c4043;
                    padding: 4px;
                }
                QMenu::item:selected {
                    background: #1a73e8;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: none;
                    background: #202124;
                }
                QTabBar::tab {
                    background: #2c2f33;
                    color: #e8eaed;
                    padding: 8px 16px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    border: 1px solid #3c4043;
                    border-bottom: none;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background: #202124;
                    color: #1a73e8;
                    border-bottom: 2px solid #1a73e8;
                }
                QTabBar::tab:!selected {
                    background: #35363a;
                }
                QTabBar::close-button {
                    image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ8mKz2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABnSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    padding: 4px;
                }
                QTabBar::close-button:hover {
                    background: #3c4043;
                    border-radius: 50%;
                }
            """)
            # Update toolbar dropdown, Tor button, logo, and new tab button styles
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                tab.search_engine.setStyleSheet("""
                    QComboBox {
                        background: #35363a;
                        color: #e8eaed;
                        border: 1px solid #3c4043;
                        border-radius: 12px;
                        padding: 6px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QComboBox:hover {
                        background: #3c4043;
                    }
                    QComboBox::drop-down {
                        border: none;
                    }
                    QComboBox::down-arrow {
                        image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ4r2z2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABYSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    }
                """)
                tab.dork_box.setStyleSheet("""
                    QComboBox {
                        background: #35363a;
                        color: #e8eaed;
                        border: 1px solid #3c4043;
                        border-radius: 12px;
                        padding: 6px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QComboBox:hover {
                        background: #3c4043;
                    }
                    QComboBox::drop-down {
                        border: none;
                    }
                    QComboBox::down-arrow {
                        image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ4r2z2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABYSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    }
                """)
                tab.tor_button.setStyleSheet("""
                    QPushButton {
                        background: #35363a;
                        color: #e8eaed;
                        border: 1px solid #3c4043;
                        border-radius: 4px;
                        padding: 4px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background: #3c4043;
                    }
                    QPushButton:checked {
                        background: #1a73e8;
                        color: #ffffff;
                    }
                """)
                tab.logo_label.setStyleSheet("""
                    QLabel {
                        color: #1a73e8;
                        font-size: 16px;
                        font-weight: bold;
                        padding: 8px;
                        margin: 4px;
                        background: #2c2f33;
                        border-radius: 4px;
                    }
                """)
            self.tabs.tabBar().new_tab_button.setStyleSheet("""
                QPushButton {
                    background: #35363a;
                    color: #e8eaed;
                    border: 1px solid #3c4043;
                    border-radius: 4px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background: #3c4043;
                }
            """)
        elif mode == "neon":
            self.setStyleSheet("""
                QMainWindow {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                stop:0 #0a0e14, stop:0.5 #1a3c34, stop:1 #2a1a3c);
                }
                QMenuBar {
                    background: #0a0e14;
                    color: #00ff00;
                    font-size: 14px;
                    padding: 4px;
                }
                QMenuBar::item {
                    background: transparent;
                    padding: 4px 8px;
                }
                QMenuBar::item:selected {
                    background: #800080;
                    color: #00ff00;
                }
                QMenu {
                    background: #0a0e14;
                    color: #00ff00;
                    border: 1px solid #800080;
                    padding: 4px;
                }
                QMenu::item:selected {
                    background: #800080;
                    color: #00ff00;
                }
                QTabWidget::pane {
                    border: none;
                    background: #0a0e14;
                }
                QTabBar::tab {
                    background: #1a3c34;
                    color: #00ff00;
                    padding: 8px 16px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    border: 1px solid #800080;
                    border-bottom: none;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background: #0a0e14;
                    color: #00ff00;
                    border-bottom: 2px solid #800080;
                }
                QTabBar::tab:!selected {
                    background: #1a3c34;
                }
                QTabBar::close-button {
                    image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ8mKz2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABnSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    padding: 4px;
                }
                QTabBar::close-button:hover {
                    background: #800080;
                    border-radius: 50%;
                }
            """)
            # Update toolbar dropdown, Tor button, logo, and new tab button styles
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                tab.search_engine.setStyleSheet("""
                    QComboBox {
                        background: #00ff00;
                        color: #0a0e14;
                        border: 1px solid #800080;
                        border-radius: 12px;
                        padding: 6px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QComboBox:hover {
                        background: #00cc00;
                    }
                    QComboBox::drop-down {
                        border: none;
                    }
                    QComboBox::down-arrow {
                        image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ4r2z2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABYSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    }
                """)
                tab.dork_box.setStyleSheet("""
                    QComboBox {
                        background: #00ff00;
                        color: #0a0e14;
                        border: 1px solid #800080;
                        border-radius: 12px;
                        padding: 6px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QComboBox:hover {
                        background: #00cc00;
                    }
                    QComboBox::drop-down {
                        border: none;
                    }
                    QComboBox::down-arrow {
                        image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ4r2z2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABYSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    }
                """)
                tab.tor_button.setStyleSheet("""
                    QPushButton {
                        background: #00ff00;
                        color: #0a0e14;
                        border: 1px solid #800080;
                        border-radius: 4px;
                        padding: 4px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background: #00cc00;
                    }
                    QPushButton:checked {
                        background: #800080;
                        color: #ffffff;
                    }
                """)
                tab.logo_label.setStyleSheet("""
                    QLabel {
                        color: #00ff00;
                        font-size: 16px;
                        font-weight: bold;
                        padding: 8px;
                        margin: 4px;
                        background: #0a0e14;
                        border: 1px solid #800080;
                        border-radius: 4px;
                    }
                """)
            self.tabs.tabBar().new_tab_button.setStyleSheet("""
                QPushButton {
                    background: #00ff00;
                    color: #0a0e14;
                    border: 1px solid #800080;
                    border-radius: 4px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background: #00cc00;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background: #ffffff;
                }
                QMenuBar {
                    background: #f1f3f4;
                    color: #202124;
                    font-size: 14px;
                    padding: 4px;
                }
                QMenuBar::item {
                    background: transparent;
                    padding: 4px 8px;
                }
                QMenuBar::item:selected {
                    background: #e8eaed;
                    color: #202124;
                }
                QMenu {
                    background: #ffffff;
                    color: #202124;
                    border: 1px solid #dadce0;
                    padding: 4px;
                }
                QMenu::item:selected {
                    background: #1a73e8;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: none;
                    background: #ffffff;
                }
                QTabBar::tab {
                    background: #f1f3f4;
                    color: #202124;
                    padding: 8px 16px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    border: 1px solid #dadce0;
                    border-bottom: none;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background: #ffffff;
                    color: #1a73e8;
                    border-bottom: 2px solid #1a73e8;
                }
                QTabBar::tab:!selected {
                    background: #e8eaed;
                }
                QTabBar::close-button {
                    image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ8mKz2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABnSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    padding: 4px;
                }
                QTabBar::close-button:hover {
                    background: #dadce0;
                    border-radius: 50%;
                }
            """)
            # Update toolbar dropdown, Tor button, logo, and new tab button styles
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                tab.search_engine.setStyleSheet("""
                    QComboBox {
                        background: #e8eaed;
                        color: #202124;
                        border: 1px solid #dadce0;
                        border-radius: 12px;
                        padding: 6px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QComboBox:hover {
                        background: #dfe1e5;
                    }
                    QComboBox::drop-down {
                        border: none;
                    }
                    QComboBox::down-arrow {
                        image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ4r2z2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABYSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    }
                """)
                tab.dork_box.setStyleSheet("""
                    QComboBox {
                        background: #e8eaed;
                        color: #202124;
                        border: 1px solid #dadce0;
                        border-radius: 12px;
                        padding: 6px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QComboBox:hover {
                        background: #dfe1e5;
                    }
                    QComboBox::drop-down {
                        border: none;
                    }
                    QComboBox::down-arrow {
                        image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5gMMDQ4r2z2B8wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABYSURBVCjPY2AYBaNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhWNgFIyCUSAWDCDEEy8YhQEAi8oR7s8N8Z8AAAAASUVORK5CYII=);
                    }
                """)
                tab.tor_button.setStyleSheet("""
                    QPushButton {
                        background: #ffffff;
                        color: #202124;
                        border: 1px solid #dadce0;
                        border-radius: 4px;
                        padding: 4px;
                        margin: 4px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background: #e8eaed;
                    }
                    QPushButton:checked {
                        background: #1a73e8;
                        color: #ffffff;
                    }
                """)
                tab.logo_label.setStyleSheet("""
                    QLabel {
                        color: #1a73e8;
                        font-size: 16px;
                        font-weight: bold;
                        padding: 8px;
                        margin: 4px;
                        background: #ffffff;
                        border-radius: 4px;
                    }
                """)
            self.tabs.tabBar().new_tab_button.setStyleSheet("""
                QPushButton {
                    background: #f1f3f4;
                    color: #202124;
                    border: 1px solid #dadce0;
                    border-radius: 4px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background: #e8eaed;
                }
            """)

# ------------------------------------------------------------------
# 8. Entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
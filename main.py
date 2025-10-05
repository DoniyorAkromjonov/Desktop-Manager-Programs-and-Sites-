from __future__ import annotations
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import webbrowser

# --- Qt imports: PyQt6 приоритетно, иначе PyQt5 ---
try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    PYQT6 = True
except Exception:
    from PyQt5 import QtCore, QtGui, QtWidgets 
    PYQT6 = False

APP_NAME = "Windows Launcher Profiles"
CONFIG_NAME = "profiles.json"
CONFIG_PATH = Path(__file__).with_name(CONFIG_NAME)
STARTUP_DIR = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"


def load_state() -> Dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"profiles": {}}


def save_state(data: Dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_autostart_enabled() -> bool:
    return (STARTUP_DIR / f"{APP_NAME}.lnk").exists() or (STARTUP_DIR / f"{APP_NAME}.bat").exists()


def enable_autostart() -> bool:
    try:
        STARTUP_DIR.mkdir(parents=True, exist_ok=True)
        lnk_path = STARTUP_DIR / f"{APP_NAME}.lnk"
        target = str(Path(sys.executable).with_name("pythonw.exe") if Path(sys.executable).name.lower()=="python.exe" else Path(sys.executable))
        script = str(Path(__file__).resolve())
        ps = rf"$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('{lnk_path}'); $s.TargetPath = '{target}'; $s.Arguments = '" + '"' + script + '"' + "'; $s.WorkingDirectory = '{Path(__file__).resolve().parent}'; $s.IconLocation='{target},0'; $s.Save()"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        try:
            bat_path = STARTUP_DIR / f"{APP_NAME}.bat"
            target = str(Path(sys.executable).with_name("pythonw.exe") if Path(sys.executable).name.lower()=="python.exe" else Path(sys.executable))
            script = str(Path(__file__).resolve())
            bat_path.write_text(f"start \"\" \"{target}\" \"{script}\"\n", encoding="utf-8")
            return bat_path.exists()
        except Exception:
            return False


def disable_autostart() -> bool:
    ok = True
    for p in [(STARTUP_DIR / f"{APP_NAME}.lnk"), (STARTUP_DIR / f"{APP_NAME}.bat")]:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            ok = False
    return ok


def _resolve_lnk(path: str) -> str:
    p = Path(path)
    if p.suffix.lower() != ".lnk" or not p.exists():
        return str(p)
    try:
        ps = rf"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{str(p)}'); Write-Output $s.TargetPath"
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps], text=True)
        return out.strip() or str(p)
    except Exception:
        return str(p)


def open_urls_with_browser(urls: List[str], browser_path: Optional[str]):
    urls = [u.strip() for u in urls if u and u.strip()]
    if not urls:
        return
    if browser_path:
        real = _resolve_lnk(browser_path)
        bp = Path(real)
        if bp.exists():
            try:
                subprocess.Popen([str(bp), *urls], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
                return
            except Exception:
                pass
    for u in urls:
        webbrowser.open_new_tab(u)


def launch_item(path: str):
    if not path:
        return
    p = Path(_resolve_lnk(path))
    if not p.exists():
        return
    try:
        if p.suffix.lower() == ".exe":
            subprocess.Popen([str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        else:
            os.startfile(str(p))  # type: ignore[attr-defined]
    except Exception:
        pass


def launch_profile(name: str, state: Dict):
    prof = state.get("profiles", {}).get(name, {})
    apps: List[str] = prof.get("apps", [])
    urls: List[str] = prof.get("urls", [])
    browser_path: Optional[str] = prof.get("browser_path")
    open_urls_with_browser(urls, browser_path)
    for a in apps:
        launch_item(a)


class Theme:
    def __init__(self, name: str, base: str, card: str, border: str, text: str, subtext: str,
                 primary: str, danger: str, success: str, shadow_rgba: str):
        self.name=name; self.base=base; self.card=card; self.border=border
        self.text=text; self.subtext=subtext
        self.primary=primary; self.danger=danger; self.success=success
        self.shadow=shadow_rgba

LIGHT = Theme(
    name="light",
    base="#FFFFFF", card="#F5F5F5", border="#E6E6E6", text="#202020", subtext="#555555",
    primary="#0078D7", danger="#E81123", success="#107C10", shadow_rgba="0,0,0,0.10"
)
DARK = Theme(
    name="dark",
    base="#1E1E1E", card="#2C2C2C", border="#3A3A3A", text="#E0E0E0", subtext="#A0A0A0",
    primary="#2F7DD7", danger="#E81123", success="#2EA043", shadow_rgba="0,0,0,0.35"
)

CARD_QSS = """
QFrame#Card {
    background: %(card)s;
    border: 1px solid %(border)s;
    border-radius: 12px;
}
QFrame#Card:hover { border-color: %(primary)s; }
QLabel#Title { color: %(text)s; font-size: 20px; font-weight: 600; }
QLabel#Meta { color: %(subtext)s; }
"""

BUTTONS_QSS = """
QPushButton { padding: 8px 14px; border-radius: 10px; border: 0px; font-weight: 600; }
QPushButton#Primary { background: %(primary)s; color: white; }
QPushButton#Primary:hover { filter: brightness(1.05); }
QPushButton#Danger { background: %(danger)s; color: white; }
QPushButton#Ghost { background: %(card)s; color: %(text)s; border: 1px solid %(border)s; }
QPushButton#Ghost:hover { border-color: %(primary)s; }
QCheckBox, QLabel { color: %(text)s; }
QStatusBar { color: %(text)s; background: %(base)s; }
QMainWindow, QWidget { background: %(base)s; }
QComboBox, QLineEdit, QListWidget { background: %(card)s; color: %(text)s; border: 1px solid %(border)s; border-radius: 8px; padding: 6px; }
QListWidget::item { padding: 6px; }
"""


class ProfileCard(QtWidgets.QFrame):
    clicked = QtCore.pyqtSignal(str)

    def __init__(self, name: str, programs: int, sites: int, browser: str, theme: Theme, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.name = name
        self.theme = theme
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))


        eff = QtWidgets.QGraphicsDropShadowEffect(self)
        eff.setBlurRadius(18)
        eff.setOffset(0, 6)
        eff.setColor(QtGui.QColor.fromString("rgba("+theme.shadow+")") if hasattr(QtGui.QColor, 'fromString') else QtGui.QColor(0,0,0,120))
        self.setGraphicsEffect(eff)


        icon = QtWidgets.QLabel("💼")
        title = QtWidgets.QLabel(name); title.setObjectName("Title")
        meta = QtWidgets.QLabel(f"{programs} Programs · {sites} Websites    {browser}"); meta.setObjectName("Meta")

        grid = QtWidgets.QGridLayout(self); grid.setContentsMargins(16,14,16,14); grid.setVerticalSpacing(6)
        grid.addWidget(icon, 0, 0)
        grid.addWidget(title, 0, 1)
        grid.addWidget(meta, 1, 1, 1, 2)

    def mousePressEvent(self, e):
        if e.button() == (QtCore.Qt.MouseButton.LeftButton if PYQT6 else QtCore.Qt.LeftButton):
            self.clicked.emit(self.name)
        super().mousePressEvent(e)


class ProfileEditor(QtWidgets.QDialog):
    def __init__(self, parent=None, name: Optional[str]=None, state: Optional[Dict]=None, theme: Theme=LIGHT):
        super().__init__(parent)
        self.setWindowTitle("Профиль")
        self.resize(760, 560)
        self.state = state or {"profiles": {}}
        self.theme = theme
        self.initial_name = name if (name and name in self.state.get("profiles", {})) else None
        if self.initial_name:
            prof = self.state["profiles"][self.initial_name]
            apps = prof.get("apps", [])
            urls = prof.get("urls", [])
            browser_path = prof.get("browser_path", "")
        else:
            apps, urls, browser_path = [], [], ""

        self.name_edit = QtWidgets.QLineEdit(self.initial_name or "")
        self.browser_edit = QtWidgets.QLineEdit(browser_path)
        self.browser_btn = QtWidgets.QPushButton("Обзор…")
        self.browser_btn.clicked.connect(self.pick_browser)

        self.apps_list = QtWidgets.QListWidget(); self.apps_list.addItems(apps)
        self.apps_add_btn = QtWidgets.QPushButton("Добавить…")
        self.apps_del_btn = QtWidgets.QPushButton("Удалить выбранные")
        self.apps_add_btn.clicked.connect(self.add_apps)
        self.apps_del_btn.clicked.connect(self.del_apps)

        self.urls_list = QtWidgets.QListWidget(); self.urls_list.addItems(urls)
        self.url_edit = QtWidgets.QLineEdit()
        self.url_add_btn = QtWidgets.QPushButton("Добавить URL")
        self.url_del_btn = QtWidgets.QPushButton("Удалить выбранные")
        self.url_add_btn.clicked.connect(self.add_url)
        self.url_del_btn.clicked.connect(self.del_urls)

        form = QtWidgets.QFormLayout()
        form.addRow("Имя профиля:", self.name_edit)
        hb = QtWidgets.QHBoxLayout(); hb.addWidget(self.browser_edit); hb.addWidget(self.browser_btn)
        form.addRow("Браузер (.exe или .lnk):", hb)

        apps_lbl = QtWidgets.QLabel("Программы/файлы (exe/lnk/docx/xlsx/pptx/и т.д.):")
        urls_lbl = QtWidgets.QLabel("Сайты (URL):")

        apps_btns = QtWidgets.QHBoxLayout(); apps_btns.addWidget(self.apps_add_btn); apps_btns.addWidget(self.apps_del_btn)
        urls_btns = QtWidgets.QHBoxLayout(); urls_btns.addWidget(self.url_edit); urls_btns.addWidget(self.url_add_btn); urls_btns.addWidget(self.url_del_btn)

        buttons = QtWidgets.QDialogButtonBox();
        ok = buttons.addButton("Сохранить", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        cancel = buttons.addButton("Отмена", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        ok.setObjectName("Primary"); cancel.setObjectName("Ghost")
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)

        main = QtWidgets.QVBoxLayout(self)
        main.addLayout(form)
        main.addWidget(apps_lbl); main.addWidget(self.apps_list); main.addLayout(apps_btns)
        main.addSpacing(8)
        main.addWidget(urls_lbl); main.addWidget(self.urls_list); main.addLayout(urls_btns)
        main.addStretch(1); main.addSpacing(8); main.addWidget(buttons)

        self.apply_theme()

    def apply_theme(self):
        qss = (BUTTONS_QSS % self.theme.__dict__) + ("QDialog { background: %s; }" % self.theme.base)
        self.setStyleSheet(qss)


    def pick_browser(self):
        dlg = QtWidgets.QFileDialog(self, "Выберите браузер (.exe или .lnk)")
        dlg.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile if PYQT6 else QtWidgets.QFileDialog.ExistingFile)
        dlg.setNameFilters(["Браузер (*.exe *.lnk)", "Все файлы (*.*)"])
        if dlg.exec():
            files = dlg.selectedFiles()
            if files:
                self.browser_edit.setText(files[0])

    def add_apps(self):
        dlg = QtWidgets.QFileDialog(self, "Выберите элементы (программы/файлы)")
        dlg.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFiles if PYQT6 else QtWidgets.QFileDialog.ExistingFiles)
        dlg.setNameFilters(["Все файлы (*.*)", "Программы (*.exe *.lnk)", "Документы/проекты (*.docx *.xlsx *.pptx *.pdf *.sln)"])
        if dlg.exec():
            for p in dlg.selectedFiles():
                if p and not self._list_contains(self.apps_list, p):
                    self.apps_list.addItem(p)

    def del_apps(self):
        for item in self.apps_list.selectedItems():
            self.apps_list.takeItem(self.apps_list.row(item))

    def add_url(self):
        u = self.url_edit.text().strip()
        if u and not self._list_contains(self.urls_list, u):
            self.urls_list.addItem(u); self.url_edit.clear()

    def del_urls(self):
        for item in self.urls_list.selectedItems():
            self.urls_list.takeItem(self.urls_list.row(item))

    def _list_contains(self, lw: QtWidgets.QListWidget, text: str) -> bool:
        return any(lw.item(i).text() == text for i in range(lw.count()))

    def get_profile(self) -> Optional[Dict]:
        name = self.name_edit.text().strip()
        if not name:
            return None
        apps = [self.apps_list.item(i).text() for i in range(self.apps_list.count())]
        urls = [self.urls_list.item(i).text() for i in range(self.urls_list.count())]
        browser_path = self.browser_edit.text().strip()
        return {"name": name, "apps": apps, "urls": urls, "browser_path": browser_path}



class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(900, 640)
        self.theme = DARK if self._prefer_dark() else LIGHT
        self.state = load_state()
        self.selected_name: Optional[str] = None


        title = QtWidgets.QLabel("Windows Launcher Profiles"); title.setObjectName("Title")
        self.theme_btn = QtWidgets.QToolButton(); self.theme_btn.setText("🌙" if self.theme.name=="dark" else "☀️")
        self.theme_btn.clicked.connect(self.toggle_theme)

        header = QtWidgets.QHBoxLayout(); header.addWidget(title); header.addStretch(1); header.addWidget(self.theme_btn)

        self.cards_container = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_container); self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch(1)

        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame if PYQT6 else QtWidgets.QFrame.NoFrame)
        scroll.setWidget(self.cards_container)


        self.autostart_chk = QtWidgets.QCheckBox("Запускать при входе в Windows"); self.autostart_chk.setChecked(is_autostart_enabled())
        self.apply_auto_btn = QtWidgets.QPushButton("Применить"); self.apply_auto_btn.setObjectName("Ghost")
        self.apply_auto_btn.clicked.connect(self.on_apply_auto)

        self.new_btn = QtWidgets.QPushButton("Новый профиль"); self.new_btn.setObjectName("Primary")
        self.edit_btn = QtWidgets.QPushButton("Редактировать"); self.edit_btn.setObjectName("Ghost")
        self.del_btn = QtWidgets.QPushButton("Удалить"); self.del_btn.setObjectName("Danger")
        self.run_btn = QtWidgets.QPushButton("Запустить"); self.run_btn.setObjectName("Primary")

        self.new_btn.clicked.connect(self.on_new)
        self.edit_btn.clicked.connect(self.on_edit)
        self.del_btn.clicked.connect(self.on_del)
        self.run_btn.clicked.connect(self.on_run)

        footerA = QtWidgets.QHBoxLayout()
        footerA.addWidget(self.autostart_chk); footerA.addStretch(1); footerA.addWidget(self.apply_auto_btn)
        footerB = QtWidgets.QHBoxLayout()
        footerB.addWidget(self.new_btn); footerB.addWidget(self.edit_btn); footerB.addWidget(self.del_btn); footerB.addStretch(1); footerB.addWidget(self.run_btn)


        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central); root.setContentsMargins(18,18,18,18); root.setSpacing(14)
        root.addLayout(header)
        root.addWidget(scroll)
        root.addLayout(footerA)
        root.addLayout(footerB)

        self.status = QtWidgets.QStatusBar(); self.setStatusBar(self.status)

        self.apply_theme()
        self.refresh_cards()


    def _prefer_dark(self) -> bool:

        pal = self.palette(); c = pal.window().color();
        return (c.red()+c.green()+c.blue())/3 < 128

    def apply_theme(self):
        qss = (CARD_QSS % self.theme.__dict__) + (BUTTONS_QSS % self.theme.__dict__)
        self.setStyleSheet(qss)
        self.setAutoFillBackground(True)
        p = self.palette(); p.setColor(self.backgroundRole(), QtGui.QColor(self.theme.base)); self.setPalette(p)
        self.theme_btn.setText("🌙" if self.theme.name=="light" else "☀️")  # инвертируем иконку как переключатель

    def toggle_theme(self):
        self.theme = DARK if self.theme.name=="light" else LIGHT
        self.apply_theme(); self.refresh_cards()

    def refresh_cards(self):
        # clear layout except stretch
        for i in reversed(range(self.cards_layout.count()-1)):
            item = self.cards_layout.takeAt(i)
            w = item.widget()
            if w:
                w.setParent(None)
        names = sorted(self.state.get("profiles", {}).keys())
        if not names:
            empty = ProfileCard("Пока нет профилей", 0, 0, "", self.theme)
            empty.setEnabled(False)
            self.cards_layout.insertWidget(0, empty)
            self.selected_name = None
        else:
            for idx, name in enumerate(names):
                prof = self.state["profiles"][name]
                apps = prof.get("apps", [])
                urls = prof.get("urls", [])
                browser = Path(prof.get("browser_path", "")).name or ""
                card = ProfileCard(name, len(apps), len(urls), browser, self.theme)
                card.clicked.connect(self.on_card_clicked)
                self.cards_layout.insertWidget(idx, card)

    def on_card_clicked(self, name: str):
        self.selected_name = name
        self.status.showMessage(f"Выбрано: {name}", 2000)

    def on_new(self):
        dlg = ProfileEditor(self, None, self.state, self.theme)
        if dlg.exec() == (QtWidgets.QDialog.DialogCode.Accepted if PYQT6 else QtWidgets.QDialog.Accepted):
            prof = dlg.get_profile()
            if prof:
                st = load_state(); st.setdefault("profiles", {})
                st["profiles"][prof["name"]] = {"apps": prof["apps"], "urls": prof["urls"], "browser_path": prof["browser_path"]}
                save_state(st); self.state = st
                self.selected_name = prof["name"]
                self.refresh_cards(); self.status.showMessage(f"Профиль «{prof['name']}» сохранён", 3000)

    def on_edit(self):
        name = self.selected_name
        if not name: return
        dlg = ProfileEditor(self, name, self.state, self.theme)
        if dlg.exec() == (QtWidgets.QDialog.DialogCode.Accepted if PYQT6 else QtWidgets.QDialog.Accepted):
            prof = dlg.get_profile()
            if prof:
                st = load_state(); st.setdefault("profiles", {})
                if name != prof["name"] and name in st["profiles"]:
                    st["profiles"].pop(name, None)
                st["profiles"][prof["name"]] = {"apps": prof["apps"], "urls": prof["urls"], "browser_path": prof["browser_path"]}
                save_state(st); self.state = st
                self.selected_name = prof["name"]
                self.refresh_cards(); self.status.showMessage(f"Профиль «{prof['name']}» обновлён", 3000)

    def on_del(self):
        name = self.selected_name
        if not name: return
        reply = QtWidgets.QMessageBox.question(self, "Удалить профиль", f"Удалить профиль «{name}»?",
                                               QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            st = load_state(); st.get("profiles", {}).pop(name, None)
            save_state(st); self.state = st
            self.selected_name = None
            self.refresh_cards(); self.status.showMessage(f"Профиль «{name}» удалён", 3000)

    def on_run(self):
        name = self.selected_name
        if not name:
            self.status.showMessage("Сначала выберите профиль", 3000); return
        self.status.showMessage(f"Запуск профиля: {name}…", 3000)
        launch_profile(name, self.state)
        self.status.showMessage(f"Готово: {name}", 3000)

    def on_apply_auto(self):
        if self.autostart_chk.isChecked():
            ok = enable_autostart(); self.status.showMessage("Автозапуск включён" if ok else "Не удалось включить автозапуск", 3000)
            self.autostart_chk.setChecked(is_autostart_enabled())
        else:
            ok = disable_autostart(); self.status.showMessage("Автозапуск отключён" if ok else "Не удалось отключить автозапуск", 3000)
            self.autostart_chk.setChecked(is_autostart_enabled())

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())

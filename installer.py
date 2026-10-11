import sys
import os
import ctypes
import zipfile
import subprocess
from PyQt6.QtWidgets import (QApplication, QWizard, QWizardPage, QLabel, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QProgressBar, 
                             QLineEdit, QFileDialog, QCheckBox, QWidget, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor

def get_res(rel):
    """Obtiene la ruta de un recurso tanto en desarrollo como empaquetado en PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, rel)
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel)

class SoundPlayer:
    """Reproductor nativo de audio MP3 para Windows usando MCI (WinMM)."""
    def __init__(self, file_path):
        self.file_path = file_path
        self.winmm = ctypes.windll.winmm
        self.is_playing = False
        self.alias = "nesting_bgm"

    def play(self):
        if not os.path.exists(self.file_path):
            return
        # Cerrar si ya existiera
        self.stop()
        cmd_open = f'open "{self.file_path}" type mpegvideo alias {self.alias}'
        res = self.winmm.mciSendStringW(cmd_open, None, 0, None)
        if res == 0:
            self.winmm.mciSendStringW(f'play {self.alias} repeat', None, 0, None)
            self.is_playing = True

    def stop(self):
        self.winmm.mciSendStringW(f'stop {self.alias}', None, 0, None)
        self.winmm.mciSendStringW(f'close {self.alias}', None, 0, None)
        self.is_playing = False

    def toggle(self):
        if self.is_playing:
            self.stop()
        else:
            self.play()
        return self.is_playing

class UnpackThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, zip_path, dest_dir, make_desktop, make_start):
        super().__init__()
        self.zip_path = zip_path
        self.dest_dir = dest_dir
        self.make_desktop = make_desktop
        self.make_start = make_start

    def run(self):
        try:
            os.makedirs(self.dest_dir, exist_ok=True)
            if not os.path.exists(self.zip_path):
                self.finished.emit(False, f"No se encontró el paquete de instalación: {self.zip_path}")
                return

            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                items = zf.infolist()
                total = len(items)
                for idx, item in enumerate(items):
                    zf.extract(item, self.dest_dir)
                    pct = int(((idx + 1) / total) * 85)
                    self.progress.emit(pct, f"Extrayendo: {item.filename}")

            self.progress.emit(90, "Configurando accesos directos...")
            target_exe = os.path.join(self.dest_dir, "Nesting Maker Pro 2.0.1.exe")
            target_ico = os.path.join(self.dest_dir, "icon.ico")
            if not os.path.exists(target_ico):
                target_ico = target_exe

            # Crear accesos directos
            if self.make_desktop:
                desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
                shortcut_file = os.path.join(desktop_dir, "Nesting Maker Pro 2.0.1.lnk")
                self._create_shortcut(shortcut_file, target_exe, target_ico, self.dest_dir)

            if self.make_start:
                start_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
                shortcut_file = os.path.join(start_dir, "Nesting Maker Pro 2.0.1.lnk")
                self._create_shortcut(shortcut_file, target_exe, target_ico, self.dest_dir)

            self.progress.emit(100, "¡Instalación completada con éxito!")
            self.finished.emit(True, target_exe)

        except Exception as e:
            self.finished.emit(False, str(e))

    def _create_shortcut(self, lnk_path, target, icon, work_dir):
        ps_cmd = (
            f"$WshShell = New-Object -ComObject WScript.Shell; "
            f"$Shortcut = $WshShell.CreateShortcut('{lnk_path}'); "
            f"$Shortcut.TargetPath = '{target}'; "
            f"$Shortcut.IconLocation = '{icon}'; "
            f"$Shortcut.WorkingDirectory = '{work_dir}'; "
            f"$Shortcut.Save();"
        )
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], 
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                           check=True)
        except Exception:
            pass

class InstallerWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instalador - Nesting Maker Pro 2.0.1")
        self.resize(650, 480)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        
        # Icono de la ventana
        ico = get_res("icon.ico")
        if os.path.exists(ico):
            self.setWindowIcon(QIcon(ico))

        # Música de fondo
        mp3 = get_res(os.path.join("media", "Nestingmaker music.mp3"))
        self.player = SoundPlayer(mp3)
        self.player.play()

        # Estilo visual moderno y limpio
        self.setStyleSheet("""
            QWizard {
                background-color: #1e1e24;
                color: #ffffff;
            }
            QWizardPage {
                background-color: #1e1e24;
                color: #ffffff;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:disabled {
                background-color: #424242;
                color: #888888;
            }
            QLineEdit {
                background-color: #2a2a32;
                color: white;
                border: 1px solid #4a4a58;
                border-radius: 4px;
                padding: 6px;
            }
            QCheckBox {
                color: #e0e0e0;
                font-size: 13px;
            }
            QProgressBar {
                border: 1px solid #4a4a58;
                border-radius: 5px;
                background-color: #2a2a32;
                text-align: center;
                color: white;
                font-weight: bold;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)

        # Añadir botón de silenciar / reanudar música en la botonera inferior
        self.btn_sound = QPushButton("🔊 Música: ON")
        self.btn_sound.setStyleSheet("background-color: #3f51b5; color: white; border-radius: 4px; padding: 5px 10px;")
        self.btn_sound.clicked.connect(self.toggle_music)
        self.setButton(QWizard.WizardButton.HelpButton, self.btn_sound)
        self.setOption(QWizard.WizardOption.HaveHelpButton, True)

        # Páginas
        self.page_welcome = self.create_welcome_page()
        self.page_target = self.create_target_page()
        self.page_progress = self.create_progress_page()
        self.page_finish = self.create_finish_page()

        self.addPage(self.page_welcome)
        self.addPage(self.page_target)
        self.addPage(self.page_progress)
        self.addPage(self.page_finish)

        self.installed_exe = ""

    def toggle_music(self):
        playing = self.player.toggle()
        self.btn_sound.setText("🔊 Música: ON" if playing else "🔇 Música: OFF")
        self.btn_sound.setStyleSheet("background-color: #3f51b5;" if playing else "background-color: #616161;")

    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)

    def create_welcome_page(self):
        page = QWizardPage()
        page.setTitle("Bienvenido a Nesting Maker Pro 2.0.1")
        page.setSubTitle("Optimización inteligente de corte por láser y CNC con tecnología Raster.")
        
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Logotipo
        logo_path = get_res(os.path.join("media", "Logo.jpg"))
        if os.path.exists(logo_path):
            lbl_logo = QLabel()
            pix = QPixmap(logo_path).scaled(110, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl_logo)

        intro = QLabel(
            "<h2 style='color: #4CAF50; text-align: center;'>Nesting Maker Pro 2.0.1</h2>"
            "<p style='text-align: center; color: #bbb; font-size: 13px;'>"
            "Este asistente instalará la nueva versión 2.0.1 en tu equipo.<br>"
            "Incluye el nuevo motor matemático de <b>falsos píxeles (FFT)</b>, soporte multi-proyecto, temas claro/oscuro y selección de idioma español/inglés."
            "</p>"
            "<p style='text-align: center; color: #ba68c8; font-size: 13px; margin-top: 15px;'>"
            "Creado con 💜 por: <b>Javier Bayón Álvarez</b>"
            "</p>"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addStretch()

        return page

    def create_target_page(self):
        page = QWizardPage()
        page.setTitle("Seleccionar carpeta de instalación")
        page.setSubTitle("Elige dónde deseas instalar Nesting Maker Pro en tu ordenador.")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        default_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", "Nesting Maker Pro 2.0.1")
        
        lbl = QLabel("Carpeta de destino:")
        lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl)

        dir_layout = QHBoxLayout()
        self.edit_dir = QLineEdit(default_dir)
        btn_browse = QPushButton("Examinar...")
        btn_browse.setStyleSheet("background-color: #455a64;")
        btn_browse.clicked.connect(self.browse_dir)
        dir_layout.addWidget(self.edit_dir)
        dir_layout.addWidget(btn_browse)
        layout.addLayout(dir_layout)

        layout.addSpacing(10)
        
        lbl_opt = QLabel("Opciones adicionales:")
        lbl_opt.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl_opt)

        self.chk_desktop = QCheckBox("Crear acceso directo en el Escritorio")
        self.chk_desktop.setChecked(True)
        self.chk_start = QCheckBox("Crear acceso directo en el Menú Inicio")
        self.chk_start.setChecked(True)

        layout.addWidget(self.chk_desktop)
        layout.addWidget(self.chk_start)
        layout.addStretch()

        return page

    def browse_dir(self):
        sel = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta", self.edit_dir.text())
        if sel:
            self.edit_dir.setText(os.path.join(sel, "Nesting Maker Pro 2.0.1"))

    def create_progress_page(self):
        page = QWizardPage()
        page.setTitle("Instalando Nesting Maker Pro...")
        page.setSubTitle("Por favor espera mientras se extraen y configuran los archivos.")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(15)

        self.lbl_step = QLabel("Iniciando descompresión...")
        self.lbl_step.setStyleSheet("color: #81c784; font-size: 13px;")
        layout.addWidget(self.lbl_step)

        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        layout.addWidget(self.pbar)

        self.lbl_detail = QLabel("Preparando...")
        self.lbl_detail.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.lbl_detail)
        layout.addStretch()

        return page

    def initializePage(self, page_id):
        super().initializePage(page_id)
        if page_id == 2:  # Página de progreso
            self.button(QWizard.WizardButton.BackButton).setEnabled(False)
            self.button(QWizard.WizardButton.NextButton).setEnabled(False)
            
            dest = self.edit_dir.text().strip()
            zip_file = get_res("app_payload.zip")
            
            self.thread = UnpackThread(zip_file, dest, self.chk_desktop.isChecked(), self.chk_start.isChecked())
            self.thread.progress.connect(self.on_progress)
            self.thread.finished.connect(self.on_install_finished)
            self.thread.start()

    def on_progress(self, val, text):
        self.pbar.setValue(val)
        self.lbl_detail.setText(text)

    def on_install_finished(self, ok, result):
        if ok:
            self.installed_exe = result
            self.button(QWizard.WizardButton.NextButton).setEnabled(True)
            self.next()
        else:
            self.lbl_step.setText("Error en la instalación:")
            self.lbl_detail.setText(result)
            self.lbl_step.setStyleSheet("color: #e53935; font-size: 13px;")

    def create_finish_page(self):
        page = QWizardPage()
        page.setTitle("¡Instalación completada!")
        page.setSubTitle("Nesting Maker Pro 2.0.1 está listo para utilizarse.")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        lbl_check = QLabel("<h1 style='text-align: center; color: #4CAF50;'>✅</h1>")
        layout.addWidget(lbl_check)

        lbl_success = QLabel(
            "<h3 style='text-align: center; color: white;'>¡Instalación finalizada con éxito!</h3>"
            "<p style='text-align: center; color: #bbb; font-size: 13px;'>"
            "Se han creado los accesos directos configurados.<br>"
            "Ya puedes comenzar a anidar tus diseños para corte láser y CNC."
            "</p>"
        )
        layout.addWidget(lbl_success)

        self.chk_launch = QCheckBox("Ejecutar Nesting Maker Pro 2.0.1 ahora")
        self.chk_launch.setChecked(True)
        self.chk_launch.setStyleSheet("font-weight: bold; font-size: 13px; color: #81c784; margin-top: 15px;")
        layout.addWidget(self.chk_launch, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        return page

    def accept(self):
        self.player.stop()
        if self.chk_launch.isChecked() and self.installed_exe and os.path.exists(self.installed_exe):
            subprocess.Popen([self.installed_exe], cwd=os.path.dirname(self.installed_exe))
        super().accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = InstallerWizard()
    wizard.show()
    sys.exit(app.exec())

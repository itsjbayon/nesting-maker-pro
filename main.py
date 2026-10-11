import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QGraphicsView, QGraphicsScene, QSpinBox, QDoubleSpinBox, QFormLayout, 
                             QGroupBox, QScrollArea, QFrame, QMessageBox, QComboBox, QDialog, QTextBrowser)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath, QTransform, QPainter, QPixmap, QIcon

from nesting_engine import NestingEngine

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)

class ZoomView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(35, 35, 40)))
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.zoom_factor = 1.15
        self._is_panning = False
        self._last_mouse_pos = None

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            zoom = self.zoom_factor
        else:
            zoom = 1 / self.zoom_factor
        self.scale(zoom, zoom)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.position() - self._last_mouse_pos
            self._last_mouse_pos = event.position()
            
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - int(delta.x()))
            v_bar.setValue(v_bar.value() - int(delta.y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

TRANSLATIONS = {
    'es': {
        'window_title': "Nesting Maker Pro 2.0.1 (Raster Engine) - Laser & CNC",
        'mat_group': "1. Tamaño del Material (mm)",
        'width_lbl': "Ancho (X):",
        'height_lbl': "Alto (Y):",
        'settings_group': "2. Ajustes de Nesting",
        'margin_lbl': "Margen (mm):",
        'rotation_lbl': "Rotación:",
        'rot_modes': ["Sin Rotación", "Giros de 90º", "Rotación Libre (Auto)"],
        'btn_add': "3. ➕ Añadir SVG(s)...",
        'btn_clear': "🗑️ Limpiar Lista de Piezas",
        'btn_nest': "4. Optimizar (Nesting)",
        'btn_export': "5. Exportar SVG Final",
        'status_waiting': "Estado: Esperando archivo...",
        'status_ready': "Estado: {count} piezas listas ({files} archivo(s) añadidos).",
        'status_empty': "Lista vaciada. Puedes añadir nuevos archivos SVG.",
        'status_calculating': "Calculando Nesting... por favor espera.",
        'status_completed': "¡Nesting completado! Revisa y exporta.",
        'status_deleted': "Pieza eliminada. Quedan {count} piezas.",
        'status_all_deleted': "Todas las piezas han sido eliminadas.",
        'status_error_svg': "Error: No se encontraron piezas válidas.",
        'btn_info': "ℹ️ Novedades v2.0.1 & Créditos",
        'signature': "<b>Nesting Maker Pro 2.0.1</b><br>Creado con 💜 por: Javier Bayón Álvarez",
        'pieces_header': "<b>Piezas a procesar</b>",
        'piece_num': "Pieza",
        'cant_lbl': "Cant:",
        'btn_del': "🗑️ Eliminar",
        'theme_label': "🎨 Tema:",
        'lang_label': "🌐 Idioma:",
        'theme_dark': "🌙 Oscuro",
        'theme_light': "☀️ Claro",
        'open_svg_dialog': "Seleccionar uno o varios archivos SVG",
        'save_svg_dialog': "Guardar SVG Optimizado",
        'export_success': "Archivo exportado correctamente en:\n{path}",
        'export_error': "Hubo un error al exportar el archivo.",
        'dialog_title': "Nesting Maker Pro 2.0.1 - Información & Novedades",
        'dialog_header': "Nesting Maker Pro 2.0.1",
        'dialog_sub': "<b>Raster Engine Edition</b> • Optimización Inteligente para Corte Láser & CNC",
        'dialog_author': "Creado con 💜 por: <b>Javier Bayón Álvarez</b>",
        'dialog_evolution': "🚀 Evolución: Versión 1.0 vs Versión 2.0.1",
        'dialog_intro': "Esta versión 2.0.1 supone un salto radical de arquitectura respecto a la v1.0, incorporando tecnología de última generación inspirada en motores web como <i>LaserBurn AI</i>:",
        'col_feature': "Característica",
        'col_v1': "Versión 1.0 (Anterior)",
        'col_v2': "Versión 2.0.1 (Superversión)",
        'feat_engine': "Cerebro Algorítmico",
        'feat_engine_v1': "Cálculo geométrico NFP clásico. Lento o vulnerable a bloqueos ante curvas de Bézier complejas.",
        'feat_engine_v2': "<b>Malla Matricial Discreta + FFT</b>: Detección de colisiones mediante convolución de 'falsos píxeles' en milisegundos. Inmune a errores de dibujo.",
        'feat_holes': "Piezas con Recortes Interiores",
        'feat_holes_v1': "Fragmentaba la pieza: el marco exterior y los cortes interiores se trataban como piezas sueltas.",
        'feat_holes_v2': "<b>Topología Jerárquica Automática</b>: Detecta y agrupa recortes interiores en un solo conjunto rígido protegido.",
        'feat_packing': "Aprovechamiento de Huecos",
        'feat_packing_v1': "El hueco central de un aro o marco quedaba como material totalmente desperdiciado.",
        'feat_packing_v2': "<b>Hole-Packing Inteligente</b>: El algoritmo embuta piezas pequeñas dentro de piezas grandes si encajan.",
        'feat_multi': "Múltiples Proyectos (Multi-SVG)",
        'feat_multi_v1': "Solo permitía cargar un único archivo cada vez.",
        'feat_multi_v2': "<b>Carga acumulativa</b>: Añade múltiples SVG de diferentes proyectos y organízalos juntos en la misma chapa.",
        'feat_nav': "Navegación e Interfaz",
        'feat_nav_v1': "Zoom básico sin desplazamiento fluido.",
        'feat_nav_v2': "<b>Panorámica (Pan) con Botón Central</b> de ratón, selector de tema Claro/Oscuro y soporte multilingüe (ES/EN).",
        'feat_export': "Exportación Taller",
        'feat_export_v1': "Exportación básica con posibles desajustes.",
        'feat_export_v2': "<b>SVG optimizado</b> para LightBurn, fresadoras CNC y láser (CO2 / Fibra / Diodo).",
        'tips_title': "🛠️ Consejos de uso para el Taller",
        'tip_margin': "<b>Margen (mm):</b> Configura el valor según el sangrado (kerf) del láser o diámetro de fresa.",
        'tip_rot': "<b>Modo de Rotación:</b> <i>Giros de 90º</i> proporciona el máximo aprovechamiento con alta rapidez.",
        'tip_nav': "<b>Navegación:</b> Mantén pulsada la rueda del ratón y mueve el cursor para desplazarte con comodidad.",
        'dialog_close': "Entendido"
    },
    'en': {
        'window_title': "Nesting Maker Pro 2.0.1 (Raster Engine) - Laser & CNC",
        'mat_group': "1. Material Size (mm)",
        'width_lbl': "Width (X):",
        'height_lbl': "Height (Y):",
        'settings_group': "2. Nesting Settings",
        'margin_lbl': "Margin (mm):",
        'rotation_lbl': "Rotation:",
        'rot_modes': ["No Rotation", "90º Rotations", "Free Rotation (Auto)"],
        'btn_add': "3. ➕ Add SVG(s)...",
        'btn_clear': "🗑️ Clear All Pieces",
        'btn_nest': "4. Optimize (Nesting)",
        'btn_export': "5. Export Final SVG",
        'status_waiting': "Status: Waiting for files...",
        'status_ready': "Status: {count} pieces ready ({files} file(s) added).",
        'status_empty': "Piece list cleared. Ready to add new SVG files.",
        'status_calculating': "Calculating Nesting... please wait.",
        'status_completed': "Nesting completed! Review and export.",
        'status_deleted': "Piece removed. {count} pieces remaining.",
        'status_all_deleted': "All pieces have been removed.",
        'status_error_svg': "Error: No valid shapes found in files.",
        'btn_info': "ℹ️ What's New v2.0.1 & Credits",
        'signature': "<b>Nesting Maker Pro 2.0.1</b><br>Created with 💜 by: Javier Bayón Álvarez",
        'pieces_header': "<b>Pieces to process</b>",
        'piece_num': "Piece",
        'cant_lbl': "Qty:",
        'btn_del': "🗑️ Delete",
        'theme_label': "🎨 Theme:",
        'lang_label': "🌐 Language:",
        'theme_dark': "🌙 Dark",
        'theme_light': "☀️ Light",
        'open_svg_dialog': "Select one or multiple SVG files",
        'save_svg_dialog': "Save Optimized SVG",
        'export_success': "File exported successfully to:\n{path}",
        'export_error': "An error occurred while exporting the file.",
        'dialog_title': "Nesting Maker Pro 2.0.1 - Information & What's New",
        'dialog_header': "Nesting Maker Pro 2.0.1",
        'dialog_sub': "<b>Raster Engine Edition</b> • Smart Optimization for Laser & CNC Cutting",
        'dialog_author': "Created with 💜 by: <b>Javier Bayón Álvarez</b>",
        'dialog_evolution': "🚀 Evolution: Version 1.0 vs Version 2.0.1",
        'dialog_intro': "Version 2.0.1 is a radical architectural leap from v1.0, featuring cutting-edge technology inspired by modern web engines like <i>LaserBurn AI</i>:",
        'col_feature': "Feature",
        'col_v1': "Version 1.0 (Previous)",
        'col_v2': "Version 2.0.1 (Super Edition)",
        'feat_engine': "Algorithmic Brain",
        'feat_engine_v1': "Classic geometric NFP solver. Slow or vulnerable to freezing on complex Bézier curves.",
        'feat_engine_v2': "<b>Discrete Matrix Grid + FFT</b>: True-shape collision detection via 'virtual pixels' in milliseconds. Immune to drawing flaws.",
        'feat_holes': "Parts with Interior Cutouts",
        'feat_holes_v1': "Fragmented pieces: outer borders and inner cutouts were treated as separate loose shapes.",
        'feat_holes_v2': "<b>Automatic Hierarchical Topology</b>: Automatically groups interior cutouts into a single rigid part with protected holes.",
        'feat_packing': "Hole-Packing Efficiency",
        'feat_packing_v1': "The central empty hole in a ring or hollow frame was completely wasted material.",
        'feat_packing_v2': "<b>Intelligent Hole-Packing</b>: The algorithm nests smaller parts inside larger parts' holes if they fit.",
        'feat_multi': "Multi-Project Nesting",
        'feat_multi_v1': "Only allowed loading a single SVG file at a time.",
        'feat_multi_v2': "<b>Cumulative Loading</b>: Add multiple SVGs from different projects and nest them together on one sheet.",
        'feat_nav': "Canvas Navigation & UI",
        'feat_nav_v1': "Basic zoom without smooth center panning.",
        'feat_nav_v2': "<b>Middle-Mouse Panning</b>, Dark & Light themes, and bilingual support (ES/EN).",
        'feat_export': "Workshop Export",
        'feat_export_v1': "Basic export with possible offset discrepancies.",
        'feat_export_v2': "<b>Optimized SVG</b> for LightBurn, CNC routers, and laser cutters (CO2 / Fiber / Diode).",
        'tips_title': "🛠️ Workshop Practical Tips",
        'tip_margin': "<b>Margin (mm):</b> Adjust according to laser kerf or router bit diameter plus safety clearance.",
        'tip_rot': "<b>Rotation Mode:</b> <i>90º Rotations</i> provides the best balance between packing density and calculation speed.",
        'tip_nav': "<b>Navigation:</b> Hold the mouse scroll wheel and drag to pan across the sheet smoothly.",
        'dialog_close': "Got it"
    }
}

class InfoDialog(QDialog):
    def __init__(self, parent=None, lang='es'):
        super().__init__(parent)
        t = TRANSLATIONS.get(lang, TRANSLATIONS['es'])
        self.setWindowTitle(t['dialog_title'])
        self.resize(740, 580)
        layout = QVBoxLayout(self)

        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        logo_path = get_resource_path(os.path.join("media", "Logo.jpg")).replace('\\', '/')
        logo_tag = f'<img src="file:///{logo_path}" width="70" style="border-radius: 10px; margin-bottom: 6px;"><br>' if os.path.exists(logo_path) else ''

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        html_content = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.5; color: #222;">
            <div style="text-align: center; margin-bottom: 15px;">
                {logo_tag}
                <h1 style="color: #4CAF50; margin-bottom: 4px; font-size: 24px;">{t['dialog_header']}</h1>
                <p style="font-size: 14px; color: #555; margin-top: 0;">
                    {t['dialog_sub']}
                </p>
                <p style="font-size: 13px; color: #6a1b9a; background-color: #f3e5f5; display: inline-block; padding: 6px 14px; border-radius: 20px;">
                    {t['dialog_author']}
                </p>
            </div>
            
            <hr style="border: 0; border-top: 1px solid #e0e0e0; margin: 15px 0;">

            <h3 style="color: #1976D2; margin-bottom: 8px;">{t['dialog_evolution']}</h3>
            <p style="font-size: 13px; color: #444;">
                {t['dialog_intro']}
            </p>

            <table border="1" cellpadding="9" cellspacing="0" style="border-collapse: collapse; width: 100%; border-color: #ddd; font-size: 12.5px;">
                <tr style="background-color: #f5f5f5;">
                    <th style="width: 25%; text-align: left;">{t['col_feature']}</th>
                    <th style="width: 35%; text-align: left; color: #757575;">{t['col_v1']}</th>
                    <th style="width: 40%; text-align: left; color: #2e7d32;">{t['col_v2']}</th>
                </tr>
                <tr>
                    <td><b>{t['feat_engine']}</b></td>
                    <td>{t['feat_engine_v1']}</td>
                    <td>{t['feat_engine_v2']}</td>
                </tr>
                <tr>
                    <td><b>{t['feat_holes']}</b></td>
                    <td>{t['feat_holes_v1']}</td>
                    <td>{t['feat_holes_v2']}</td>
                </tr>
                <tr>
                    <td><b>{t['feat_packing']}</b></td>
                    <td>{t['feat_packing_v1']}</td>
                    <td>{t['feat_packing_v2']}</td>
                </tr>
                <tr>
                    <td><b>{t['feat_multi']}</b></td>
                    <td>{t['feat_multi_v1']}</td>
                    <td>{t['feat_multi_v2']}</td>
                </tr>
                <tr>
                    <td><b>{t['feat_nav']}</b></td>
                    <td>{t['feat_nav_v1']}</td>
                    <td>{t['feat_nav_v2']}</td>
                </tr>
                <tr>
                    <td><b>{t['feat_export']}</b></td>
                    <td>{t['feat_export_v1']}</td>
                    <td>{t['feat_export_v2']}</td>
                </tr>
            </table>

            <h3 style="color: #1976D2; margin-top: 20px; margin-bottom: 8px;">{t['tips_title']}</h3>
            <ul style="font-size: 13px; color: #444; padding-left: 20px;">
                <li>{t['tip_margin']}</li>
                <li>{t['tip_rot']}</li>
                <li>{t['tip_nav']}</li>
            </ul>

            <hr style="border: 0; border-top: 1px solid #e0e0e0; margin: 15px 0;">
            <p style="text-align: center; color: #888; font-size: 12px; margin-bottom: 5px;">
                © 2026 Nesting Maker Pro • Javier Bayón Álvarez
            </p>
        </div>
        """
        browser.setHtml(html_content)
        layout.addWidget(browser)

        btn_close = QPushButton(t['dialog_close'])
        btn_close.setFixedWidth(120)
        btn_close.setMinimumHeight(32)
        btn_close.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_lang = 'es'
        self.current_theme = 'dark'
        
        self.engine = NestingEngine()
        self.piece_widgets = [] 
        
        self.resize(1280, 880)
        
        # Establecer icono de la ventana principal
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(8, 6, 8, 8)
        main_layout.setSpacing(6)
        
        # --- Barra Superior (Header con Tema e Idioma arriba a la derecha) ---
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(8, 4, 8, 4)
        
        # Logotipo en la cabecera
        logo_path = get_resource_path(os.path.join("media", "Logo.jpg"))
        if os.path.exists(logo_path):
            logo_lbl = QLabel()
            logo_pix = QPixmap(logo_path).scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(logo_pix)
            logo_lbl.setStyleSheet("border-radius: 6px; margin-right: 4px;")
            top_bar_layout.addWidget(logo_lbl)
        
        self.header_title = QLabel("<b>Nesting Maker Pro</b> <span style='color: #4CAF50;'>v2.0.1</span>")
        self.header_title.setStyleSheet("font-size: 15px;")
        top_bar_layout.addWidget(self.header_title)
        
        top_bar_layout.addStretch()
        
        # Selector de Tema
        self.theme_label = QLabel("🎨 Tema:")
        self.theme_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["🌙 Oscuro", "☀️ Claro"])
        self.theme_combo.setMinimumWidth(110)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        
        top_bar_layout.addWidget(self.theme_label)
        top_bar_layout.addWidget(self.theme_combo)
        
        top_bar_layout.addSpacing(20)
        
        # Selector de Idioma (Arriba a la derecha)
        self.lang_label = QLabel("🌐 Idioma:")
        self.lang_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["🇪🇸 Español", "🇬🇧 English"])
        self.lang_combo.setMinimumWidth(125)
        self.lang_combo.currentIndexChanged.connect(self.on_lang_changed)
        
        top_bar_layout.addWidget(self.lang_label)
        top_bar_layout.addWidget(self.lang_combo)
        
        main_layout.addWidget(top_bar)
        
        # --- Contenedor Principal (3 columnas: Izquierda, Canvas, Derecha) ---
        content_layout = QHBoxLayout()
        content_layout.setSpacing(8)
        
        # --- Panel Izquierdo (Controles) ---
        left_panel = QWidget()
        left_panel.setFixedWidth(270)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(6, 6, 6, 6)
        
        self.material_group = QGroupBox("1. Tamaño del Material (mm)")
        material_layout = QFormLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 10000)
        self.width_spin.setValue(1200)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 10000)
        self.height_spin.setValue(600)
        
        self.width_spin.valueChanged.connect(self.draw_workspace)
        self.height_spin.valueChanged.connect(self.draw_workspace)
        
        self.lbl_width = QLabel("Ancho (X):")
        self.lbl_height = QLabel("Alto (Y):")
        material_layout.addRow(self.lbl_width, self.width_spin)
        material_layout.addRow(self.lbl_height, self.height_spin)
        self.material_group.setLayout(material_layout)
        left_layout.addWidget(self.material_group)
        
        # --- Ajustes del Algoritmo ---
        self.settings_group = QGroupBox("2. Ajustes de Nesting")
        settings_layout = QFormLayout()
        
        self.margin_spin = QDoubleSpinBox()
        self.margin_spin.setRange(0, 100)
        self.margin_spin.setSingleStep(1)
        self.margin_spin.setValue(5.0)
        
        self.rotation_combo = QComboBox()
        self.rotation_combo.addItems(["Sin Rotación", "Giros de 90º", "Rotación Libre (Auto)"])
        self.rotation_combo.setCurrentIndex(1) # Por defecto 90º
        
        self.lbl_margin = QLabel("Margen (mm):")
        self.lbl_rotation = QLabel("Rotación:")
        settings_layout.addRow(self.lbl_margin, self.margin_spin)
        settings_layout.addRow(self.lbl_rotation, self.rotation_combo)
        self.settings_group.setLayout(settings_layout)
        left_layout.addWidget(self.settings_group)
        
        # --- Botones de Acción ---
        self.btn_load = QPushButton("3. ➕ Añadir SVG(s)...")
        self.btn_load.clicked.connect(self.load_svg)
        self.btn_load.setMinimumHeight(42)
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; font-size: 13px; border-radius: 4px;")
        left_layout.addWidget(self.btn_load)
        
        self.btn_clear = QPushButton("🗑️ Limpiar Lista de Piezas")
        self.btn_clear.clicked.connect(self.clear_all_pieces)
        self.btn_clear.setMinimumHeight(28)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setStyleSheet("background-color: #ffebee; color: #c62828; border: 1px solid #ffcdd2; border-radius: 4px; font-size: 11px; font-weight: bold;")
        left_layout.addWidget(self.btn_clear)
        
        self.btn_nest = QPushButton("4. Optimizar (Nesting)")
        self.btn_nest.clicked.connect(self.start_nesting)
        self.btn_nest.setEnabled(False)
        self.btn_nest.setMinimumHeight(50)
        self.btn_nest.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 14px; border-radius: 4px;")
        left_layout.addWidget(self.btn_nest)
        
        self.btn_export = QPushButton("5. Exportar SVG Final")
        self.btn_export.clicked.connect(self.export_svg)
        self.btn_export.setEnabled(False)
        self.btn_export.setMinimumHeight(42)
        self.btn_export.setStyleSheet("background-color: #FF9800; color: black; font-weight: bold; font-size: 13px; border-radius: 4px;")
        left_layout.addWidget(self.btn_export)
        
        self.status_label = QLabel("Estado: Esperando archivo...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("padding: 6px; border-radius: 4px;")
        left_layout.addWidget(self.status_label)
        left_layout.addStretch()
        
        self.btn_info = QPushButton("ℹ️ Novedades v2.0.1 & Créditos")
        self.btn_info.setMinimumHeight(38)
        self.btn_info.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_info.setStyleSheet("""
            QPushButton {
                background-color: #3f51b5;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #303f9f;
            }
            QPushButton:pressed {
                background-color: #1a237e;
            }
        """)
        self.btn_info.clicked.connect(self.show_info_dialog)
        left_layout.addWidget(self.btn_info)
        
        self.signature = QLabel("<b>Nesting Maker Pro 2.0.1</b><br>Creado con 💜 por: Javier Bayón Álvarez")
        self.signature.setStyleSheet("color: #888; font-size: 11px; margin-top: 5px;")
        left_layout.addWidget(self.signature)
        
        # --- Panel Central (Canvas) ---
        self.scene = QGraphicsScene()
        self.view = ZoomView(self.scene)
        
        # --- Panel Derecho (Piezas) ---
        right_panel = QWidget()
        right_panel.setFixedWidth(330)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(6, 6, 6, 6)
        
        self.right_title = QLabel("<b>Piezas a procesar</b>")
        self.right_title.setStyleSheet("font-size: 13px;")
        right_layout.addWidget(self.right_title)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.pieces_container = QWidget()
        self.pieces_layout = QVBoxLayout(self.pieces_container)
        self.pieces_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.pieces_layout.setSpacing(6)
        
        self.scroll_area.setWidget(self.pieces_container)
        right_layout.addWidget(self.scroll_area)
        
        content_layout.addWidget(left_panel)
        content_layout.addWidget(self.view, stretch=1)
        content_layout.addWidget(right_panel)
        main_layout.addLayout(content_layout)
        
        # Aplicar tema inicial y traducciones
        self.apply_theme(self.current_theme)
        self.retranslate_ui()
        self.draw_workspace()

    def on_theme_changed(self, index):
        theme = 'dark' if index == 0 else 'light'
        self.apply_theme(theme)

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        if theme_name == 'dark':
            self.view.setBackgroundBrush(QBrush(QColor(28, 28, 33)))
            self.pieces_container.setStyleSheet("background-color: #232328;")
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #1a1a1e;
                    color: #e0e0e0;
                }
                QGroupBox {
                    border: 1px solid #3c3c44;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                    color: #81c784;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 4px;
                }
                QLabel {
                    color: #e0e0e0;
                }
                QSpinBox, QDoubleSpinBox, QComboBox {
                    background-color: #2a2a30;
                    color: #ffffff;
                    border: 1px solid #454550;
                    border-radius: 4px;
                    padding: 4px;
                }
                QComboBox QAbstractItemView {
                    background-color: #2a2a30;
                    color: #ffffff;
                    selection-background-color: #3f51b5;
                }
                QScrollArea {
                    border: 1px solid #33333a;
                }
            """)
        else:
            self.view.setBackgroundBrush(QBrush(QColor(238, 238, 242)))
            self.pieces_container.setStyleSheet("background-color: #eaebee;")
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #f7f7f9;
                    color: #222222;
                }
                QGroupBox {
                    border: 1px solid #d0d0d5;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                    color: #2e7d32;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 4px;
                }
                QLabel {
                    color: #222222;
                }
                QSpinBox, QDoubleSpinBox, QComboBox {
                    background-color: #ffffff;
                    color: #111111;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 4px;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    color: #111111;
                    selection-background-color: #e0e0e0;
                }
                QScrollArea {
                    border: 1px solid #d0d0d5;
                }
            """)
        self.draw_workspace()
        self.update_pieces_list()

    def on_lang_changed(self, index):
        self.current_lang = 'es' if index == 0 else 'en'
        self.retranslate_ui()

    def retranslate_ui(self):
        t = TRANSLATIONS[self.current_lang]
        self.setWindowTitle(t['window_title'])
        self.material_group.setTitle(t['mat_group'])
        self.lbl_width.setText(t['width_lbl'])
        self.lbl_height.setText(t['height_lbl'])
        self.settings_group.setTitle(t['settings_group'])
        self.lbl_margin.setText(t['margin_lbl'])
        self.lbl_rotation.setText(t['rotation_lbl'])
        
        cur_rot = self.rotation_combo.currentIndex()
        self.rotation_combo.blockSignals(True)
        self.rotation_combo.clear()
        self.rotation_combo.addItems(t['rot_modes'])
        self.rotation_combo.setCurrentIndex(cur_rot if cur_rot >= 0 else 1)
        self.rotation_combo.blockSignals(False)
        
        self.btn_load.setText(t['btn_add'])
        self.btn_clear.setText(t['btn_clear'])
        self.btn_nest.setText(t['btn_nest'])
        self.btn_export.setText(t['btn_export'])
        self.btn_info.setText(t['btn_info'])
        self.signature.setText(t['signature'])
        self.right_title.setText(t['pieces_header'])
        self.theme_label.setText(t['theme_label'])
        self.lang_label.setText(t['lang_label'])
        
        cur_theme_idx = self.theme_combo.currentIndex()
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self.theme_combo.addItems([t['theme_dark'], t['theme_light']])
        self.theme_combo.setCurrentIndex(cur_theme_idx if cur_theme_idx >= 0 else 0)
        self.theme_combo.blockSignals(False)
        
        if not self.engine.pieces:
            self.status_label.setText(t['status_waiting'])
        else:
            files_count = len(set(p.get('source_file', '') for p in self.engine.pieces))
            self.status_label.setText(t['status_ready'].format(count=len(self.engine.pieces), files=files_count))
            
        self.update_pieces_list()

    def draw_workspace(self):
        self.scene.clear()
        w = self.width_spin.value()
        h = self.height_spin.value()
        
        if self.current_theme == 'dark':
            pen = QPen(QColor(100, 255, 100))
            pen.setWidth(2)
            brush = QBrush(QColor(42, 42, 48))
        else:
            pen = QPen(QColor(46, 125, 50))
            pen.setWidth(2)
            brush = QBrush(QColor(255, 255, 255))
            
        self.scene.addRect(0, 0, w, h, pen, brush)

    def _generate_thumbnail(self, piece, size=60):
        pixmap = QPixmap(size, size)
        if self.current_theme == 'dark':
            pixmap.fill(QColor(42, 42, 48))
            pen = QPen(QColor(220, 220, 220))
            brush = QBrush(QColor(255, 140, 50, 220))
        else:
            pixmap.fill(QColor(230, 230, 235))
            pen = QPen(QColor(30, 30, 30))
            brush = QBrush(QColor(255, 120, 50, 200))
            
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(brush)
        
        scale_x = (size - 10) / piece['width'] if piece['width'] > 0 else 1
        scale_y = (size - 10) / piece['height'] if piece['height'] > 0 else 1
        scale = min(scale_x, scale_y)
        
        painter.translate(size / 2.0, size / 2.0)
        painter.scale(scale, scale)
        painter.translate(-piece['width'] / 2.0, -piece['height'] / 2.0)
        
        painter.drawPath(piece['qpath'])
        painter.end()
        return pixmap

    def update_pieces_list(self):
        t = TRANSLATIONS[self.current_lang]
        for i in reversed(range(self.pieces_layout.count())): 
            widget = self.pieces_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
                
        self.piece_widgets.clear()
        
        is_dark = (self.current_theme == 'dark')
        card_bg = "#2a2a30" if is_dark else "#ffffff"
        card_border = "#454550" if is_dark else "#cccccc"
        text_color = "#ffffff" if is_dark else "#111111"
        sub_color = "#aaaaaa" if is_dark else "#666666"
        file_color = "#64b5f6" if is_dark else "#1565C0"
        
        for i, piece in enumerate(self.engine.pieces):
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            frame.setStyleSheet(f"QFrame {{ background-color: {card_bg}; border-radius: 6px; margin-bottom: 4px; border: 1px solid {card_border}; }}")
            flyt = QHBoxLayout(frame)
            flyt.setContentsMargins(6, 6, 6, 6)
            
            thumb_label = QLabel()
            thumb_label.setPixmap(self._generate_thumbnail(piece, size=60))
            thumb_label.setFixedSize(60, 60)
            
            info_layout = QVBoxLayout()
            lbl = QLabel(f"<b>{t['piece_num']} {i+1}</b>")
            lbl.setStyleSheet(f"color: {text_color}; font-size: 13px;")
            
            src_name = piece.get('source_file', 'SVG')
            src_lbl = QLabel(f"📄 {src_name}")
            src_lbl.setStyleSheet(f"color: {file_color}; font-size: 11px;")
            src_lbl.setToolTip(f"Proviene de: {src_name}")
            
            dim_lbl = QLabel(f"{int(piece['width'])} x {int(piece['height'])} mm")
            dim_lbl.setStyleSheet(f"color: {sub_color}; font-size: 11px;")
            
            info_layout.addWidget(lbl)
            info_layout.addWidget(src_lbl)
            info_layout.addWidget(dim_lbl)
            
            controls_layout = QVBoxLayout()
            controls_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
            
            qty_layout = QHBoxLayout()
            cant_lbl = QLabel(t['cant_lbl'])
            cant_lbl.setStyleSheet(f"color: {text_color}; font-weight: bold; font-size: 12px;")
            spin = QSpinBox()
            spin.setRange(0, 1000)
            spin.setValue(1)
            spin.setMinimumWidth(65)
            qty_layout.addWidget(cant_lbl)
            qty_layout.addWidget(spin)
            
            btn_del = QPushButton(t['btn_del'])
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setToolTip("Quitar esta pieza")
            btn_del.setStyleSheet("""
                QPushButton {
                    background-color: #ffebee;
                    color: #c62828;
                    border: 1px solid #ffcdd2;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e53935;
                    color: white;
                    border-color: #c62828;
                }
                QPushButton:pressed {
                    background-color: #b71c1c;
                }
            """)
            btn_del.clicked.connect(lambda _, idx=i: self.remove_single_piece(idx))
            
            controls_layout.addLayout(qty_layout)
            controls_layout.addWidget(btn_del)
            
            flyt.addWidget(thumb_label)
            flyt.addLayout(info_layout, stretch=1)
            flyt.addLayout(controls_layout)
            
            self.pieces_layout.addWidget(frame)
            self.piece_widgets.append({'id': i, 'spin': spin})

    def load_svg(self):
        t = TRANSLATIONS[self.current_lang]
        file_paths, _ = QFileDialog.getOpenFileNames(self, t['open_svg_dialog'], "", "SVG Files (*.svg)")
        if file_paths:
            added_files = 0
            for fp in file_paths:
                if self.engine.load_svg(fp, append=True):
                    added_files += 1
            
            total_pieces = len(self.engine.pieces)
            if total_pieces > 0:
                self.btn_nest.setEnabled(True)
                self.update_pieces_list()
                self.draw_workspace()
                
                w = self.width_spin.value()
                h = self.height_spin.value()
                self.view.fitInView(-50, -50, w+100, h+100, Qt.AspectRatioMode.KeepAspectRatio)
                self.status_label.setText(t['status_ready'].format(count=total_pieces, files=added_files))
                self.btn_export.setEnabled(False)
            else:
                self.status_label.setText(t['status_error_svg'])

    def clear_all_pieces(self):
        t = TRANSLATIONS[self.current_lang]
        if not self.engine.pieces:
            return
        self.engine.clear_pieces()
        self.update_pieces_list()
        self.draw_workspace()
        self.btn_nest.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.status_label.setText(t['status_empty'])

    def remove_single_piece(self, piece_index):
        t = TRANSLATIONS[self.current_lang]
        if 0 <= piece_index < len(self.engine.pieces):
            self.engine.pieces.pop(piece_index)
            for idx, p in enumerate(self.engine.pieces):
                p['id'] = idx
            self.update_pieces_list()
            if not self.engine.pieces:
                self.btn_nest.setEnabled(False)
                self.btn_export.setEnabled(False)
                self.draw_workspace()
                self.status_label.setText(t['status_all_deleted'])
            else:
                self.status_label.setText(t['status_deleted'].format(count=len(self.engine.pieces)))

    def start_nesting(self):
        t = TRANSLATIONS[self.current_lang]
        self.status_label.setText(t['status_calculating'])
        QApplication.processEvents()
        
        quantities = {pw['id']: pw['spin'].value() for pw in self.piece_widgets}
        self.engine.set_quantities(quantities)
        self.engine.set_material_size(self.width_spin.value(), self.height_spin.value())
        
        margin = self.margin_spin.value()
        rot_mode = self.rotation_combo.currentIndex()
        self.engine.set_nesting_options(margin, rot_mode)
        
        result_paths = self.engine.run_nesting()
        
        self.draw_results(result_paths)
        self.status_label.setText(t['status_completed'])
        self.btn_export.setEnabled(True)

    def draw_results(self, placed_pieces):
        self.draw_workspace()
        pen = QPen(QColor(255, 150, 0))
        pen.setWidthF(1.5)
        brush = QBrush(QColor(255, 150, 0, 60))
        
        for qpath in placed_pieces:
            self.scene.addPath(qpath, pen, brush)

    def export_svg(self):
        t = TRANSLATIONS[self.current_lang]
        file_path, _ = QFileDialog.getSaveFileName(self, t['save_svg_dialog'], "nesting_resultado.svg", "SVG Files (*.svg)")
        if file_path:
            success = self.engine.export_svg(file_path)
            if success:
                QMessageBox.information(self, "OK", t['export_success'].format(path=file_path))
            else:
                QMessageBox.critical(self, "Error", t['export_error'])

    def show_info_dialog(self):
        dialog = InfoDialog(self, lang=self.current_lang)
        dialog.exec()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

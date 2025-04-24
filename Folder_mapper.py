import os
import sys
import logging
from datetime import datetime
import subprocess
# PyQt6 Imports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QFileDialog, QTreeWidget, QTreeWidgetItem,
                             QSplitter, QFrame, QTextEdit, QGroupBox, QHeaderView, QMenu,
                             QMessageBox, QToolTip, QScrollArea, QSizePolicy, QLineEdit,
                             QTreeWidgetItemIterator, QStyle)
from PyQt6.QtCore import (Qt, QSize, pyqtSignal, QThread, QPoint, QTimer, QUrl, 
                          QStandardPaths)
from PyQt6.QtGui import (QIcon, QFont, QColor, QBrush, QDragEnterEvent, QDropEvent, 
                          QAction, QMouseEvent)


# ─────────────────────────────────────────────────────────────────────────────
# Constantes y Configuración Global
# ─────────────────────────────────────────────────────────────────────────────

# Configuración del logging: se registran eventos en un archivo y en la salida estándar
logging.basicConfig(
    level=logging.DEBUG, # Cambiado a DEBUG para ver el mensaje de diagnóstico
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mapper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Colores y estilos
COLOR_PRIMARY = "#2B579A"
COLOR_SECONDARY = "#1C3D6B"
COLOR_HOVER = "#3A6BB5"
COLOR_DISABLED = "#CCCCCC"
COLOR_SUCCESS = "#107C10"
COLOR_ERROR = "#D83B01"
COLOR_BACKGROUND_LIGHT = "#f5f5f5"
COLOR_BORDER = "#e0e0e0"
COLOR_BORDER_DARK = "#cccccc"
COLOR_SELECTED_BACKGROUND = "#E0E0E0" # Nuevo color para fondo de ítems seleccionados

# Dimensiones
MIN_CONTROL_PANEL_WIDTH = 280
FOLDER_PATH_DISPLAY_HEIGHT = 35

# Mensajes de estado
STATUS_READY = "Estado: Listo"
STATUS_FOLDER_LOADED = "Carpeta cargada exitosamente"
STATUS_FILE_GENERATED = "Archivo generado: {}"
STATUS_ERROR_PREFIX = "Error: {}"
STATUS_PROCESSING_ITEM = "Procesando: {}" # Nuevo mensaje de estado para ítems
STATUS_LOADING_DIRECTORY = "Cargando directorio: {}" # Nuevo mensaje de estado para carga de árbol

# Estilos CSS consolidados (No change needed for PyQt6)
APP_STYLESHEET = f"""
    QGroupBox {{
        font-weight: bold;
        border: 1px solid {COLOR_BORDER_DARK};
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 3px;
    }}
    QToolTip {{
        background-color: #ffffe0;
        border: 1px solid black;
        padding: 5px;
    }}
    QTextEdit[readOnly="true"] {{ /* Style for the read-only QTextEdit */
        background-color: {COLOR_BACKGROUND_LIGHT};
        padding: 5px;
        border: 1px solid {COLOR_BORDER};
    }}
    QPushButton {{
        background-color: {COLOR_PRIMARY};
        color: white;
        border: none;
        padding: 8px; /* Increased padding slightly */
        border-radius: 3px; /* Added subtle rounding */
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {COLOR_HOVER};
    }}
    QPushButton:disabled {{
        background-color: {COLOR_DISABLED};
    }}
    #HeaderFrame {{ /* Style for the header frame */
        background-color: {COLOR_PRIMARY};
        padding: 10px;
        border-radius: 0px; /* Ensure sharp corners if desired */
    }}
    #TitleLabel {{ /* Style for the title label */
        color: white;
        font-size: 16pt;
        font-weight: bold;
    }}
    QTreeWidget {{
        font-size: 9pt;
        border: 1px solid {COLOR_BORDER};
    }}
    QTreeWidget::item:selected {{
        /* Style for the item with focus, not the logical selection for mapping */
        background-color: {COLOR_PRIMARY};
        color: white;
    }}
    #StatusLabel {{ /* Style for the status label */
        padding: 5px;
        /* text-align: center; CSS property not directly applicable here, use AlignmentFlag */
        border-top: 1px solid {COLOR_BORDER}; /* Add a separator line */
    }}
    QLineEdit {{ /* Basic styling for filter input */
         padding: 4px;
         border: 1px solid {COLOR_BORDER_DARK};
         border-radius: 3px;
    }}
"""

# Función para obtener rutas de recursos (funciona tanto en .py como en .exe) - No change needed
def get_resource_path(relative_path):
    """Obtiene la ruta absoluta a un recurso, compatible con desarrollo y producción (.exe)"""
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError: # Use AttributeError check for _MEIPASS
        # Si no estamos en un .exe, usamos la ruta del script
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, "recursos", relative_path)

# Función auxiliar para formatear el tamaño de archivo - No change needed
def format_size(size_in_bytes):
    """Convierte el tamaño en bytes a un formato legible (B, KB, MB, GB)."""
    if size_in_bytes is None:
        return "N/A"
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.2f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"

# ─────────────────────────────────────────────────────────────────────────────
# Clase para operaciones asíncronas en un hilo separado (Mapeo de Estructura)
# ─────────────────────────────────────────────────────────────────────────────

class MappingWorker(QThread):
    # Signals remain the same
    finished = pyqtSignal(str, bool)
    status_update = pyqtSignal(str, str)

    def __init__(self, root_path, tree_data):
        super().__init__()
        self.root_path = root_path
        self.tree_data = tree_data # Diccionario con paths como claves

    def run(self):
        """Ejecuta el mapeo en el hilo de trabajo."""
        try:
            # Generate structure using logic that traverses FS and checks tree_data (with paths)
            estructura = self.mapear_estructura(self.root_path)

            # Determine output path
            output_name = f"{os.path.basename(self.root_path)}-estructura.txt"
            output_path = os.path.join(self.root_path, output_name)

            # Write output file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"ESTRUCTURA DE CARPETAS\n{'='*25}\n")
                f.write(f"Ruta: {self.root_path}\n")
                f.write(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
                f.write(estructura)

            logging.info(f"Archivo de estructura generado: {output_path}")
            # Emit final success status
            self.status_update.emit(STATUS_FILE_GENERATED.format(output_path), COLOR_SUCCESS)
            self.finished.emit(output_path, True)

        except PermissionError:
            logging.error(f"Error de permisos al acceder a {self.root_path}")
            # Emit final error status
            self.status_update.emit(STATUS_ERROR_PREFIX.format("Acceso denegado a la carpeta raíz."), COLOR_ERROR)
            self.finished.emit("Permission Error", False)
        except Exception as e:
            logging.exception("Error inesperado durante el mapeo:")
            # Emit final error status
            self.status_update.emit(STATUS_ERROR_PREFIX.format(str(e)), COLOR_ERROR)
            self.finished.emit(str(e), False)

    def mapear_estructura(self, dir_path, prefix=""):
        """Recursive function to map the directory structure respecting selections."""
        try:
            items = []
            # Added error handling for os.listdir
            try:
                dir_contents = os.listdir(dir_path)
            except PermissionError:
                logging.warning(f"Permiso denegado para listar contenido en: {dir_path}")
                return f"{prefix}└── [Acceso denegado]"
            except Exception as e:
                logging.warning(f"Error al listar contenido de {dir_path}: {e}")
                return f"{prefix}└── [Error al listar: {str(e)}]"

            # Sort items (directories first, then alphabetically)
            sorted_contents = sorted(dir_contents, key=lambda x: (not os.path.isdir(os.path.join(dir_path, x)), x.lower()))

            for item_name in sorted_contents:
                full_path = os.path.join(dir_path, item_name)

                # Emit status update for the current item
                self.status_update.emit(STATUS_PROCESSING_ITEM.format(item_name), COLOR_PRIMARY) # Emit intermediate status

                # Check selection status directly using path as key in tree_data
                item_data = self.tree_data.get(full_path)

                # If item not in tree_data (e.g., not dynamically loaded), assume selected by default
                # If in tree_data, use its 'selected' status
                selected = item_data.get("selected", True) if item_data else True

                if not selected:
                    continue

                # Safely check if the element is a directory
                is_dir = False
                try:
                    is_dir = os.path.isdir(full_path)
                except Exception as e:
                    logging.warning(f"Error checking if path is directory {full_path}: {e}")
                    is_dir = False # Treat as file on error

                items.append((item_name, is_dir, full_path)) # Store full_path too

            result = []
            for index, (name, is_dir, full_item_path) in enumerate(items): # Use full_path from items
                is_last = index == len(items) - 1
                line = "└── " if is_last else "├── "
                next_prefix = "    " if is_last else "│   " # Adjusted spacing

                details = ""
                try:
                    if is_dir:
                        # Add item count for directories
                        try:
                            num_items = len(os.listdir(full_item_path))
                            details = f" ({num_items} items)"
                        except PermissionError:
                            details = " [Acceso denegado]"
                        except Exception as e:
                            details = f" [Error al contar: {str(e)}]"
                            logging.warning(f"Could not count items in {full_item_path}: {e}")
                    else:
                        # Add size for files
                        try:
                            size_bytes = os.path.getsize(full_item_path)
                            details = f" ({format_size(size_bytes)})"
                        except PermissionError:
                            details = " [Acceso denegado]"
                        except Exception as e:
                            details = f" [Error al obtener tamaño: {str(e)}]"
                            logging.warning(f"Could not get size for {full_item_path}: {e}")
                except Exception as e:
                    details = f" [Error detalles: {str(e)}]"
                    logging.warning(f"Unexpected error getting details for {full_item_path}: {e}")

                result.append(f"{prefix}{line}{'📁 ' if is_dir else '📄 '}{name}{details}") # Add details to line

                if is_dir:
                    # Add explicit check before recursive call
                    try:
                        if os.path.isdir(full_item_path): # Use full_item_path
                            sub_result = self.mapear_estructura(full_item_path, prefix + next_prefix) # Use full_item_path
                            if sub_result:
                                result.append(sub_result)
                        else:
                            logging.warning(f"Skipping recursive call for non-directory (check failed): {full_item_path}")
                    except Exception as e:
                        logging.warning(f"Error checking directory before recursive call {full_item_path}: {e}")
                        # result.append(f"{prefix}{next_prefix}└── [Error al verificar directorio: {str(e)}]")

            return "\n".join(result)
        except PermissionError:
            # Catches PermissionError if it occurs when listing the main directory (dir_path)
            logging.warning(f"Permiso denegado para mapear estructura en: {dir_path}")
            return f"{prefix}└── [Acceso denegado]"
        except Exception as e:
            logging.exception(f"Error inesperado en mapear_estructura para {dir_path}:")
            return f"{prefix}└── [Error: {str(e)}]"


# ─────────────────────────────────────────────────────────────────────────────
# Clase para la carga asíncrona de directorios al expandir el árbol
# ─────────────────────────────────────────────────────────────────────────────

class DirectoryLoaderWorker(QThread):
    # Signal definition needs adjustment for PyQt6? No, list is fine.
    finished = pyqtSignal(QTreeWidgetItem, list, str) # parent item, list of (name, is_dir, full_path), error message
    status_update = pyqtSignal(str, str) # For updating GUI status

    def __init__(self, parent_item, dir_path):
        super().__init__()
        self.parent_item = parent_item
        self.dir_path = dir_path

    def run(self):
        """Loads directory content in a separate thread."""
        loaded_items_data = []
        error_message = ""
        try:
            self.status_update.emit(STATUS_LOADING_DIRECTORY.format(os.path.basename(self.dir_path)), COLOR_PRIMARY) # Update status

            dir_contents = os.listdir(self.dir_path)
            sorted_contents = sorted(dir_contents, key=lambda x: (not os.path.isdir(os.path.join(self.dir_path, x)), x.lower()))

            for item_name in sorted_contents:
                full_path = os.path.join(self.dir_path, item_name)
                is_dir = False
                try:
                    is_dir = os.path.isdir(full_path)
                except Exception as e:
                    logging.warning(f"Error checking if path is directory in worker {full_path}: {e}")
                    is_dir = False # Treat as file on error

                loaded_items_data.append((item_name, is_dir, full_path))

        except PermissionError:
            logging.warning(f"Permiso denegado para cargar directorio en worker: {self.dir_path}")
            error_message = f"[Acceso denegado al cargar: {os.path.basename(self.dir_path)}]"
        except Exception as e:
            logging.exception(f"Error inesperado al cargar directorio en worker {self.dir_path}:")
            error_message = f"[Error al cargar: {str(e)}]"

        # Emit signal upon completion, passing loaded data or error message
        self.finished.emit(self.parent_item, loaded_items_data, error_message)


# ─────────────────────────────────────────────────────────────────────────────
# Clase EnhancedFolderMapper: Implementa la GUI y la lógica de mapeo
# ─────────────────────────────────────────────────────────────────────────────

class EnhancedFolderMapper(QMainWindow):
    def __init__(self):
        super().__init__()
        # Dictionary storing: {full_path: {"selected": state, "loaded": bool, "item": QTreeWidgetItem}}
        self.tree_data = {}
        self.mapping_worker = None # For MappingWorker
        self.loader_worker = None # For DirectoryLoaderWorker
        self.init_ui()
        self.setAcceptDrops(True) # Enable drag and drop for the main window


    def init_ui(self):
        """Initializes the user interface."""
        # Basic window setup
        self.setWindowTitle("Folder_mapper (PyQt6)")

        # Configure application icon
        icon_path = get_resource_path("Icon.ico")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
        else:
            # Use a standard icon if custom one not found (PyQt6 theme names might differ)
            # Trying common names, might need adjustment based on system theme availability
            app_icon = QIcon.fromTheme("folder-documents", QIcon.fromTheme("folder"))
            if app_icon.isNull(): # Check if the theme icon is valid
                 # Load a fallback from Qt's standard pixmaps if theme icons fail
                 standard_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon) # Example fallback
                 self.setWindowIcon(standard_icon)
            else:
                self.setWindowIcon(app_icon)

            logging.warning(f"Icono no encontrado en: {icon_path}. Usando icono por defecto/estándar.")

        # Get primary screen geometry using the preferred PyQt6 method
        primary_screen = QApplication.primaryScreen()
        if not primary_screen: # Handle case where primary screen might not be found
            logging.error("Could not retrieve primary screen information.")
            # Set a default size or handle error appropriately
            initial_width = 1024
            initial_height = 768
        else:
            screen_geometry = primary_screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            # Calculate initial window size
            initial_width = int(screen_width * 0.8)
            initial_height = int(screen_height * 0.9)

        self.setGeometry(100, 100, initial_width, initial_height)

        # Apply global styles
        self.setStyleSheet(APP_STYLESHEET)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0,0,0,0) # Remove margins for main layout

        # Header frame (top bar)
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame") # Use ObjectName for CSS
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 10, 10, 10)

        # Title Label
        title_label = QLabel("Folder_mapper")
        title_label.setObjectName("TitleLabel") # Use ObjectName for CSS
        header_layout.addWidget(title_label)
        header_layout.addStretch() # Push help button to the right

        # Help Button
        help_button = QPushButton("Ayuda")
        help_button.setToolTip("Mostrar información de ayuda y soporte")
        help_button.clicked.connect(self.mostrar_ayuda)
        header_layout.addWidget(help_button)

        main_layout.addWidget(header_frame)

        # Main horizontal splitter (Control + Main Area)
        main_splitter = QSplitter(Qt.Orientation.Horizontal) # PyQt6 Enum

        # Control panel (left)
        control_panel = QWidget()
        control_panel.setMinimumWidth(MIN_CONTROL_PANEL_WIDTH) # Set minimum width
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(10, 10, 10, 10) # Add margins inside panel

        # Folder selection section
        folder_group = QGroupBox("CARPETA A ANALIZAR")
        folder_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum) # Adjust size policy
        folder_layout = QVBoxLayout(folder_group)

        self.folder_path_display = QTextEdit("No seleccionada")
        self.folder_path_display.setReadOnly(True)
        self.folder_path_display.setFixedHeight(FOLDER_PATH_DISPLAY_HEIGHT) # Fixed height
        # PyQt6 Enums for ScrollBarPolicy
        self.folder_path_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.folder_path_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        folder_layout.addWidget(self.folder_path_display)

        browse_btn = QPushButton("Examinar")
        browse_btn.clicked.connect(lambda: self.select_folder(None))
        browse_btn.setToolTip("Seleccionar carpeta raíz para análisis")
        folder_layout.addWidget(browse_btn)
        control_layout.addWidget(folder_group)

        # View management section
        view_group = QGroupBox("GESTIÓN DE VISTA")
        view_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        view_layout = QVBoxLayout(view_group)

        view_buttons_layout = QHBoxLayout()
        expand_btn = QPushButton("Expandir Todo")
        expand_btn.setToolTip("Expandir todos los nodos cargados")
        expand_btn.clicked.connect(self._expand_all_nodes)

        collapse_btn = QPushButton("Colapsar Todo")
        collapse_btn.setToolTip("Colapsar todos los nodos del árbol")
        collapse_btn.clicked.connect(self._collapse_all_nodes)

        view_buttons_layout.addWidget(expand_btn)
        view_buttons_layout.addWidget(collapse_btn)
        view_layout.addLayout(view_buttons_layout)
        control_layout.addWidget(view_group)

        # Selection section
        selection_group = QGroupBox("SELECCIÓN")
        selection_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        selection_layout = QVBoxLayout(selection_group)

        select_all_btn = QPushButton("Seleccionar Todo")
        select_all_btn.setToolTip("Marcar todos los elementos cargados para incluir")
        select_all_btn.clicked.connect(lambda: self.toggle_all(True)) # Default propagate is True

        deselect_all_btn = QPushButton("Deseleccionar Todo")
        deselect_all_btn.setToolTip("Desmarcar todos los elementos cargados")
        deselect_all_btn.clicked.connect(lambda: self.toggle_all(False)) # Default propagate is True

        selection_layout.addWidget(select_all_btn)
        selection_layout.addWidget(deselect_all_btn)
        control_layout.addWidget(selection_group)

        # Filter section (New)
        filter_group = QGroupBox("FILTRAR")
        filter_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        filter_layout = QVBoxLayout(filter_group)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filtrar por nombre...")
        self.filter_input.setToolTip("Escriba para filtrar elementos por nombre")
        self.filter_input.textChanged.connect(self._apply_filter) # Connect textChanged signal

        filter_layout.addWidget(self.filter_input)
        control_layout.addWidget(filter_group)

        control_layout.addStretch(1) # Push generate button and status to bottom

        # Generate map button
        self.generate_btn = QPushButton("Generar Mapa")
        self.generate_btn.setToolTip("Generar el archivo de texto con la estructura seleccionada")
        self.generate_btn.clicked.connect(self.start_mapping)
        self.generate_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed) # Fixed height
        control_layout.addWidget(self.generate_btn)

        # Status label
        self.status_label = QLabel(STATUS_READY)
        self.status_label.setObjectName("StatusLabel") # Use ObjectName for CSS
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter) # PyQt6 Enum
        self.status_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed) # Fixed height
        control_layout.addWidget(self.status_label)

        # Vertical splitter for the right area (TreeView and Preview)
        right_splitter = QSplitter(Qt.Orientation.Vertical) # PyQt6 Enum

        # TreeView for file structure
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Estructura", "Tipo", "Incluir"])
        header = self.tree.header()
        # PyQt6 Enum for ResizeMode
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(1, 100)
        header.resizeSection(2, 80)
        header.setMinimumSectionSize(20)
        # header.setVisible(True) # Header is visible by default
        header.setStretchLastSection(False) # Still valid

        self.tree.itemDoubleClicked.connect(self.on_item_expanded_or_load) # Connect to unified handler
        self.tree.itemExpanded.connect(self.on_item_expanded_or_load)     # Connect expansion too
        self.tree.itemClicked.connect(self.on_item_click)
        # PyQt6 Enum for ContextMenuPolicy
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        # Preview area
        preview_widget = QWidget() # Use QWidget as container
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 5, 0, 0) # Add a little top margin
        preview_label = QLabel("Vista Previa de la Estructura (Elementos Seleccionados)")
        preview_label.setStyleSheet(f"color: {COLOR_SECONDARY}; font-size: 10pt; font-weight: bold; padding-left: 5px;") # Adjusted style
        preview_layout.addWidget(preview_label)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Courier New", 9))
        self.preview_text.setStyleSheet(f"background-color: {COLOR_BACKGROUND_LIGHT}; border: 1px solid {COLOR_BORDER};") # Match read-only style
        preview_layout.addWidget(self.preview_text)

        # Add widgets to splitters
        right_splitter.addWidget(self.tree)
        right_splitter.addWidget(preview_widget)
        right_splitter.setSizes([int(initial_height * 0.7), int(initial_height * 0.3)]) # Initial sizes

        main_splitter.addWidget(control_panel)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([int(initial_width * 0.35), int(initial_width * 0.65)]) # Adjust initial sizes

        main_layout.addWidget(main_splitter)

        # Set focus policy for potential keyboard shortcuts (if added later)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus) # PyQt6 Enum

        # Center and show window
        self.center_window()
        self.show()

    def center_window(self):
        """Centers the window on the primary screen."""
        primary_screen = QApplication.primaryScreen()
        if primary_screen:
            screen_center = primary_screen.availableGeometry().center()
            # frameGeometry() returns the geometry including window frame, move using this
            frame_geo = self.frameGeometry()
            frame_geo.moveCenter(screen_center)
            self.move(frame_geo.topLeft())
        else:
            # Fallback if screen info is unavailable
            self.resize(1024, 768)


    def mostrar_ayuda(self):
        """Displays the help dialog box."""
        # Use Markdown subset supported by QMessageBox
        info = (
            f"## ✨ Folder Mapper v2.0 (PyQt6) 🗺️\n\n"
            f"--- **Desarrollador** ---\n"
            f"🧑‍💻 José Gabriel Calderón\n\n"
            f"--- **Contacto** ---\n"
            f"🔗 GitHub: [https://github.com/Jose985537](https://github.com/Jose985537)\n" # Markdown link
            f"📧 Email: gc5444592@gmail.com\n\n"
            f"--- **Funcionalidades Principales** ---\n"
            f"* 📂 Mapeo completo de estructuras de directorios.\n" # Use Markdown list
            f"* 🔍 Selección inteligente y detallada de elementos.\n"
            f"* 📄 Generación de informes estructurados en formato TXT.\n"
            f"* 🖱️ Arrastrar y Soltar carpetas.\n"
            f"* ⚡ Carga dinámica de directorios.\n"
            f"* ⚖️ Filtrado de elementos.\n\n"
            f"--- **Derechos de Autor** ---\n"
            f"©️ 2025 Todos los derechos reservados."
        )
        # QMessageBox supports rich text (subset of HTML/Markdown)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Soporte Técnico")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setTextFormat(Qt.TextFormat.MarkdownText) # Specify Markdown
        msg_box.setText(info)
        msg_box.exec()


    def select_folder(self, folder_path=None):
        """Selects a folder and loads its structure."""
        if folder_path is None:
            # Use QFileDialog static method
            # Define starting directory (e.g., home or last used)
            start_dir = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.HomeLocation)[0]
            folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta raíz", start_dir)
        else:
            # Use path provided (e.g., from drag and drop)
            folder = folder_path

        if folder: # Proceed only if a folder was selected or provided
            try:
                self.folder_path_display.setText(folder)
                self.tree.clear()
                self.tree_data.clear() # Clear the data dictionary
                # Load only the first level initially
                self._populate_tree_level(None, folder) # Pass None as parent item for root
                self._update_status(STATUS_FOLDER_LOADED, COLOR_SUCCESS)
                # Apply the current filter after loading the structure
                self._apply_filter(self.filter_input.text())
                self._update_preview() # Update preview after loading
            except Exception as e:
                logging.exception(f"Error al seleccionar o cargar la carpeta {folder}:")
                self._update_status(STATUS_ERROR_PREFIX.format(str(e)), COLOR_ERROR)
                QMessageBox.critical(self, "Error de Carga", f"No se pudo cargar la carpeta:\n{folder}\n\nError: {e}")


    def _populate_tree_level(self, parent_item, path, items_data=None):
        """
        Populates one level of the tree with provided data.
        If items_data is None, lists the content of path.
        """
        try:
            if items_data is None:
                # List content if data not provided (for initial load)
                dir_contents = os.listdir(path)
                sorted_contents = sorted(dir_contents, key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
                items_data = []
                for item_name in sorted_contents:
                    full_path = os.path.join(path, item_name)
                    is_dir = False
                    try:
                        is_dir = os.path.isdir(full_path)
                    except Exception as e:
                        logging.warning(f"Error checking if path is directory in _populate_tree_level {full_path}: {e}")
                        is_dir = False # Treat as file on error
                    items_data.append((item_name, is_dir, full_path))

            target_node = parent_item if parent_item else self.tree # Add to tree root if parent_item is None

            for item_name, is_dir, full_path in items_data:
                # Check if item already exists (less likely with path-based keys, but good practice)
                if full_path in self.tree_data:
                     logging.warning(f"Item path {full_path} already exists in tree_data. Skipping add.")
                     continue # Avoid adding duplicates

                # Determine parent's selection state for inheritance (default to True if no parent)
                parent_selected = True
                if parent_item:
                    parent_path = parent_item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
                    if parent_path and parent_path in self.tree_data:
                        parent_selected = self.tree_data[parent_path].get("selected", True)

                # Create tree item
                tree_item = QTreeWidgetItem(target_node)

                tree_item.setText(0, item_name)
                tree_item.setText(1, "📁 Directorio" if is_dir else "📄 Archivo")
                # Store the full path in the item's data using UserRole
                tree_item.setData(0, Qt.ItemDataRole.UserRole, full_path) # PyQt6 Enum

                # Store associated data in tree_data using path as key
                current_selected_state = parent_selected # Inherit selection state
                self.tree_data[full_path] = {"selected": current_selected_state, "loaded": False, "item": tree_item}

                # Apply visual style based on selection state
                self._update_item_style(tree_item, current_selected_state)

                if is_dir:
                    # Add placeholder for dynamic loading if not already loaded
                    if not self.tree_data[full_path].get("loaded", False):
                        placeholder = QTreeWidgetItem(tree_item)
                        placeholder.setText(0, "...")
                        # Do not associate placeholder with a path in tree_data
                        # Placeholder has no data set for UserRole

            # Mark parent node as loaded if it's not the initial root load
            if parent_item is not None:
                parent_path = parent_item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
                if parent_path in self.tree_data:
                    self.tree_data[parent_path]["loaded"] = True

        except PermissionError:
            logging.warning(f"Permiso denegado para poblar nivel del árbol en: {path}")
            error_item = QTreeWidgetItem(target_node) # Add error item to parent or root
            error_item.setText(0, "[Acceso denegado]")
            error_item.setForeground(0, QColor(COLOR_ERROR)) # Use QColor directly
            # Do not associate with path in tree_data
        except Exception as e:
            logging.exception(f"Error inesperado al poblar nivel del árbol en {path}:")
            error_item = QTreeWidgetItem(target_node)
            error_item.setText(0, f"[Error: {str(e)}]")
            error_item.setForeground(0, QColor(COLOR_ERROR))
            # Do not associate with path in tree_data


    # Combined handler for item expansion and double-click to trigger loading
    def on_item_expanded_or_load(self, item: QTreeWidgetItem, column: int = -1):
        """Handles item expansion or double-click to load directory contents asynchronously."""
        if item is None: return

        item_path = item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
        if not item_path: # If no path (e.g., placeholder or error item), do nothing
            return

        data = self.tree_data.get(item_path)

        # Check if it's a directory, present in tree_data, and not yet loaded
        if data and os.path.isdir(item_path) and not data.get("loaded", False):
            # Only proceed if not already loading (basic check)
            if self.loader_worker and self.loader_worker.isRunning():
                 logging.debug("Loader worker is already running.")
                 # Optionally, you could queue requests or provide feedback
                 return

            # Remove placeholder(s) if they exist
            placeholders_to_remove = []
            for i in range(item.childCount()):
                child = item.child(i)
                # Identify placeholder by lack of UserRole data
                if child.data(0, Qt.ItemDataRole.UserRole) is None: # PyQt6 Enum
                    placeholders_to_remove.append(child)
            for placeholder in placeholders_to_remove:
                item.removeChild(placeholder)

            # Create and start the worker to load content
            logging.debug(f"Initiating DirectoryLoaderWorker for: {item_path}")
            worker = DirectoryLoaderWorker(item, item_path)

            # Connect signals
            worker.finished.connect(self._on_directory_load_finished)
            worker.status_update.connect(self._update_status)

            # Keep a reference to the worker
            self.loader_worker = worker

            # Start the worker thread
            self.loader_worker.start()
            logging.debug(f"Started DirectoryLoaderWorker for: {item_path}")

        # If it's already loaded, expansion/double-click default behavior takes over.


    def _on_directory_load_finished(self, parent_item, loaded_items_data, error_message):
        """Slot executed when DirectoryLoaderWorker finishes loading a directory."""
        parent_path = parent_item.data(0, Qt.ItemDataRole.UserRole) if parent_item else "Root" # PyQt6 Enum
        logging.debug(f"DirectoryLoaderWorker finished for item: {parent_item.text(0)} (Path: {parent_path}). Error: '{error_message}'")

        try:
            if error_message:
                # Show error item in the tree
                error_item = QTreeWidgetItem(parent_item)
                error_item.setText(0, error_message)
                error_item.setForeground(0, QColor(COLOR_ERROR))
                # Mark parent as 'loaded' even on error to prevent retry attempts
                if parent_path != "Root" and parent_path in self.tree_data:
                    self.tree_data[parent_path]["loaded"] = True
                self._update_status(f"Error al cargar {os.path.basename(str(parent_path))}: {error_message}", COLOR_ERROR)

            else:
                # Populate the tree with loaded items
                current_path = parent_item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
                if current_path:
                     self._populate_tree_level(parent_item, current_path, loaded_items_data)
                # 'loaded' flag for parent_item is updated inside _populate_tree_level

                # Update general status (optional, could be more specific)
                base_name = os.path.basename(str(parent_path)) if parent_path else "Raíz"
                self._update_status(f"Contenido de {base_name} cargado", COLOR_PRIMARY)
                # Schedule status update back to "Ready" after a short delay
                QTimer.singleShot(2000, lambda: self._update_status(STATUS_READY, COLOR_PRIMARY))

            # Apply current filter to ensure new items are correctly shown/hidden
            self._apply_filter(self.filter_input.text())

            # Update the preview, as the visible/selectable structure has changed
            self._update_preview()

        except Exception as e:
            logging.exception(f"Critical error in _on_directory_load_finished for {parent_path}:")
            self._update_status(f"Error al procesar resultados de carga: {e}", COLOR_ERROR)

        # Clean up worker reference
        self.loader_worker = None


    def on_item_click(self, item: QTreeWidgetItem, column: int):
        """Handles clicks on an item, especially the 'Include' column."""
        if column == 2: # Click on the "Include" column
            item_path = item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
            if item_path and item_path in self.tree_data:
                current_state = self.tree_data[item_path].get("selected", True)
                new_state = not current_state
                # Update state in tree_data and visually (including children if directory)
                self.toggle_item_selection(item, new_state, True) # Propagate to children
                self._update_preview() # Update preview after selection change


    def toggle_item_selection(self, item: QTreeWidgetItem, select: bool, propagate_to_children: bool):
        """Changes the selection state of an item and optionally its children."""
        item_path = item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
        if not item_path or item_path not in self.tree_data:
            # Also ignore placeholders/error messages
            return

        # Update state in the dictionary
        self.tree_data[item_path]["selected"] = select
        # Update visual style of the item
        self._update_item_style(item, select)

        # Propagate to children if it's a directory and requested
        if propagate_to_children and os.path.isdir(item_path):
            # Iterate over children ALREADY LOADED in the QTreeWidget
            for i in range(item.childCount()):
                child_item = item.child(i)
                child_path = child_item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
                # If child has path (is real item) and in tree_data
                if child_path and child_path in self.tree_data:
                    # Check if child's current state differs before recursing to avoid redundant updates
                    if self.tree_data[child_path].get("selected") != select:
                        self.toggle_item_selection(child_item, select, True) # Recursive call

        # Propagate change upwards to parent if deselecting
        # If selecting, parent should also be selected
        parent_item = item.parent()
        if parent_item: # Check if it has a parent
            parent_path = parent_item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
            if parent_path and parent_path in self.tree_data:
                if select and not self.tree_data[parent_path].get("selected", True):
                    # If selecting child, ensure parent is selected (don't propagate further up from here)
                    self.toggle_item_selection(parent_item, True, False)
                elif not select:
                    # If deselecting, check if all siblings are also deselected to potentially deselect parent
                    all_siblings_deselected = True
                    for i in range(parent_item.childCount()):
                        sibling_item = parent_item.child(i)
                        sibling_path = sibling_item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
                        if sibling_path and sibling_path in self.tree_data:
                             if self.tree_data[sibling_path].get("selected", True):
                                 all_siblings_deselected = False
                                 break
                    if all_siblings_deselected and self.tree_data[parent_path].get("selected", True):
                         # Only deselect parent if it was previously selected and all children are now deselected
                         self.toggle_item_selection(parent_item, False, False) # Don't propagate further


    def _update_item_style(self, item: QTreeWidgetItem, selected: bool):
        """Updates the visual style of an item (text and icon) based on its selection state."""
        if selected:
            item.setText(2, "☑") # Checked box
            item.setForeground(0, QColor(Qt.GlobalColor.black)) # Normal text color - PyQt6 Enum
            # item.setBackground(0, QColor(Qt.transparent)) # Normal background
        else:
            item.setText(2, "☐") # Unchecked box
            item.setForeground(0, QColor(Qt.GlobalColor.gray)) # Dimmed text color - PyQt6 Enum
            # item.setBackground(0, QColor(COLOR_BACKGROUND_LIGHT)) # Slightly different background?


    def toggle_all(self, select: bool):
        """Selects or deselects all currently loaded items in the tree."""
        logging.debug(f"Toggle all selection to: {select}")
        # Block signals temporarily to avoid excessive updates during batch change? Optional.
        # self.tree.blockSignals(True)
        iterator = QTreeWidgetItemIterator(self.tree)
        items_to_process = []
        while iterator.value():
            items_to_process.append(iterator.value()) # Collect items first
            iterator += 1

        for item in items_to_process:
            # Apply only to items with path (real data items)
            item_path = item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
            if item_path and item_path in self.tree_data:
                 # Only update if the state is different
                 if self.tree_data[item_path].get("selected") != select:
                    self.toggle_item_selection(item, select, False) # Don't propagate from here

        # self.tree.blockSignals(False)
        self._update_preview() # Update preview once at the end


    def _expand_all_nodes(self):
        """Expands all currently loaded nodes in the tree."""
        logging.debug("Expanding all nodes...")
        # Load any unloaded first-level items if root exists
        root_path = self.folder_path_display.toPlainText()
        if root_path and root_path != "No seleccionada" and os.path.isdir(root_path):
            for i in range(self.tree.topLevelItemCount()):
                top_item = self.tree.topLevelItem(i)
                self.on_item_expanded_or_load(top_item) # Ensure top levels are loaded/expanded

        self.tree.expandAll()
        self._update_status("Vista expandida", COLOR_PRIMARY)


    def _collapse_all_nodes(self):
        """Collapses all nodes in the tree."""
        logging.debug("Collapsing all nodes...")
        self.tree.collapseAll()
        self._update_status("Vista colapsada", COLOR_PRIMARY)


    def _apply_filter(self, text: str):
        """Applies a filter to the tree items based on text."""
        filter_text = text.lower().strip()
        logging.debug(f"Applying filter: '{filter_text}'")

        # Iterate through all items and hide/show based on filter
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            item_path = item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum

            # Skip placeholders or error messages (identified by lack of path)
            if item_path is None:
                item.setHidden(False) # Always show placeholders/errors? Maybe hide... depends. Let's hide if parent is hidden.
                # Check parent visibility
                parent = item.parent()
                if parent and parent.isHidden():
                    item.setHidden(True)
                else:
                     item.setHidden(False)

                iterator += 1
                continue

            item_text = item.text(0).lower()
            match = filter_text in item_text if filter_text else True

            # Simple hide/show logic (more complex logic could show parents of matches)
            item.setHidden(not match)

            iterator += 1

        self._update_preview() # Update preview after filtering


    def _update_preview(self):
        """Updates the preview area based on the current selection and filter."""
        logging.debug("Actualizando vista previa...")
        root_path = self.folder_path_display.toPlainText()
        if not root_path or root_path == "No seleccionada" or not os.path.isdir(root_path):
            self.preview_text.setText("Seleccione una carpeta válida para ver la vista previa.")
            return

        try:
            # Generate preview structure respecting selection and filter
            preview_content = self._generate_preview_structure(root_path)
            self.preview_text.setPlainText(preview_content) # Use setPlainText for efficiency
        except Exception as e:
            logging.error(f"Error generando vista previa: {e}")
            self.preview_text.setText(f"Error al generar vista previa:\n{e}")


    def _generate_preview_structure(self, dir_path, prefix="", level=0, max_items_per_level=50):
        """ Generates a preview string (limited depth/items) respecting selection/filter. """
        output = ""
        try:
            # Check if item is selected and not filtered out
            item_data = self.tree_data.get(dir_path)
            if level > 0: # Don't check root itself for selection/filter for recursive call entry
                 if not item_data or not item_data.get("selected", True):
                     return "" # Item deselected

                 item_widget = item_data.get("item")
                 if item_widget and item_widget.isHidden():
                     return "" # Item hidden by filter

            items_to_process = []
            # Get children from tree_data/widget if loaded, or listdir if not (for preview only)
            parent_item = item_data.get("item") if item_data else None

            children_paths = []
            if parent_item and item_data and item_data.get("loaded"):
                # Get loaded children from the widget
                for i in range(parent_item.childCount()):
                    child_item = parent_item.child(i)
                    child_path = child_item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
                    if child_path: # Ignore placeholders/errors
                        children_paths.append(child_path)
            elif os.path.isdir(dir_path): # Only listdir if it's actually a directory
                # List first few items from filesystem if not loaded (limit for preview)
                try:
                    dir_contents = os.listdir(dir_path)
                    sorted_contents = sorted(dir_contents, key=lambda x: (not os.path.isdir(os.path.join(dir_path, x)), x.lower()))
                    for name in sorted_contents[:max_items_per_level]:
                        children_paths.append(os.path.join(dir_path, name))
                    if len(sorted_contents) > max_items_per_level:
                         children_paths.append("...") # Indicate more items exist

                except PermissionError:
                    output += f"{prefix}└── [Acceso denegado al listar]\n"
                except Exception as e:
                    output += f"{prefix}└── [Error al listar para preview: {e}]\n"

            # Process the collected children paths
            valid_children_count = 0
            items_to_render = []
            for i, child_path in enumerate(children_paths):
                 if child_path == "...":
                      items_to_render.append(("...", False, "..."))
                      continue

                 child_data = self.tree_data.get(child_path)
                 selected = child_data.get("selected", True) if child_data else True # Default true if unknown

                 # Check filter status from the widget if available, otherwise simple text check
                 child_widget = child_data.get("item") if child_data else None
                 is_hidden = child_widget.isHidden() if child_widget else False
                 filter_text = self.filter_input.text().lower().strip()
                 if not is_hidden and filter_text: # Double check text if widget wasn't available or somehow visible
                     if filter_text not in os.path.basename(child_path).lower():
                         is_hidden = True


                 if selected and not is_hidden:
                     is_dir = False
                     try: is_dir = os.path.isdir(child_path)
                     except: pass # Ignore errors just for preview type check
                     items_to_render.append((os.path.basename(child_path), is_dir, child_path))
                     valid_children_count += 1


            # Render the filtered/selected children
            for index, (name, is_dir, full_path) in enumerate(items_to_render):
                is_last = index == len(items_to_render) - 1
                line = "└── " if is_last else "├── "
                next_prefix = "    " if is_last else "│   "

                if full_path == "...":
                     output += f"{prefix}{line}{name}\n"
                else:
                     output += f"{prefix}{line}{'📁 ' if is_dir else '📄 '}{name}\n"
                     if is_dir:
                         # Recursive call only for directories, limit depth implicitly via level check at start
                         output += self._generate_preview_structure(full_path, prefix + next_prefix, level + 1, max_items_per_level)

        except PermissionError:
            # This might catch permission error for the dir_path itself
            output += f"{prefix}[Acceso denegado a: {os.path.basename(dir_path)}]\n"
        except Exception as e:
             output += f"{prefix}[Error preview: {e}]\n"
             logging.warning(f"Error generando sub-preview para {dir_path}: {e}")

        return output


    def _update_status(self, message: str, color_hex: str):
        """Updates the status label text and color, and logs the message."""
        logging.info(message) # Log the message
        self.status_label.setText(message)
        # Use style sheet for color
        self.status_label.setStyleSheet(f"#StatusLabel {{ color: {color_hex}; padding: 5px; border-top: 1px solid {COLOR_BORDER}; }}")
        # Force immediate UI update
        QApplication.processEvents()


    def start_mapping(self):
        """Starts the mapping process in a separate thread."""
        root_path = self.folder_path_display.toPlainText()
        if not root_path or root_path == "No seleccionada" or not os.path.isdir(root_path):
            QMessageBox.warning(self, "Carpeta no válida", "Por favor, seleccione una carpeta raíz válida antes de generar el mapa.")
            return

        if self.mapping_worker and self.mapping_worker.isRunning():
            QMessageBox.information(self, "Proceso en curso", "Ya hay un proceso de mapeo en ejecución.")
            return

        logging.info(f"Iniciando mapeo para: {root_path}")
        self._update_status("Iniciando mapeo...", COLOR_PRIMARY)
        self.generate_btn.setEnabled(False) # Disable button while running

        # Pass a copy of relevant tree_data (paths and selection state) to the worker
        mapping_data = {path: {"selected": data["selected"]}
                        for path, data in self.tree_data.items()
                        if data.get("item")} # Ensure item exists (is loaded)

        self.mapping_worker = MappingWorker(root_path, mapping_data)
        self.mapping_worker.finished.connect(self.on_mapping_finished)
        self.mapping_worker.status_update.connect(self._update_status) # Connect mapper status updates
        self.mapping_worker.start()


    def on_mapping_finished(self, output_path_or_error: str, success: bool):
        """Slot called when MappingWorker finishes."""
        self.generate_btn.setEnabled(True) # Re-enable button
        if success:
            output_path = output_path_or_error
            logging.info(f"Mapeo completado exitosamente: {output_path}")
            # Status already updated by worker's status_update signal
            reply = QMessageBox.information(self, "Mapeo Completado",
                                            f"Archivo de estructura generado en:\n{output_path}\n\n¿Abrir directorio contenedor?",
                                            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                            defaultButton=QMessageBox.StandardButton.Yes)

            if reply == QMessageBox.StandardButton.Yes:
                self.open_location(os.path.dirname(output_path))

        else:
            error_msg = output_path_or_error
            logging.error(f"Mapeo fallido. Razón: {error_msg}")
            # Status already updated by worker's status_update signal
            QMessageBox.critical(self, "Error de Mapeo", f"Ocurrió un error durante el mapeo:\n{error_msg}")
        self.mapping_worker = None # Clean up worker reference


    def open_location(self, path):
        """Opens the specified path in the default file explorer."""
        try:
            if not os.path.exists(path):
                logging.error(f"Cannot open location: Path does not exist - {path}")
                QMessageBox.warning(self, "Error", f"La ubicación no existe:\n{path}")
                return

            # Ensure path is absolute
            abs_path = os.path.abspath(path)
            logging.info(f"Attempting to open location: {abs_path}")

            if sys.platform == 'win32':
                # Use os.startfile on Windows
                os.startfile(abs_path)
            elif sys.platform == 'darwin':
                # Use 'open' command on macOS
                subprocess.Popen(['open', abs_path])
            else:
                # Use 'xdg-open' command on Linux/other Unix-like
                subprocess.Popen(['xdg-open', abs_path])
        except Exception as e:
            logging.error(f"No se pudo abrir la ubicación '{path}': {e}")
            QMessageBox.warning(self, "Error", f"No se pudo abrir la ubicación:\n{e}")


    def show_context_menu(self, position: QPoint):
        """Shows the context menu for a tree item."""
        item = self.tree.itemAt(position)
        if not item: return

        item_path = item.data(0, Qt.ItemDataRole.UserRole) # PyQt6 Enum
        if not item_path: # Don't show menu for placeholders or errors
            return

        menu = QMenu(self) # Parent menu to self

        # --- Selection Action ---
        is_selected = self.tree_data.get(item_path, {}).get("selected", True)
        toggle_action_text = "Deseleccionar (y descendientes)" if is_selected else "Seleccionar (y descendientes)"
        # Use QAction for better handling
        toggle_action = QAction(toggle_action_text, self)
        toggle_action.triggered.connect(lambda: self.toggle_item_selection(item, not is_selected, True) or self._update_preview())
        menu.addAction(toggle_action)

        menu.addSeparator()

        # --- Expand/Collapse Actions (if directory) ---
        if os.path.isdir(item_path):
            if not item.isExpanded():
                expand_action = QAction("Expandir", self)
                expand_action.triggered.connect(lambda: self.on_item_expanded_or_load(item)) # Use unified handler
                menu.addAction(expand_action)
            else:
                collapse_action = QAction("Colapsar", self)
                collapse_action.triggered.connect(lambda: item.setExpanded(False))
                menu.addAction(collapse_action)
            menu.addSeparator()

        # --- Open Location Action ---
        open_action = QAction("Abrir ubicación", self)
        dir_to_open = os.path.dirname(item_path) if not os.path.isdir(item_path) else item_path
        open_action.triggered.connect(lambda: self.open_location(dir_to_open))
        menu.addAction(open_action)

        # Execute menu at global position
        menu.exec(self.tree.mapToGlobal(position)) # Use exec() in PyQt6


    # --- Drag and Drop Event Handlers ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accepts the event if it contains a single folder URL."""
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            # Check for single, local, directory URL
            if len(urls) == 1 and urls[0].isLocalFile():
                path = urls[0].toLocalFile()
                if os.path.isdir(path):
                    event.acceptProposedAction()
                    logging.debug(f"Drag Enter accepted for folder: {path}")
                    return # Accepted, exit early
        # If conditions not met, ignore
        logging.debug("Drag Enter rejected (not a single folder)")
        event.ignore()


    # dragMoveEvent is often not needed unless providing custom visual feedback
    # def dragMoveEvent(self, event: QDragMoveEvent):
    #     event.acceptProposedAction()


    def dropEvent(self, event: QDropEvent):
        """Handles the dropped folder."""
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if len(urls) == 1 and urls[0].isLocalFile():
                path = urls[0].toLocalFile()
                if os.path.isdir(path):
                    logging.info(f"Folder dropped: {path}")
                    self.select_folder(path) # Call select_folder with the path
                    event.acceptProposedAction()
                    return # Accepted, exit early
        # If conditions not met, ignore
        logging.warning("Drop rejected (not a single folder)")
        event.ignore()


    # --- Close Event Handler ---
    def closeEvent(self, event):
        """Handles the main window close event."""
        # Optional: Add confirmation dialog or cleanup here if needed
        logging.info("Folder Mapper application closing.")
        # Terminate worker threads gracefully if they are running
        if self.loader_worker and self.loader_worker.isRunning():
             logging.info("Terminating directory loader worker...")
             self.loader_worker.quit() # Request termination
             self.loader_worker.wait(1000) # Wait max 1 sec
        if self.mapping_worker and self.mapping_worker.isRunning():
             logging.info("Terminating mapping worker...")
             self.mapping_worker.quit() # Request termination
             self.mapping_worker.wait(1000) # Wait max 1 sec

        event.accept() # Accept the close event


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée principal de l'application / Main application entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Ensure QApplication instance exists before any widgets
    app = QApplication(sys.argv)

    # Set application details (optional)
    app.setApplicationName("FolderMapper")
    app.setOrganizationName("YourNameOrCompany") # Optional

    # Create and show the main window
    main_window = EnhancedFolderMapper()
    # main_window.show() # Already called in init_ui

    # Start the application event loop
    sys.exit(app.exec())
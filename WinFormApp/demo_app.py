import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget,
    QFileDialog, QHBoxLayout, QProgressBar
)
from PySide6.QtGui import QPixmap, QWheelEvent, QMouseEvent, QPalette, QColor, QIcon
from PySide6.QtCore import Qt, QPoint, QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QMessageBox


class DetectionWorker(QObject):
    finished = Signal(str)   # path processed
    error = Signal(str)

    def __init__(self, paths: list[str], is_folder_mode: bool):
        super().__init__()
        self.paths = paths
        self.is_folder_mode = is_folder_mode

    @Slot()
    def run(self):
        try:
            from pathlib import Path
            from MesoDetect.meso_detect import meso_detect, meso_batch_detect

            if self.is_folder_mode:
                folder_path = Path(self.paths[0]).parent
                meso_batch_detect(folder_path, folder_path, enable_debug_mode=False)
            else:
                img_path = Path(self.paths[0])
                meso_detect(img_path, img_path.parent, enable_debug_mode=False)

            self.finished.emit("Done")
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.error.emit(str(e))


class ImageDropWidget(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.setAcceptDrops(True)

        # Hint label
        self.hint_label = QLabel("Click or Drop an Image Here", self)
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 16px;
                background-color: transparent;
            }
        """)
        self.hint_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def resizeEvent(self, event):
        # Center hint label
        self.hint_label.resize(self.size())
        super().resizeEvent(event)

    def show_hint(self, show: bool):
        self.hint_label.setVisible(show)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.parent_window.load_image_from_path(file_path)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open Image File", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            if file_path:
                self.parent_window.load_image_from_path(file_path)


class DetectionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MesoDetect")
        self.resize(1200, 700)
        self.setWindowIcon(QIcon("mainwindow_con.ico"))

        # === Central Widget and Layout ===
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        outer_layout = QHBoxLayout(central_widget)  # outermost layout
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.setSpacing(0)

        # === Main Content Container (holds image and buttons) ===
        main_content_container = QWidget()
        main_content_layout = QHBoxLayout(main_content_container)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(20)  # space between image and buttons
        main_content_layout.setAlignment(Qt.AlignCenter)

        # === Left Column: Image Viewer ===
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.image_container = ImageDropWidget(self)
        # Give the container a default minimum size so it shows up initially
        self.image_container.setMinimumSize(800, 600)
        self.image_container.setStyleSheet("""
            background-color: #2a2a2a;
            border: 2px dashed #888;
        """)
        self.image_container.setLayout(None)
        self.image_container.setAcceptDrops(True)

        self.image_label = ZoomableLabel(self)
        self.image_label.setParent(self.image_container)
        self.image_label.hide()

        left_layout.addWidget(self.image_container)
        left_column.setLayout(left_layout)

        # === Right Column: Buttons and Progress ===
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(15)

        # Buttons
        self.clear_button = QPushButton("Clear")
        self.process_button = QPushButton("Meso Detect")
        self.folder_button = QPushButton("Select Folder")

        # Connect signal
        self.folder_button.clicked.connect(self.select_folder)
        self.process_button.clicked.connect(self.start_detection_thread)

        button_style = """
            QPushButton {
                padding: 12px;
                font-size: 14px;
                min-width: 160px;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #444;
            }
            QPushButton:pressed {
                background-color: #333;
            }
        """
        self.clear_button.setStyleSheet(button_style)
        self.folder_button.setStyleSheet(button_style)
        self.process_button.setStyleSheet(button_style + "\nQPushButton:disabled { color: #777; }")

        right_layout.addWidget(self.clear_button)
        right_layout.addWidget(self.process_button)
        right_layout.addWidget(self.folder_button)


        # === Image Entry List ===
        from PySide6.QtWidgets import QScrollArea, QGroupBox, QFrame

        self.image_list_group = QGroupBox("Radar Images List")
        self.image_list_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        image_list_layout = QVBoxLayout(self.image_list_group)
        image_list_layout.setContentsMargins(5, 5, 5, 5)
        image_list_layout.setSpacing(5)

        # === Status Label for Processing ===
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #444; font-style: italic;")

        # Scrollable area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        self.image_list_widget = QWidget()
        self.image_list_layout = QVBoxLayout(self.image_list_widget)
        self.image_list_layout.setSpacing(4)
        self.image_list_layout.setAlignment(Qt.AlignTop)  # 👈 add this line
        self.image_list_widget.setLayout(self.image_list_layout)

        scroll_area.setWidget(self.image_list_widget)

        # Add to container
        image_list_layout.addWidget(scroll_area)
        right_layout.addWidget(self.image_list_group)
        right_layout.addWidget(self.status_label)

        # === Detection Result List ===
        self.result_list_group = QGroupBox("Detection Result")
        self.result_list_group.setStyleSheet("QGroupBox { font-weight: bold; }")

        result_list_layout = QVBoxLayout(self.result_list_group)
        result_list_layout.setContentsMargins(5, 5, 5, 5)
        result_list_layout.setSpacing(5)

        result_scroll_area = QScrollArea()
        result_scroll_area.setWidgetResizable(True)
        result_scroll_area.setFrameShape(QFrame.NoFrame)

        self.result_list_widget = QWidget()
        self.result_list_layout = QVBoxLayout(self.result_list_widget)
        self.result_list_layout.setSpacing(4)
        self.result_list_layout.setAlignment(Qt.AlignTop)
        self.result_list_widget.setLayout(self.result_list_layout)

        result_scroll_area.setWidget(self.result_list_widget)
        result_list_layout.addWidget(result_scroll_area)

        right_layout.addWidget(self.result_list_group)

        right_layout.addStretch()
        right_column.setLayout(right_layout)

        # === Add Left and Right to Main Content Layout ===
        main_content_layout.addWidget(left_column)
        main_content_layout.addWidget(right_column)

        # === Add Main Content to Outer Layout, Centered ===
        outer_layout.addStretch()
        outer_layout.addWidget(main_content_container)
        outer_layout.addStretch()

        # === Signals ===
        self.clear_button.clicked.connect(self.clear_image)

        # === Initial State ===
        self.zoom_factor = 1.0
        self.original_pixmap = None
        self.default_container_size = (800, 600)
        self.is_maximized = False
        self.image_aspect_ratio = None
        self.process_button.setEnabled(False)
        self.image_container.show_hint(True)
        self.loaded_image_paths = []  # <- new

    def on_detection_finished(self, message):
        print(f"[Done] {message}")
        self.status_label.setText("Radar image process complete.")
        self.process_button.setEnabled(True)  # Optional: re-enable if needed

    def on_detection_error(self, err):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Error", f"Detection failed:\n{err}")
        self.status_label.setText("Detection failed. See log for details.")
        self.process_button.setEnabled(True)

    def start_detection_thread(self):
        self.status_label.setText("Processing radar images...")
        # Disable button during processing
        self.process_button.setEnabled(False)

        # Determine mode
        is_folder_mode = len(self.loaded_image_paths) > 1
        input_paths = self.loaded_image_paths

        # Thread and worker
        self.thread = QThread()
        self.worker = DetectionWorker(input_paths, is_folder_mode)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_detection_finished)
        self.worker.error.connect(self.on_detection_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Start the thread
        self.thread.start()

    def load_image_from_path(self, file_path):
        if file_path:
            self.original_pixmap = QPixmap(file_path)
            self.process_button.setEnabled(True)
            self.current_image_path = file_path
            self.image_container.show_hint(False)

            self.image_label.show()  # ✅ Show label again when image is loaded

            img_size = self.original_pixmap.size()
            if img_size.width() == 760 and img_size.height() == 600:
                self.image_aspect_ratio = 760 / 600
            elif img_size.width() == 1024 and img_size.height() == 768:
                self.image_aspect_ratio = 1024 / 768
            else:
                self.image_aspect_ratio = None

            self.zoom_factor = self.calculate_initial_zoom()
            self.update_image()
            self.image_label.setCursor(Qt.OpenHandCursor)

        self.loaded_image_paths = [file_path]
        self.process_button.setEnabled(True)

        # After setting aspect ratio
        container_height = 600
        container_width = int(container_height * self.image_aspect_ratio)
        self.image_container.setMinimumSize(container_width, container_height)
        self.image_container.setMaximumSize(container_width, container_height)

        self.add_image_to_list(file_path)

    def add_image_to_list(self, file_path: str):
        import os
        from PySide6.QtWidgets import QPushButton, QLabel

        image_name = os.path.basename(file_path)
        timestamp = image_name.split("_")[4] if len(image_name.split("_")) > 4 else "unknown"

        entry_button = QPushButton(f"📡 {timestamp}")
        entry_button.setCheckable(True)
        entry_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 5px;
                border: 1px solid #888;
                border-radius: 3px;
            }
            QPushButton:checked {
                background-color: #def;
            }
        """)

        entry_content = QLabel(file_path)
        entry_content.setWordWrap(True)
        entry_content.setVisible(False)

        # Connect button click to show the image
        entry_button.clicked.connect(lambda checked, path=file_path: self.show_image_from_list(path))
        entry_button.clicked.connect(lambda: entry_content.setVisible(entry_button.isChecked()))

        self.image_list_layout.addWidget(entry_button)
        self.image_list_layout.addWidget(entry_content)

    def show_image_from_list(self, file_path: str):
        """Load and display the image when clicked from the list"""
        if file_path:
            self.original_pixmap = QPixmap(file_path)
            self.process_button.setEnabled(True)
            self.current_image_path = file_path
            self.image_container.show_hint(False)

            self.image_label.show()

            img_size = self.original_pixmap.size()
            if img_size.width() == 760 and img_size.height() == 600:
                self.image_aspect_ratio = 760 / 600
            elif img_size.width() == 1024 and img_size.height() == 768:
                self.image_aspect_ratio = 1024 / 768
            else:
                self.image_aspect_ratio = None

            self.zoom_factor = self.calculate_initial_zoom()
            self.update_image()
            self.image_label.setCursor(Qt.OpenHandCursor)

            # After setting aspect ratio
            container_height = 600
            container_width = int(container_height * self.image_aspect_ratio)
            self.image_container.setMinimumSize(container_width, container_height)
            self.image_container.setMaximumSize(container_width, container_height)

            self.populate_result_entries(file_path)

    def populate_result_entries(self, radar_img_path: str):
        print("populat result entries...")
        from PySide6.QtWidgets import QPushButton, QLabel
        from pathlib import Path

        # Clear previous entries
        while self.result_list_layout.count():
            item = self.result_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # ✅ Correctly get detection result folder path
        # get radar image name
        resolved_image_path = Path(radar_img_path).expanduser().resolve()
        image_name = resolved_image_path.as_posix().split("/")[-1].split(".")[0]
        detection_dir = Path(radar_img_path).parent / Path(image_name)
        print(f"[Debug] Looking for detection result folder: {detection_dir}")

        if not detection_dir.exists():
            print(f"[Debug] result directory not exist.")

        if not detection_dir.exists() or not detection_dir.is_dir():
            self.result_list_layout.addWidget(QLabel("No detection result folder found."))
            return

        result_images = list(detection_dir.glob("*.png"))

        if not result_images:
            self.result_list_layout.addWidget(QLabel("No mesocyclone detected."))
            return

        for img_path in result_images:
            entry_button = QPushButton(f"📈 {img_path.name}")
            entry_button.setCheckable(True)
            entry_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 5px;
                    border: 1px solid #888;
                    border-radius: 3px;
                }
                QPushButton:checked {
                    background-color: #cde;
                }
            """)
            entry_button.clicked.connect(lambda checked, p=img_path: self.show_result_image(str(p)))
            self.result_list_layout.addWidget(entry_button)

    def show_result_image(self, img_path: str):
        self.original_pixmap = QPixmap(img_path)
        self.zoom_factor = self.calculate_initial_zoom()
        self.update_image()
        self.image_label.setCursor(Qt.OpenHandCursor)
        self.image_label.show()
        self.image_container.show_hint(False)

    def calculate_initial_zoom(self):
        if not self.original_pixmap:
            return 1.0

        container_size = self.image_container.size()
        img_size = self.original_pixmap.size()

        zoom_w = container_size.width() / img_size.width()
        zoom_h = container_size.height() / img_size.height()

        return min(zoom_w, zoom_h)  # 👈 ensures entire image is visible

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            if self.isMaximized() and not self.is_maximized:
                self.is_maximized = True
                if self.original_pixmap:
                    self.zoom_factor = self.calculate_initial_zoom()
                    self.update_image()
            elif not self.isMaximized() and self.is_maximized:
                self.is_maximized = False
                # Optional: also reinit zoom when exiting maximized
                if self.original_pixmap:
                    self.zoom_factor = self.calculate_initial_zoom()
                    self.update_image()
        super().changeEvent(event)

    def adjust_container_size(self):
        if not hasattr(self, 'image_aspect_ratio') or self.image_aspect_ratio is None:
            # Let container fill available space
            self.image_container.setMinimumSize(100, 100)  # Small minimum size
            self.image_container.setMaximumSize(16777215, 16777215)  # Qt's default maximum
            return

        # Get available size from container
        available_size = self.image_container.size()
        if available_size.width() <= 0 or available_size.height() <= 0:
            return  # Not yet visible

        # Calculate size that maintains aspect ratio within available space
        new_width = min(available_size.width(), int(available_size.height() * self.image_aspect_ratio))
        new_height = min(available_size.height(), int(available_size.width() / self.image_aspect_ratio))

        # Update image label size and position
        self.update_image()

    def select_folder(self):
        from pathlib import Path

        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if not folder:
            return

        image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
        image_files = [
            str(p) for p in Path(folder).iterdir()
            if p.is_file() and p.suffix.lower() in image_extensions
        ]

        if not image_files:
            return

        self.reset_all()

        self.image_container.show_hint(False)
        self.loaded_image_paths = image_files
        self.process_button.setEnabled(True)

        for image_path in image_files:
            self.add_image_to_list(image_path)

        # Optionally display the first image
        self.original_pixmap = QPixmap(image_files[0])
        self.current_image_path = image_files[0]
        self.zoom_factor = self.calculate_initial_zoom()
        self.image_label.setPixmap(self.original_pixmap)
        self.image_label.setCursor(Qt.OpenHandCursor)
        self.image_label.show()
        self.update_image()

    def reset_all(self):
        self.original_pixmap = None
        self.process_button.setEnabled(False)
        self.zoom_factor = 1.0

        self.image_label.clear()
        self.image_label.setText("")
        self.status_label.setText("")
        self.image_label.unsetCursor()
        self.image_label.hide()

        self.image_container.show_hint(True)

        # ✅ Clear the image list entries
        while self.image_list_layout.count():
            item = self.image_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

            # ✅ Also clear detection result entries
        while self.result_list_layout.count():
            item = self.result_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()


    def clear_image(self):
        # Create a confirmation dialog
        reply = QMessageBox.question(
            self,
            'Confirm Clear',
            'Are you sure you want to clear all loaded images and detection results?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return
        self.reset_all()

    def update_image(self, center_pos=None):
        if not self.original_pixmap:
            return

        old_size = self.image_label.size()
        old_pos = self.image_label.pos()

        # Optional: resize container to match image aspect ratio
        aspect_ratio = self.original_pixmap.width() / self.original_pixmap.height()
        container_height = self.image_container.height()
        new_width = int(container_height * aspect_ratio)
        self.image_container.setFixedWidth(new_width)

        scaled_pixmap = self.original_pixmap.scaled(
            self.original_pixmap.size() * self.zoom_factor,
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())

        container_w, container_h = self.image_container.width(), self.image_container.height()
        label_w, label_h = scaled_pixmap.width(), scaled_pixmap.height()

        if center_pos:
            # Try to preserve zoom center
            delta_x = center_pos.x() - old_pos.x()
            delta_y = center_pos.y() - old_pos.y()

            scale_x = label_w / old_size.width()
            scale_y = label_h / old_size.height()

            new_x = center_pos.x() - int(delta_x * scale_x)
            new_y = center_pos.y() - int(delta_y * scale_y)
        else:
            # Default to centering
            new_x = (container_w - label_w) // 2
            new_y = (container_h - label_h) // 2

        # Clamp position
        if label_w <= container_w:
            new_x = (container_w - label_w) // 2
        else:
            new_x = max(container_w - label_w, min(0, new_x))

        if label_h <= container_h:
            new_y = (container_h - label_h) // 2
        else:
            new_y = max(container_h - label_h, min(0, new_y))

        self.image_label.move(new_x, new_y)


class ZoomableLabel(QLabel):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.setMouseTracking(True)
        self.setCursor(Qt.OpenHandCursor)
        self.dragging = False
        self.last_mouse_pos = QPoint()

    def wheelEvent(self, event: QWheelEvent):
        if not self.pixmap():
            return

        parent_window = self.parent_window
        old_zoom = parent_window.zoom_factor
        zoom_in = event.angleDelta().y() > 0
        new_zoom = old_zoom * (1.25 if zoom_in else 0.8)

        # 👇 Calculate minimum zoom to fit at least one axis
        pixmap_size = parent_window.original_pixmap.size()
        container_size = parent_window.image_container.size()
        min_zoom_w = container_size.width() / pixmap_size.width()
        min_zoom_h = container_size.height() / pixmap_size.height()
        min_zoom = max(min_zoom_w, min_zoom_h)  # prevent showing gaps

        # Clamp zoom level
        new_zoom = max(min_zoom, min(10.0, new_zoom))

        if abs(new_zoom - old_zoom) >= 0.01:
            # Get position of mouse relative to container
            global_mouse = self.mapToGlobal(event.position().toPoint())
            container_mouse = self.parent().mapFromGlobal(global_mouse)

            parent_window.zoom_factor = new_zoom
            parent_window.update_image(center_pos=container_mouse)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.setCursor(Qt.ClosedHandCursor)
            self.last_mouse_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self.last_mouse_pos
            self.last_mouse_pos = current_pos

            new_pos = self.pos() + delta

            # Get container and image size
            container = self.parent()
            container_w, container_h = container.width(), container.height()
            image_w, image_h = self.width(), self.height()

            # Restrict movement: ensure image covers the container at all times
            min_x = min(0, container_w - image_w)
            max_x = max(0, container_w - image_w)
            min_y = min(0, container_h - image_h)
            max_y = max(0, container_h - image_h)

            clamped_x = max(min_x, min(new_pos.x(), 0))
            clamped_y = max(min_y, min(new_pos.y(), 0))

            self.move(clamped_x, clamped_y)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(Qt.OpenHandCursor)


def set_light_theme(app):
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#ffffff"))
    palette.setColor(QPalette.WindowText, Qt.black)
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#f6f6f6"))
    palette.setColor(QPalette.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ToolTipText, Qt.black)
    palette.setColor(QPalette.Text, Qt.black)
    palette.setColor(QPalette.Button, QColor("#e1e1e1"))
    palette.setColor(QPalette.ButtonText, Qt.black)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Highlight, QColor("#d0d0ff"))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    app.setStyle("Fusion")  # use platform-independent look


if __name__ == "__main__":
    app = QApplication([])
    set_light_theme(app)
    window = DetectionWindow()
    window.show()
    app.exec()
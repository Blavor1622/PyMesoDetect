from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget,
    QFileDialog, QScrollArea, QHBoxLayout, QProgressDialog
)
import tempfile
from PySide6.QtGui import QPixmap, QWheelEvent, QMouseEvent
from PySide6.QtCore import Qt, QPointF, QPoint
from PySide6.QtGui import QIcon  # Add this with your other imports
from MesoDetect.meso_detect import meso_detect

class MyLearnWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MesoDetect")
        self.resize(1200, 700)
        self.setWindowIcon(QIcon("mainwindow_con.ico"))

        # Central widget and layout - now using QHBoxLayout for columns
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)  # Changed to horizontal layout
        main_layout.setContentsMargins(10, 10, 10, 10)  # Add some margin around edges

        # Left column (image container) - will take most space
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)  # No extra margins

        # Image container - now fills available space
        self.image_container = QWidget()
        self.image_container.setStyleSheet("background-color: #222; border: 1px solid #444;")
        self.image_container.setLayout(None)  # allow manual positioning

        # Image label (moveable within container)
        self.image_label = ZoomableLabel(self)
        self.image_label.setParent(self.image_container)

        left_layout.addWidget(self.image_container)
        main_layout.addWidget(left_column, stretch=4)  # Left column takes 4/5 of space

        # Right column (buttons) - thinner rectangle
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(10, 10, 10, 10)  # Add some padding
        right_layout.setSpacing(15)  # Add spacing between widgets

        # Buttons - now in vertical layout
        self.open_button = QPushButton("Open Image")
        self.clear_button = QPushButton("Clear Image")
        self.process_button = QPushButton("Process Image")  # New processing button

        # Style buttons
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
        self.open_button.setStyleSheet(button_style)
        self.clear_button.setStyleSheet(button_style)
        self.process_button.setStyleSheet(button_style.replace("}", "}\nQPushButton:disabled { color: #777; }"))

        # Add buttons to layout
        right_layout.addWidget(self.open_button)
        right_layout.addWidget(self.clear_button)
        right_layout.addWidget(self.process_button)

        # Add status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #aaa;
                font-size: 12px;
                padding: 8px;
                background-color: #333;
                border-radius: 4px;
            }
        """)
        right_layout.addWidget(self.status_label)

        # Add stretch to push everything up
        right_layout.addStretch()

        # Add right column to main layout
        main_layout.addWidget(right_column, stretch=1)  # Right column takes 1/5 of space

        # Connections
        self.open_button.clicked.connect(self.open_image)
        self.clear_button.clicked.connect(self.clear_image)
        self.process_button.clicked.connect(self.process_image)

        # State
        self.zoom_factor = 1.0
        self.original_pixmap = None
        self.default_container_size = (800, 600)  # Adjusted default size
        self.is_maximized = False
        self.image_aspect_ratio = None

        # Initially disable process button until image is loaded
        self.process_button.setEnabled(False)

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image File", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.original_pixmap = QPixmap(file_path)
            self.process_button.setEnabled(True)  # Enable the process button
            self.current_image_path = file_path  # Store the original path
            # Detect image type and set aspect ratio
            img_size = self.original_pixmap.size()
            if img_size.width() == 760 and img_size.height() == 600:
                self.image_aspect_ratio = 760 / 600
            elif img_size.width() == 1024 and img_size.height() == 768:
                self.image_aspect_ratio = 1024 / 768
            else:
                self.image_aspect_ratio = None

            # Calculate initial zoom to fit
            self.zoom_factor = self.calculate_initial_zoom()
            self.update_image()
            self.image_label.setCursor(Qt.OpenHandCursor)

    def process_image(self):
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            self.status_label.setText("No image loaded to process")
            return

        # Setup progress dialog
        progress = QProgressDialog("Processing image...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        try:
            self.status_label.setText("Processing...")
            self.setEnabled(False)  # Disable UI during processing
            QApplication.processEvents()  # Update UI immediately

            # Get project root directory for output
            import os
            project_root = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(project_root, "meso_output")
            os.makedirs(output_dir, exist_ok=True)

            # Process the original image directly
            result_path = meso_detect(
                img_path=self.current_image_path,  # Use the original path
                output_folder_path=output_dir,
                station_num="",
                enable_default_config=True,
                enable_debug_mode=False
            )

            if result_path and os.path.exists(result_path):
                # Load and display the result
                self.original_pixmap = QPixmap(result_path)
                self.zoom_factor = self.calculate_initial_zoom()
                self.update_image()
                self.status_label.setText("Processing complete")
            else:
                self.status_label.setText("Processing failed")

        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            print(f"Error during processing: {str(e)}")

        finally:
            progress.close()
            self.setEnabled(True)  # Re-enable UI

    def calculate_initial_zoom(self):
        if not self.original_pixmap:
            return 1.0

        container_size = self.image_container.size()
        img_size = self.original_pixmap.size()

        zoom_w = container_size.width() / img_size.width()
        zoom_h = container_size.height() / img_size.height()

        return min(zoom_w, zoom_h)

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            if self.isMaximized() and not self.is_maximized:
                self.is_maximized = True
            elif not self.isMaximized() and self.is_maximized:
                self.is_maximized = False

            if self.original_pixmap:
                # Let the layout handle container sizing, just update image
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

    def clear_image(self):
        self.original_pixmap = None
        self.process_button.setEnabled(False)  # Disable the process button
        self.zoom_factor = 1.0
        self.image_label.clear()
        self.image_label.setText("No image loaded")
        self.image_label.unsetCursor()

    def update_image(self, center_pos=None):
        if not self.original_pixmap:
            return

        old_size = self.image_label.size()
        old_pos = self.image_label.pos()

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


if __name__ == "__main__":
    app = QApplication([])
    window = MyLearnWindow()
    window.show()
    app.exec()
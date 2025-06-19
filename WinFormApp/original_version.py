from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget,
    QFileDialog, QScrollArea, QHBoxLayout
)
from PySide6.QtGui import QPixmap, QWheelEvent, QMouseEvent
from PySide6.QtCore import Qt, QPointF, QPoint
from PySide6.QtGui import QIcon  # Add this with your other imports


class MyLearnWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MesoDetect")
        self.resize(1200, 700)
        self.setWindowIcon(QIcon("E:/MyPrograms/DMD/WinFormApp/mainwindow_con.ico"))  # or "app_icon.png"

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Fixed image display area (mask/view)
        self.image_container = QWidget()
        self.image_container.setFixedSize(600, 400)
        self.image_container.setStyleSheet("background-color: #222; border: 1px solid #444;")
        self.image_container.setLayout(None)  # allow manual positioning
        main_layout.addWidget(self.image_container, alignment=Qt.AlignCenter)

        # Image label (moveable within container)
        self.image_label = ZoomableLabel(self)
        self.image_label.setParent(self.image_container)

        # Buttons
        self.open_button = QPushButton("Open Image")
        self.clear_button = QPushButton("Clear Image")
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.clear_button)
        main_layout.addLayout(button_layout)

        # Connections
        self.open_button.clicked.connect(self.open_image)
        self.clear_button.clicked.connect(self.clear_image)

        # State
        self.zoom_factor = 1.0
        self.original_pixmap = None
        # ... existing code ...
        self.default_container_size = (600, 400)  # Keep your original default
        self.is_maximized = False  # Track window state
        self.image_aspect_ratio = None  # Will store image ratio
        # ... rest of your init ...

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image File", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.original_pixmap = QPixmap(file_path)
            self.zoom_factor = 1.0

            # Detect image type and set aspect ratio
            img_size = self.original_pixmap.size()
            if img_size.width() == 760 and img_size.height() == 600:
                self.image_aspect_ratio = 760 / 600
            elif img_size.width() == 1024 and img_size.height() == 768:
                self.image_aspect_ratio = 1024 / 768
            else:
                self.image_aspect_ratio = None  # Keep default container size

            self.adjust_container_size()  # New method we'll add next
            self.update_image()
            self.image_label.setCursor(Qt.OpenHandCursor)

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            # Update maximized state
            if self.isMaximized() and not self.is_maximized:
                self.is_maximized = True
            elif not self.isMaximized() and self.is_maximized:
                self.is_maximized = False

            # Adjust container if we have an image loaded
            if self.original_pixmap:
                self.adjust_container_size()
                self.update_image()

        super().changeEvent(event)

    def adjust_container_size(self):
        if not hasattr(self, 'image_aspect_ratio') or self.image_aspect_ratio is None:
            # Use default size if no specific ratio needed
            self.image_container.setFixedSize(*self.default_container_size)
            return

        # Calculate available space
        if self.is_maximized:
            max_width = self.width() - 100  # Leave some margin
            max_height = self.height() - 150
        else:
            max_width, max_height = self.default_container_size

        # Calculate size that maintains aspect ratio
        new_width = min(max_width, int(max_height * self.image_aspect_ratio))
        new_height = min(max_height, int(max_width / self.image_aspect_ratio))

        self.image_container.setFixedSize(new_width, new_height)

    def clear_image(self):
        self.original_pixmap = None
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
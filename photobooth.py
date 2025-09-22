# Full PhotoBooth App with All Features in One File (Refactored with Classes)

import sys
import cv2
import time
import os
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QScrollArea,
    QGridLayout, QMessageBox, QHBoxLayout, QFrame, QSizePolicy, QStackedLayout
)
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QBrush, QFont
from PyQt5.QtCore import QTimer, pyqtSignal, Qt, QRect, QPropertyAnimation, pyqtProperty, QEasingCurve, QCoreApplication, QEventLoop, QSize

if not os.path.exists("CapturedPhotos"):
    os.makedirs("CapturedPhotos")

class SlideToggle(QFrame):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._position = 2
        self.setFixedSize(60, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.animation = QPropertyAnimation(self, b"position", self)
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self.animation.setStartValue(self._position)
        self.animation.setEndValue(32 if self._checked else 2)
        self.animation.start()
        self.toggled.emit(self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bg_color = QColor("#2c3e50") if self._checked else QColor("#f1c40f")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(QRect(self._position, 2, 24, 24))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor("black"))
        painter.drawText(8, 19, "☀") if not self._checked else painter.drawText(34, 19, "🌙")

    def isChecked(self):
        return self._checked

    def setChecked(self, value):
        self._checked = value
        self._position = 32 if value else 2
        self.update()

    def get_position(self):
        return self._position

    def set_position(self, pos):
        self._position = pos
        self.update()

    position = pyqtProperty(int, get_position, set_position)

class ClickableLabel(QLabel):
    clicked = pyqtSignal(str)

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path

    def mousePressEvent(self, event):
        self.clicked.emit(self.image_path)


class PhotoBooth(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Booth App")
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)

        self.capture = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        self.selected_filter = "Normal"
        self.countdown_enabled = True
        self.current_frame = None

        # Webcam preview
        self.image_label = QLabel()
        self.image_label.setFixedSize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border-radius: 12px; border: 2px solid #666;")
        self.image_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Countdown overlay label
        self.countdown_label = QLabel("", self.image_label)
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet("""
            QLabel {
                font-size: 72px;
                color: red;
                background-color: rgba(0, 0, 0, 100);
            }
        """)
        self.countdown_label.setGeometry(0, 0, 640, 480)
        self.countdown_label.hide()

        # Countdown toggle button
        self.countdown_button = QPushButton("🕒")
        self.countdown_button.setFixedSize(40, 40)
        self.countdown_button.clicked.connect(self.toggle_countdown)
        self.update_countdown_button_style()

        # Webcam layout
        webcam_layout = QVBoxLayout()
        top_row = QHBoxLayout()
        top_row.addStretch()
        top_row.addWidget(self.countdown_button)
        webcam_layout.addLayout(top_row)
        webcam_layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        webcam_container = QWidget()
        webcam_container.setLayout(webcam_layout)

        # Filter buttons
        filter_names = ["Normal", "Black & White", "Sepia", "Invert", "CoolTone", "WarmTone", "Sketch", "Paint"]
        filter_emojis = ["👁️", "⚫", "🌅", "💫", "❄️", "🔥", "✏️", "🎨"]
        filter_buttons_layout = QHBoxLayout()

        for name, emoji in zip(filter_names, filter_emojis):
            btn = QPushButton(emoji)
            btn.setFixedSize(40, 40)
            btn.setToolTip(name)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 18px;
                    border-radius: 20px;
                    background-color: #444;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)
            btn.clicked.connect(self.make_filter_callback(name))
            filter_buttons_layout.addWidget(btn)

        filter_container = QWidget()
        filter_container.setLayout(filter_buttons_layout)

        # Capture button
        self.capture_button = QPushButton("📸 Capture Photo")
        self.capture_button.clicked.connect(self.capture_photo)

        # Thumbnail preview
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(160, 120)

        # Gallery button
        self.gallery_button = QPushButton("🖼️ Open Gallery")
        self.gallery_button.clicked.connect(self.open_gallery_window)

        # Theme toggle (SlideToggle assumed to be defined elsewhere)
        self.theme_toggle = SlideToggle()
        self.theme_toggle.toggled.connect(self.switch_theme)

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(webcam_container)
        layout.addWidget(filter_container, alignment=Qt.AlignCenter)
        layout.addWidget(self.capture_button, alignment=Qt.AlignCenter)
        layout.addWidget(QLabel("📸 Last Photo Preview:"), alignment=Qt.AlignCenter)
        layout.addWidget(self.thumbnail_label, alignment=Qt.AlignCenter)

        footer = QHBoxLayout()
        footer.addWidget(self.gallery_button)
        footer.addStretch()
        footer.addWidget(self.theme_toggle)
        layout.addLayout(footer)

        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        self.setLayout(layout)

        # Set default theme
        self.setStyleSheet(self.dark_style())
        self.theme_toggle.setChecked(True)

    def update_frame(self):
        ret, frame = self.capture.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        self.current_frame = self.apply_filter(frame)
        rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.image_label.setPixmap(pixmap)

    def make_filter_callback(self, name):
        def callback():
            self.selected_filter = name
        return callback

    def apply_filter(self, frame):
        if self.selected_filter == "Black & White":
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif self.selected_filter == "Sepia":
            kernel = np.array([[0.272, 0.534, 0.131],
                               [0.349, 0.686, 0.168],
                               [0.393, 0.769, 0.189]])
            sepia = cv2.transform(frame, kernel)
            return np.clip(sepia, 0, 255).astype(np.uint8)
        elif self.selected_filter == "Invert":
            return cv2.bitwise_not(frame)
        elif self.selected_filter == "CoolTone":
            b, g, r = cv2.split(frame)
            b = cv2.add(b, 30)
            return cv2.merge((b, g, r))
        elif self.selected_filter == "WarmTone":
            b, g, r = cv2.split(frame)
            r = cv2.add(r, 30)
            return cv2.merge((b, g, r))
        elif self.selected_filter == "Sketch":
            gray_sketch, _ = cv2.pencilSketch(frame, sigma_s=100, sigma_r=0.04, shade_factor=0.02)
            return gray_sketch
        elif self.selected_filter == "Paint":
            return cv2.stylization(frame, sigma_s=60, sigma_r=0.45)
        return frame

    def capture_photo(self):
        if self.countdown_enabled:
            self.show_countdown(3)
        else:
            self.save_current_frame()

    def show_countdown(self, seconds=3):
        self.countdown_label.show()

        def update_count(i):
            if i == 0:
                self.countdown_label.hide()
                self.save_current_frame()
            else:
                self.countdown_label.setText(str(i))
                QTimer.singleShot(1000, lambda: update_count(i - 1))

        update_count(seconds)

    def save_current_frame(self):
        if self.current_frame is None:
            return
        os.makedirs("CapturedPhotos", exist_ok=True)
        filename = f"photo_{int(time.time())}.png"
        path = os.path.join("CapturedPhotos", filename)
        cv2.imwrite(path, self.current_frame)
        self.update_thumbnail(path)

    def update_thumbnail(self, path):
        pixmap = QPixmap(path).scaled(160, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.thumbnail_label.setPixmap(pixmap)

    def toggle_countdown(self):
        self.countdown_enabled = not self.countdown_enabled
        self.update_countdown_button_style()

    def update_countdown_button_style(self):
        if self.countdown_enabled:
            self.countdown_button.setStyleSheet("background-color: green; color: white; font-size: 18px;")
        else:
            self.countdown_button.setStyleSheet("background-color: gray; color: white; font-size: 18px;")

    def open_gallery_window(self):
        self.gallery = GalleryWindow()
        self.gallery.show()

    def switch_theme(self, dark):
        if dark:
            self.setStyleSheet(self.dark_style())
        else:
            self.setStyleSheet(self.light_style())

    def dark_style(self):
        return """
            QWidget {
                background-color: #121212;
                color: white;
            }
            QPushButton {
                background-color: #333;
                color: white;
                border-radius: 5px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """

    def light_style(self):
        return """
            QWidget {
                background-color: #f0f0f0;
                color: black;
            }
            QPushButton {
                background-color: #ccc;
                color: black;
                border-radius: 5px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #bbb;
            }
        """



class GalleryWindow(QWidget):
    def __init__(self, folder_path="CapturedPhotos"):
        super().__init__()
        self.setWindowTitle("🖼️ Gallery")
        self.resize(800, 600)
        self.setMinimumSize(600, 400)

        self.folder_path = os.path.abspath(folder_path)
        os.makedirs(self.folder_path, exist_ok=True)

        self.valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
        self.images = []

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_widget.setLayout(self.grid_layout)
        self.scroll.setWidget(self.grid_widget)

        self.slideshow_btn = QPushButton("▶️ Start Slideshow")
        self.slideshow_btn.clicked.connect(self.start_slideshow)
        self.slideshow_btn.setStyleSheet("font-size: 14px; padding: 6px; background-color: #444; color: white;")

        layout = QVBoxLayout()
        layout.addWidget(self.slideshow_btn)
        layout.addWidget(self.scroll)
        self.setLayout(layout)

        self.load_images()

    def load_images(self):
        self.images = sorted(
            [os.path.join(self.folder_path, f) for f in os.listdir(self.folder_path) if f.lower().endswith(self.valid_exts)],
            reverse=True
        )
        self.render_grid()

    def render_grid(self):
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if not self.images:
            label = QLabel("No images found in gallery.")
            label.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(label, 0, 0)
            return

        available_width = self.width() - 60
        thumb_width = 180
        columns = max(1, available_width // thumb_width)

        for idx, img_file in enumerate(self.images):
            thumb = QLabel()
            thumb.setPixmap(QPixmap(img_file).scaled(160, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            thumb.setCursor(Qt.PointingHandCursor)
            thumb.mousePressEvent = lambda event, path=img_file: self.open_full_image(path)

            vbox = QVBoxLayout()
            vbox.addWidget(thumb)

            container = QWidget()
            container.setLayout(vbox)

            row = idx // columns
            col = idx % columns
            self.grid_layout.addWidget(container, row, col)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.render_grid()

    def open_full_image(self, path):
        if path in self.images:
            index = self.images.index(path)
        else:
            index = 0
        self.viewer = ImageViewer(self.images, start_index=index, refresh_callback=self.load_images)
        self.viewer.show()

    def delete_and_close(self, path, window):
        reply = QMessageBox.question(window, "Delete", f"Delete {os.path.basename(path)}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            os.remove(path)
            window.close()
            self.load_images()

    def delete_image(self, path):
        reply = QMessageBox.question(self, "Delete", f"Delete {os.path.basename(path)}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            os.remove(path)
            self.load_images()

    def start_slideshow(self):
        if not self.images:
            QMessageBox.information(self, "Slideshow", "No images found to display.")
            return

        self.viewer = ImageViewer(self.images, start_index=0, refresh_callback=self.load_images)
        self.viewer.toggle_slideshow()  # Start slideshow immediately
        self.viewer.showFullScreen()



class ImageViewer(QWidget):
    def __init__(self, image_paths, start_index=0, refresh_callback=None):
        super().__init__()
        self.setWindowTitle("🗾️ Full Image Viewer")
        self.setGeometry(100, 100, 1000, 800)
        self.setFocusPolicy(Qt.StrongFocus)  # Accept key events

        self.image_paths = image_paths
        self.current_index = start_index
        self.refresh_callback = refresh_callback
        self.slideshow_running = False

        self.slideshow_timer = QTimer()
        self.slideshow_timer.timeout.connect(self.next_image)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)

        # Buttons
        self.prev_btn = QPushButton("⬅️ Prev")
        self.next_btn = QPushButton("Next ➡️")
        self.slideshow_btn = QPushButton("▶️ Start Slideshow")
        self.del_btn = QPushButton("🗑 Delete This")

        self.prev_btn.clicked.connect(self.prev_image)
        self.next_btn.clicked.connect(self.next_image)
        self.slideshow_btn.clicked.connect(self.toggle_slideshow)
        self.del_btn.clicked.connect(self.delete_current)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.prev_btn)
        btn_layout.addWidget(self.next_btn)
        btn_layout.addWidget(self.slideshow_btn)
        btn_layout.addWidget(self.del_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()  # Ensure widget has focus on show
        self.update_view()

    def update_view(self):
        if not self.image_paths:
            self.close()
            return

        path = self.image_paths[self.current_index]
        pixmap = QPixmap(path)

        if not pixmap or pixmap.isNull():
            self.label.setText("❌ Failed to load image.")
            return
        target_size = self.label.size()
        if target_size.width() < 10 or target_size.height() < 10:
            target_size = QSize(800, 600)

        scaled = pixmap.scaled(
            target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_view()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Right:
            self.next_image()
        elif event.key() == Qt.Key_Left:
            self.prev_image()
        elif event.key() == Qt.Key_Delete:
            self.delete_current()
        elif event.key() == Qt.Key_Escape:
            self.close()

    def next_image(self):
        if not self.image_paths:
            return
        self.current_index = (self.current_index + 1) % len(self.image_paths)
        self.update_view()

    def prev_image(self):
        if not self.image_paths:
            return
        self.current_index = (self.current_index - 1 + len(self.image_paths)) % len(self.image_paths)
        self.update_view()

    def toggle_slideshow(self):
        if self.slideshow_running:
            self.slideshow_timer.stop()
            self.slideshow_btn.setText("▶️ Start Slideshow")
        else:
            self.slideshow_timer.start(2000)
            self.slideshow_btn.setText("⏸ Pause Slideshow")
        self.slideshow_running = not self.slideshow_running

    def delete_current(self):
        path = self.image_paths[self.current_index]
        reply = QMessageBox.question(self, "Delete", f"Delete {os.path.basename(path)}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            os.remove(path)
            self.image_paths.pop(self.current_index)
            if self.refresh_callback:
                self.refresh_callback()
            if self.current_index >= len(self.image_paths):
                self.current_index = max(0, len(self.image_paths) - 1)
            self.update_view()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    booth = PhotoBooth()
    booth.show()
    sys.exit(app.exec_())
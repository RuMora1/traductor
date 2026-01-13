import sys
import logging
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPoint, QSize, QEvent, QTimer, QRunnable, QThreadPool, pyqtSlot
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QFontDatabase
from dxcam import create as dxcam_create
import cv2

import styles


class ImageSaver(QRunnable):
    def __init__(self, frame, folder: str = "screenshots"):
        super().__init__()
        self.frame = frame
        self.folder = Path(folder)

    @pyqtSlot()
    def run(self):
        try:
            self.folder.mkdir(exist_ok=True)
            filename = self.folder / f"captura_{datetime.now():%Y%m%d_%H%M%S}.png"
            cv2.imwrite(str(filename), self.frame)
            logging.info(f"Imagen guardada: {filename}")
        except Exception as e:
            logging.exception("Error guardando imagen")


class TintedPanel(QWidget):
    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self.color = color
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        brush = QBrush(self.color)
        pen = QPen(QColor(255, 255, 255, 220))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(brush)
        # Dibujar rectángulo con esquinas redondeadas
        rect = self.rect()
        painter.drawRoundedRect(rect, 12, 12)


class ResizeHandle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self._drag_start = None
        self._start_size = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        brush = QBrush(QColor(255, 255, 255, 120))
        pen = QPen(QColor(255, 255, 255, 150))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(brush)
        rect = self.rect()
        painter.drawRoundedRect(rect, 4, 4)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            w = self.window().width()
            h = self.window().height()
            self._start_size = (w, h)
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_start and event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_start
            new_w = max(self.window().minimumWidth(), self._start_size[0] + delta.x())
            new_h = max(self.window().minimumHeight(), self._start_size[1] + delta.y())
            self.window().resize(new_w, new_h)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        self._start_size = None
        super().mouseReleaseEvent(event)


class CaptureWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Captura de Pantalla con dxcam")
        self.setGeometry(100, 100, 600, 200)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint)
        self.setMinimumSize(220, 140)
        self.setWindowOpacity(1.0)
        self.setStyleSheet("QMainWindow { background: transparent; }")

        # Crear el botón de captura
        self.capture_button = QPushButton("Captura", self)

        # Fuente explícita usada para botones (con fallback)
        family = styles.DEFAULT_FONT_FAMILY
        if family not in QFontDatabase.families():
            family = QFont().defaultFamily()
        self.button_font = QFont(family, 14)
        self.small_button_font = QFont(family, 10)
        self.capture_button.setStyleSheet(styles.BTN_MAIN)
        self.capture_button.setFont(self.button_font)
        self.capture_button.clicked.connect(self.on_capture_clicked)

        window_layout = QVBoxLayout()
        window_layout.setContentsMargins(8, 8, 8, 8)

        # Texto informativo dentro de la ventana
        self.info_label = QLabel("Selecciona el texto para traducir.")
        self.info_label.setStyleSheet("color: white; background: transparent;")

        # Fuente explícita para el texto informativo
        self.label_font = QFont(family, 12)
        self.info_label.setFont(self.label_font)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        window_layout.addWidget(self.info_label)
        window_layout.addStretch()

        panel = TintedPanel(styles.PANEL_BG)
        root_layout = QVBoxLayout(panel)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addLayout(window_layout)
        self.setCentralWidget(panel)
        self._create_button_window()
        self._create_title_window()
        
        # resize handle
        self._create_resize_handle(panel)
        self._drag_position = None

        # Thread pool for background tasks and logging
        self.thread_pool = QThreadPool()
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

        self.camera = dxcam_create(output_color="BGR")

    def on_capture_clicked(self):
        # Calculate region before hiding the window
        try:
            left, top, right, bottom = self._capture_region_over_window()
            # Hide UI overlays first
            was_visible = self.isVisible()
            if was_visible:
                self.hide()
                if hasattr(self, 'button_window'):
                    self.button_window.hide()
                if hasattr(self, 'title_window'):
                    self.title_window.hide()
                QApplication.processEvents()

            # Use a short timer to allow the compositor to finish
            QTimer.singleShot(40, lambda: self._perform_capture(left, top, right, bottom, was_visible))
        except Exception:
            logging.exception("Error inicio captura")

    def _perform_capture(self, left: int, top: int, right: int, bottom: int, was_visible: bool):
        try:
            # Choose the screen that contains the window center, fallback to primary
            center = QPoint((left + right) // 2, (top + bottom) // 2)
            screen = QApplication.screenAt(center) or QApplication.primaryScreen()
            geom = screen.geometry()
            # Clamp to screen bounds
            right = min(right, geom.x() + geom.width())
            bottom = min(bottom, geom.y() + geom.height())
            left = max(left, geom.x())
            top = max(top, geom.y())

            frame = self.camera.grab(region=(left, top, right, bottom))

            if frame is not None:
                saver = ImageSaver(frame)
                self.thread_pool.start(saver)
                logging.info("Captura realizada y delegada al guardado en background.")
            else:
                logging.warning("Frame vacío durante la captura")
        except Exception:
            logging.exception("Error durante _perform_capture")
        finally:
            # Restore UI overlays
            if was_visible:
                self.show()
                if hasattr(self, 'button_window'):
                    self.button_window.show()
                if hasattr(self, 'title_window'):
                    self.title_window.show()
                QApplication.processEvents()

    def _capture_region_over_window(self):
        global_pos = self.mapToGlobal(QPoint(0, 0))
        width = self.width()
        height = self.height()
        return (global_pos.x(), global_pos.y(), global_pos.x() + width, global_pos.y() + height)

    def _create_button_window(self):
        self.button_window = QWidget(self, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.button_window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.capture_button)
        self.button_window.setLayout(button_layout)
        self.button_window.setStyleSheet("background: rgba(0,0,0,0.5); border-radius: 10px;")
        button_size = self.capture_button.sizeHint()
        self.button_window.setFixedSize(button_size.width() + 32, button_size.height() + 24)
        self._position_button_window()

    def _create_title_window(self):
        self.title_window = QWidget(self, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.title_window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QHBoxLayout(self.title_window)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        self.minimize_button = QPushButton("–")
        self.close_button = QPushButton("×")
        for btn in (self.minimize_button, self.close_button):
            btn.setFixedSize(28, 28)
            btn.setFlat(True)
            btn.setStyleSheet(styles.BTN_TITLE)
            btn.setFont(self.small_button_font)
        self.minimize_button.clicked.connect(self.showMinimized)
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.close_button)
        self.title_window.setStyleSheet("background: rgba(0,0,0,130); border-radius: 6px; border: 1px solid rgba(255,255,255,0.15);")
        self._position_title_window()

    def _create_resize_handle(self, parent):
        self.resize_handle = ResizeHandle(parent)
        self._position_resize_handle()

    def _position_resize_handle(self):
        if not hasattr(self, 'resize_handle'):
            return
        panel = self.centralWidget()
        handle = self.resize_handle
        x = panel.width() - handle.width() - 8
        y = panel.height() - handle.height() - 8
        handle.move(x, y)

    def _position_title_window(self):
        if not hasattr(self, 'title_window'):
            return
        geom = self.frameGeometry()
        btn_size = self.title_window.sizeHint()
        x = geom.x() + geom.width() - btn_size.width() - 2
        y = geom.y() - btn_size.height() + 2
        self.title_window.move(x, y)

    def _position_button_window(self):
        if not hasattr(self, 'button_window'):
            return
        geom = self.frameGeometry()
        btn_size = self.button_window.size()
        x = geom.x() + geom.width() - 2
        y = geom.y() + max(0, (geom.height() - btn_size.height()) // 2)
        self.button_window.move(x, y)

    def moveEvent(self, event):
        super().moveEvent(event)
        self._position_button_window()
        self._position_title_window()
        self._position_resize_handle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_button_window()
        self._position_title_window()
        self._position_resize_handle()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'button_window'):
            self.button_window.show()
        if hasattr(self, 'title_window'):
            self.title_window.show()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            minimized = bool(self.windowState() & Qt.WindowState.WindowMinimized)
            if hasattr(self, 'button_window'):
                self.button_window.setVisible(not minimized)
            if hasattr(self, 'title_window'):
                self.title_window.setVisible(not minimized)

    def closeEvent(self, event):
        if hasattr(self, 'button_window'):
            self.button_window.close()
        if hasattr(self, 'title_window'):
            self.title_window.close()
        super().closeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_position is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_position = None
        super().mouseReleaseEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CaptureWindow()
    window.show()
    sys.exit(app.exec())
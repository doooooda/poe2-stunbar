import sys
import numpy as np
import cv2
from collections import deque
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QImage, QPixmap, QPainter, QFont, QColor
from mss import mss
import pyautogui

class StunBarOverlay(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.output_width = 400
        self.output_height = 80
        self.resize(self.output_width, self.output_height)

        self.dragging = False
        self.offset = QPoint()

        screen_width, screen_height = pyautogui.size()

        # === Full bar display region
        self.display_monitor = {
            "top": int(screen_height * 0.861),
            "left": int(screen_width * 0.25),
            "width": int(screen_width * 0.098),
            "height": 12
        }

        # === Cropped region for detection
        self.detection_monitor = {
            "top": self.display_monitor["top"] + 9,
            "left": self.display_monitor["left"] + 9,
            "width": self.display_monitor["width"] - 18,
            "height": 2
        }

        self.sct = mss()
        self.last_printed_percent = -1
        self.recent_percentages = deque(maxlen=5)

        self.label = QLabel(self)
        self.label.setGeometry(0, 0, self.output_width, self.output_height)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_overlay)
        self.timer.start(33)

    def update_overlay(self):
        display_img = np.array(self.sct.grab(self.display_monitor))[:, :, :3]
        detect_img = np.array(self.sct.grab(self.detection_monitor))[:, :, :3]

        # === Final tuned range for filled bar (BGR)
        lower = np.array([52, 81, 100])
        upper = np.array([79, 140, 171])

        mask = cv2.inRange(detect_img, lower, upper)
        fill_ratio = cv2.countNonZero(mask) / mask.size
        percent = round(fill_ratio * 100, 1)

        self.recent_percentages.append(percent)
        smoothed = round(sum(self.recent_percentages) / len(self.recent_percentages), 1)

        if abs(smoothed - self.last_printed_percent) >= 0.5:
            print(f"Stun bar filled: {smoothed}%")
            self.last_printed_percent = smoothed

        resized = cv2.resize(display_img, (self.output_width, self.output_height), interpolation=cv2.INTER_NEAREST)
        h, w, ch = resized.shape
        bytes_per_line = ch * w
        qimg = QImage(resized.data, w, h, bytes_per_line, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(qimg)
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 20, QFont.Bold))
        painter.drawText(10, 30, f"{smoothed:.1f}%")
        painter.end()

        self.label.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(self.pos() + event.pos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.dragging = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = StunBarOverlay()
    overlay.show()
    sys.exit(app.exec_())

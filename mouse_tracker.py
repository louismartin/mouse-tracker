import sys
import math
from threading import Thread
import time

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, pyqtSlot
from pynput import mouse


class MouseMonitor():

    def __init__(self, emit_score, decay=1):
        self.emit_score = emit_score
        self.decay = decay
        self.last_timestamp = time.time()
        self.count = 0
        self.mouse_controller = mouse.Controller()

    def increment(self, increment):
        base_increment = 2
        current_timestamp = time.time()
        delta = current_timestamp - self.last_timestamp
        self.last_timestamp = current_timestamp
        self.count = self.count * math.exp(-self.decay * delta) + base_increment * increment
        score = min(1, self.count / 100)
        self.emit_score(score)
        if score == 1:
            # Deactivate the mouse if score is at maximum
            self.mouse_controller.position = (0, 0)


    def __str__(self):
        return str(self.count)

    def __repr__(self):
        return self.__str__()

    def on_move(self, x, y):
        self.increment(1)

    def on_click(self, x, y, button, pressed):
        self.increment(10)

    def on_scroll(self, x, y, dx, dy):
        self.increment(1)


class MouseMonitorUpdater(Thread):

    def __init__(self, mouse_monitor):
        Thread.__init__(self)
        self.mouse_monitor = mouse_monitor

    def run(self):
        while True:
            self.mouse_monitor.increment(0)  # Increment by 0 only to update score


class Worker(QObject):
    '''Inspired from https://stackoverflow.com/a/41605909/4255993'''

    sig_emit_score = pyqtSignal(float)

    @pyqtSlot()
    def work(self):
        mouse_monitor = MouseMonitor(emit_score=self.sig_emit_score.emit, decay=1)
        mouse_monitor_updater = MouseMonitorUpdater(mouse_monitor)
        with mouse.Listener(on_move=mouse_monitor.on_move,
                            on_click=mouse_monitor.on_click,
                            on_scroll=mouse_monitor.on_scroll) as listener:
            mouse_monitor_updater.start()
            listener.join()
            mouse_monitor_updater.join()


class App(QMainWindow):

    def __init__(self):
        super().__init__(None, Qt.WindowStaysOnTopHint)
        self.title = 'Mouse tracker'
        self.left = 1000
        self.top = 10
        self.width = 440
        self.height = 20
        self.init_UI()

    def init_UI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        # Set window background color
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)
        # Add paint widget and paint
        self.progress_bar = PaintWidget(self, self.width, self.height)
        self.progress_bar.move(0, 0)
        self.progress_bar.resize(self.width, self.height)
        # Start mouse listener
        self.start_mouse_listener()
        self.show()

    def start_mouse_listener(self):
        self.worker = Worker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.worker.sig_emit_score.connect(self.on_worker_emit_score)
        self.thread.started.connect(self.worker.work)
        self.thread.start()

    @pyqtSlot(float)
    def on_worker_emit_score(self, score):
        self.progress_bar.fill(score)


class PaintWidget(QWidget):

    def __init__(self, parent, width, height):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.fill_proportion = 0  # Percentage of the bar to be filled between 0 and 1

    def fill(self, fill_proportion):
        self.fill_proportion = fill_proportion
        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setPen(Qt.NoPen)
        n_rectangles = 1000
        rectangle_width = self.width / n_rectangles
        for i in range(round(self.fill_proportion * n_rectangles)):
            qp.setBrush(QColor(200, 0, 0))
            qp.drawRect(rectangle_width * i, 0, rectangle_width + 1, self.height)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())

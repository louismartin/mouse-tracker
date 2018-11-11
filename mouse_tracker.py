import random
import sys
import math
from threading import Thread
import time

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QLabel
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, pyqtSlot
from pynput import mouse


class Counter():

    def __init__(self, emit_score, decay=1):
        self.emit_score = emit_score
        self.decay = decay
        self.last_timestamp = time.time()
        self.count = 0
        self.last_print = time.time()

    def increment(self, increment):
        current_timestamp = time.time()
        delta = current_timestamp - self.last_timestamp
        self.last_timestamp = current_timestamp
        self.count = self.count * math.exp(-self.decay * delta) + increment
        self.emit_score(min(1, self.count / 100))

    def __str__(self):
        return str(self.count)

    def __repr__(self):
        return self.__str__()

    def on_move(self, x, y):
        self.increment(1)

    def on_click(self, x, y, button, pressed):
        self.increment(1)

    def on_scroll(self, x, y, dx, dy):
        self.increment(1)


class CounterUpdater(Thread):

    def __init__(self, counter):
        Thread.__init__(self)
        self.counter = counter

    def run(self):
        while True:
            self.counter.increment(0)  # Increment by 0 only to update score


class Worker(QObject):
    '''Inspired from https://stackoverflow.com/a/41605909/4255993'''

    sig_emit_score = pyqtSignal(float)
    sig_done = pyqtSignal(str)
    sig_msg = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.__abort = False

    @pyqtSlot()
    def work(self):
        thread_name = QThread.currentThread().objectName()
        thread_id = int(QThread.currentThreadId())  # Casting to int is necessary
        counter = Counter(emit_score=self.sig_emit_score.emit, decay=1)
        counter_updater = CounterUpdater(counter)
        with mouse.Listener(on_move=counter.on_move, on_click=counter.on_click, on_scroll=counter.on_scroll) as listener:
            counter_updater.start()
            listener.join()
            counter_updater.join()

    def abort(self):
        self.sig_msg.emit('Abort')
        self.__abort = True


class App(QMainWindow):
    sig_abort_worker = pyqtSignal()

    def __init__(self):
        super().__init__(None, Qt.WindowStaysOnTopHint)
        self.title = 'Mouse tracker'
        self.left = 1000
        self.top = 10
        self.width = 440
        self.height = 20
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Set window background color
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # Add paint widget and paint
        self.progress_bar = PaintWidget(self, self.width, self.height)
        self.progress_bar.move(0,0)
        self.progress_bar.resize(self.width, self.height)


        self.start_mouse_listener()
        self.show()
        # https://stackoverflow.com/a/33453124/4255993
        # https://wiki.python.org/moin/PyQt/Threading%2C_Signals_and_Slots
        # https://stackoverflow.com/questions/37252756/simplest-way-for-pyqt-threading/37256736
        #listener = QMouseListener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
        #listener.__exit__()
        #listener.join()

    def start_mouse_listener(self):
        self.worker = Worker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        self.worker.sig_emit_score.connect(self.on_worker_emit_score)
        self.worker.sig_done.connect(self.on_worker_done)
        self.worker.sig_msg.connect(self.on_worker_msg)

        self.sig_abort_worker.connect(self.worker.abort)

        self.thread.started.connect(self.worker.work)
        self.thread.start()

    @pyqtSlot(float)
    def on_worker_emit_score(self, score):
        self.progress_bar.fill(score)

    @pyqtSlot(str)
    def on_worker_done(self, message):
        print(message)

    @pyqtSlot(str)
    def on_worker_msg(self, message):
        print(message)

    @pyqtSlot()
    def abort_worker(self):
        self.sig_abort_worker.emit()
        self.thread.quit()
        self.thread.wait()


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

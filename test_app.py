import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel

app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("Test PyQt App")
window.setGeometry(100, 100, 400, 200)

label = QLabel("Hello World!", window)
label.setGeometry(100, 80, 200, 40)

window.show()
sys.exit(app.exec_()) 
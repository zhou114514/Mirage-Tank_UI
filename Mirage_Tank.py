# -*- coding: utf-8 -*-
import multiprocessing
import sys
import threading
import os
import time

from PyQt5 import QtCore, QtGui, QtWidgets

from mainWin import MainWindow


if __name__ == '__main__':
    multiprocessing.freeze_support()
    
    #不加这一行就会界面很小
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)

    app = QtWidgets.QApplication(sys.argv)

    MainWindow = MainWindow()
    MainWindow.show()
    MainWindow.init_ui()

    QtWidgets.QMessageBox.information(MainWindow, "欢迎使用", "作者：JackHaoZhu\ngithub:https://github.com/JackHaozhu")

    sys.exit(app.exec_())
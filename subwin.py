import multiprocessing
import sys
import threading
import os
import time

from PIL import Image, ImageOps
from PyQt5 import QtCore, QtGui, QtWidgets
from Ui_SubWIn import Ui_SubWin_Form
from PhantomTankMake_SelfChoose import TankMake
from PyQt5.QtWidgets import QVBoxLayout
from MyDrop import *


class SubWin(QtWidgets.QWidget, Ui_SubWin_Form):
    labelcolor = 0;

    def __init__(self, parent=None):
        super(SubWin, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("SubWin")
        self.Change_btn.clicked.connect(self.change_btn_callback)

    def change_btn_callback(self):
        self.labelcolor = (self.labelcolor + 1) % 2
        if self.labelcolor == 0:
            self.pic.setStyleSheet("QLabel{background-color:white}")
        else:
            self.pic.setStyleSheet("QLabel{background-color:black}")
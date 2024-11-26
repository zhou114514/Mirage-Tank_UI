import multiprocessing
import sys
import threading
import os
import time
import queue

from PIL import Image, ImageOps
from PyQt5 import QtCore, QtGui, QtWidgets
from Ui_mainWin import Ui_MainWindow
from subwin import SubWin
from PhantomTankMake_SelfChoose import TankMake
from PyQt5.QtWidgets import QVBoxLayout
from MyDrop import *

perview_queue = queue.Queue()

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Mirage Tank")

    def init_ui(self):
        self.choose_cover.clicked.connect(self.cover_selected_callback)
        self.choose_inside.clicked.connect(self.inside_selected_callback)
        self.cover_perview.setAlignment(Qt.AlignCenter) 
        self.inside_perview.setAlignment(Qt.AlignCenter) 
        self.make_btn.clicked.connect(self.make_tank_callback)
        self.perview_btn.clicked.connect(self.perview_callback)
        self.cover_path.textChanged.connect(self.cover_path_changed_callback)
        self.inside_path.textChanged.connect(self.inside_path_changed_callback)
        self.cover_perview.dropFinished.connect(self.cover_drop)
        self.inside_perview.dropFinished.connect(self.inside_drop)
        

    def cover_drop(self,file_path):
        self.cover_path.setText(file_path)


    def inside_drop(self,file_path):
        self.inside_path.setText(file_path)


    def resizeEvent(self, event):
        super(MainWindow, self).resizeEvent(event)
        self.cover_path_changed_callback()
        self.inside_path_changed_callback()


    def cover_path_changed_callback(self):
        try:
            cover = self.cover_path.text()
            try:
                pixmap = QtGui.QPixmap(cover)
            except Exception as e:
                self.cover_perview.clear()
                return
            if pixmap.isNull():
                return 
            scaled_pixmap = pixmap.scaled(self.cover_perview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.cover_perview.setPixmap(scaled_pixmap)
        except Exception as e:
            print(e)

    def inside_path_changed_callback(self):
        try:
            inside = self.inside_path.text()
            try:
                pixmap = QtGui.QPixmap(inside)
            except:
                self.inside_perview.clear()
                return
            if pixmap.isNull():
                return
            scaled_pixmap = pixmap.scaled(self.inside_perview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.inside_perview.setPixmap(scaled_pixmap)
        except Exception as e:
            print(e)


    def cover_selected_callback(self):
        self.label.setText("等待中……")
        cover = TankMake.select_image()
        if cover:
            self.cover_path.setText(cover)
            cover_change_thread = threading.Thread(target=self.cover_path_changed_callback)
            cover_change_thread.start()
        else:
            QtWidgets.QMessageBox.warning(self, "警告", "文件不存在或打开失败！")

    def inside_selected_callback(self):
        self.label.setText("等待中……")
        inside = TankMake.select_image()
        if inside:
            self.inside_path.setText(inside)
            inside_change_thread = threading.Thread(target=self.inside_path_changed_callback)
            inside_change_thread.start()
        else:
            QtWidgets.QMessageBox.warning(self, "警告", "文件不存在或打开失败！")


    def make_tank_callback(self):
        cover_path = self.cover_path.text()
        inside_path = self.inside_path.text()
        if cover_path == '' or inside_path == '':
            QtWidgets.QMessageBox.warning(self, "警告", "请选择图片！")
            return
        self.label.setText("制作中...")
        make_thread = threading.Thread(target=self.make_tank, args=(cover_path, inside_path, True))
        make_thread.start()


    def perview_callback(self):
        self.SubWin = SubWin()
        self.SubWin.show()
        pic = threading.Thread(target=self.make_tank, args=(self.cover_path.text(), self.inside_path.text(), False))
        pic.start()
        pic.join()
        try:
            self.SubWin.pic.setPixmap(QtGui.QPixmap(perview_queue.get()))
        except Exception as E:
            print(E)


    def make_tank(self, cover_path, inside_path, save=True):
        default_config = '''brightness_enhancment: 50
#↑范围0~100
brightness_reduction: -50
#↑范围-100~0
auto_open_folder: True
auto_quit: False
debug_mode: False'''

        config = TankMake.read_config(default_config)
        cover_pic = Image.open(cover_path)
        inside_pic = Image.open(inside_path)

        if self.typechoose.currentText() == '黑白':
            self.make_tank_black(cover_pic, inside_pic, config, save)
        else:
            b_f = 12
            b_b = 7
            if self.brightness_f.text() != '' and self.brightness_b.text != '':
                b_f = int(self.brightness_f.text())
                b_b = int(self.brightness_b.text())
            self.make_tank_colorful(cover_pic, inside_pic, config, b_f, b_b, save)

        self.label.setText("制作完成！")


    def make_tank_black(self, cover_pic, inside_pic, config, save=True):
        resized_cover, resized_inside = TankMake.resize_image(cover_pic, inside_pic)
        gray_cover, gray_inside = (TankMake.desaturate_image_with_alpha(resized_cover),
                                    TankMake.desaturate_image_with_alpha(resized_inside))
        
        brighten_cover = TankMake.brighten_image(gray_cover, config['brightness_enhancment'])
        final_inside = TankMake.brighten_image(gray_inside, config['brightness_reduction'])

        final_cover = TankMake.invert_image(brighten_cover)

        linear_dodged_image = TankMake.linear_dodge(final_cover, final_inside)
        divided_image = TankMake.divide_image(final_inside, linear_dodged_image)
        Mirage_tank = TankMake.apply_red_channel_mask(linear_dodged_image, divided_image)

        if save:
            file_name = 'MirageTank' + time.strftime('_%y%m%d_%H%M%S', time.localtime()) + '.png'
            Mirage_tank.save(file_name)

            if config['auto_open_folder']:
                TankMake.open_and_select(file_name)
        else:
            perview_queue.put(Mirage_tank)


    def make_tank_colorful(self, image_f, image_b, config, brightness_f=12, brightness_b=7, save=True):
        start=time.time()
        #导出宽高信息
        w_f,h_f=image_f.size
        w_b,h_b=image_b.size
        #注意：jep图片的像素信息储存格式为RGB，缺少透明度的设置
        #所以需要新建一个RGBA格式的照片文件
        w_min=min(w_f,w_b)
        h_min=min(h_f,h_b)
        new_image=Image.new('RGBA',(w_min,h_min))#此处使用的是两者较大一方的参数
        #load()将图片的像素信息储存成array，提供位置坐标即可调出
        # 其速度优于open()
        array_f=image_f.load()
        array_b=image_b.load()
        #调整为同比例图片（计算宽高比例）
        scale_h_f=int(h_f/h_min)
        scale_w_f=int(w_f/w_min)
        scale_h_b=int(h_b/h_min)
        scale_w_b=int(w_b/w_min)
        #确定较小的比例为参照比例
        scale_f=min(scale_h_f,scale_w_f)
        scale_b=min(scale_h_b,scale_w_b)
        #使选中像素点居于原图片中央
        trans_f_x=int((w_f-w_min*scale_f)/2)
        trans_b_x=int((w_b-w_min*scale_b)/2)
        #设置修正参数
        a=brightness_f
        b=brightness_b
        for i in range(0,w_min):
            for j in range(0,h_min):
                #注意：像素点位置是修正过的
                R_f,G_f,B_f=array_f[trans_f_x+i*scale_f,j*scale_f]
                R_b,G_b,B_b=array_b[trans_b_x+i*scale_b,j*scale_b]
                #对亮度信息进行修正
                R_f *= a/10
                R_b *= b/10
                G_f *= a/10
                G_b *= b/10
                B_f *= a/10
                B_b *= b/10
                #注意：下面的系数变量及结果通过LAB颜色空间求颜色近似度得到
                delta_r = R_b - R_f
                delta_g = G_b - G_f
                delta_b = B_b - B_f
                coe_a = 8+255/256+(delta_r - delta_b)/256
                coe_b = 4*delta_r + 8*delta_g + 6*delta_b + ((delta_r - delta_b)*(R_b+R_f))/256 + (delta_r**2 - delta_b**2)/512
                A_new = 255 + coe_b/(2*coe_a)
                A_new = int(A_new)
                #A_new可能存在不属于0-255的情况，需要进行修正
                if A_new<=0:
                    A_new=0
                    R_new=0
                    G_new=0
                    B_new=0
                elif A_new>=255:
                    A_new=255
                    R_new=int((255*(R_b)*b/10)/A_new)
                    G_new=int((255*(G_b)*b/10)/A_new)
                    B_new=int((255*(B_b)*b/10)/A_new)
                else:
                    A_new=A_new
                    R_new=int((255*(R_b)*b/10)/A_new)
                    G_new=int((255*(G_b)*b/10)/A_new)
                    B_new=int((255*(B_b)*b/10)/A_new)
                pixel_new=(R_new,G_new,B_new,A_new)
                #注：刚发现调试是可以看到临时数据的，需要设置断点
                # print(pixel_new)
                #导入像素信息
                new_image.putpixel((i,j),pixel_new)
        #保存新图片 
        if save:
            file_name = 'MirageTank' + time.strftime('_%y%m%d_%H%M%S', time.localtime()) + '.png'
            new_image.save(file_name)

            if config['auto_open_folder']:
                TankMake.open_and_select(file_name)
        else:
            perview_queue.put(new_image)


    def closeEvent(self, event):
        """
        重写closeEvent方法，实现dialog窗体关闭时执行一些代码
        :param event: close()触发的事件
        :return: None
        """
        reply = QtWidgets.QMessageBox.question(self,
                                               'Mirage Tank',
                                               "是否要退出程序？",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()

            os._exit(0)

        else:
            event.ignore()
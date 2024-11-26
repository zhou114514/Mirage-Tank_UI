from PIL import Image, ImageOps
import time, os, yaml, logging, sys, subprocess
import tkinter as tk
from tkinter import filedialog
import colorama
from colorama import Style, Fore
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *

logger = logging.getLogger('PhantomTank_Log')

class TankMake(QtWidgets.QMainWindow):

    def logger_initialize(debug_mode):
        colorama.init()

        logger.setLevel(logging.DEBUG)

        console_level = logging.DEBUG if debug_mode else logging.INFO
        console_formatter = logging.Formatter(Fore.LIGHTBLUE_EX +
                                            '[%(asctime)s] [%(levelname)s] %(message)s' +
                                            Style.RESET_ALL,
                                            datefmt='%Y-%m-%d %H:%M:%S')
        file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s',
                                        datefmt='%Y-%m-%d %H:%M:%S')

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(console_level)
        logger.addHandler(console_handler)

        if debug_mode:
            if not os.path.exists('PTM_logs'):
                os.makedirs('PTM_logs', exist_ok=True)
            save_time = time.strftime('%y-%m-%d_%H%M%S', time.localtime())
            save_name = f'log_{save_time}.log'
            log_path = os.path.join('PTM_logs', save_name)
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)

        return logger


    def read_config(default_config: str):
        config_file = 'PTM_config.yml'

        if not os.path.exists(config_file):
            with open(config_file, 'w', encoding='utf-8') as file:
                file.write(default_config)

        with open(config_file, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)

        return config


    def select_image():
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except ImportError:
            logging.warning('Import Error: ctypes或windll无法导入')
        except AttributeError:
            logging.warning('Attribute Error: windll.shcore.SetProcessDpiAwareness方法不存在')
        except Exception as e:
            logging.warning(f'Unexpected Exception: {e}')

        root = tk.Tk()
        root.withdraw()

        file_path = filedialog.askopenfilename(title='选择图片',
                                            filetypes=[
                                                ('图片文件', '*.jpg *.jpeg *.png *.bmp *.webp'),
                                                ('所有文件', '*.*')
                                            ])
        if file_path:
            # selected_image = Image.open(file_path)
            return file_path
        else:
            return None


    def resize_image(surface, inner):
        resized_surface, resized_inner = surface, inner
        logger.debug('正在将里图横向缩放至与表图宽度相等')

        surface_width, surface_height = surface.size
        logger.debug(f'表图尺寸: {surface_width}x{surface_height}')

        inner_width, inner_height = inner.size
        logger.debug(f'里图尺寸: {inner_width}x{inner_height}')

        ratio = surface_width / inner_width
        resized_width, resized_height = int(ratio * inner_width), int(ratio * inner_height)
        resized_inner = inner.resize((resized_width, resized_height))
        logger.debug(f'缩放后里图尺寸: {resized_width}x{resized_height}:')

        logger.debug('正在填充容器...')
        if surface_width >= resized_width and surface_height >= resized_height:
            padding_img = Image.new('RGBA', (surface_width, surface_height), (0, 0, 0, 0))
            padding_img.paste(resized_inner, (0, (surface_height - resized_height) // 2))
            resized_inner = padding_img
        else:
            padding_img = Image.new('RGBA', (resized_width, resized_height), (0, 0, 0, 0))
            padding_img.paste(surface, (0, (resized_height - surface_height) // 2))
            resized_surface = padding_img
        # padding_img = Image.new('RGBA',
        #                         (max(surface_width, resized_width), max(surface_height, resized_height)),
        #                         (0, 0, 0, 0))
        # padding_img.paste(resized_inner if surface_width >= resized_width else surface,
        #                   (0, (abs(surface_height - resized_height) // 2)))
        #
        # resized_inner if surface_width >= resized_width else resized_surface = padding_img

        return resized_surface, resized_inner


    def desaturate_image_with_alpha(image):
        image = image.convert('RGBA')
        r, g, b, a = image.split()
        grayscale_image = Image.merge("RGB", (r, g, b)).convert("L")
        final_image = Image.merge("LA", (grayscale_image, a))
        return final_image


    def brighten_image(image, lightness):
        image = image.convert('RGBA')
        r, g, b, a = image.split()
        image = image.convert('RGB')
        pixels = list(image.getdata())
        adjusted_pixels = []
        for r, g, b in pixels:
            if lightness > 0:
                r = int((r + 255) * (lightness / 100))
                g = int((g + 255) * (lightness / 100))
                b = int((b + 255) * (lightness / 100))
            else:
                # r = int(r * (1 + lightness / 100))
                # g = int(g * (1 + lightness / 100))
                # b = int(b * (1 + lightness / 100))
                # print(r,g,b, end='  ')
                r = r // 2
                g = g // 2
                b = b // 2
                # print(r,g,b)
            adjusted_pixels.append((r, g, b))
        brightened_image = Image.new('RGB', image.size, (0, 0, 0))
        brightened_image.putdata(adjusted_pixels)
        brightened_image = Image.merge('RGBA', (brightened_image.split()[0],
                                                brightened_image.split()[1],
                                                brightened_image.split()[2],
                                                a))
        return brightened_image


    def invert_image(image):
        r, g, b, a = image.convert('RGBA').split()
        inverted_image = ImageOps.invert(image.convert("RGB"))
        inverted_image = Image.merge("RGBA",
                                    (inverted_image.split()[0],
                                    inverted_image.split()[1],
                                    inverted_image.split()[2],
                                    a))
        return inverted_image


    def linear_dodge(image1, image2):
        image1 = image1.convert('RGBA')
        image2 = image2.convert('RGBA')
        width, height = image1.size
        result_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        for x in range(width):
            for y in range(height):
                r1, g1, b1, a1 = image1.getpixel((x, y))
                r2, g2, b2, a2 = image2.getpixel((x, y))

                r = min(r1 + r2, 255)
                g = min(g1 + g2, 255)
                b = min(b1 + b2, 255)

                result_image.putpixel((x, y), (r, g, b))
        return result_image


    def divide_image(image1, image2):
        image1 = image1.convert('RGBA')
        image2 = image2.convert('RGBA')
        result_image = Image.new('RGBA', image1.size, (0, 0, 0, 0))
        base_pixels = image1.load()
        blend_pixels = image2.load()
        result_pixels = result_image.load()

        for x in range(image1.width):
            for y in range(image1.height):
                r_base, g_base, b_base, a_base = base_pixels[x, y]
                r_blend, g_blend, b_blend, a_blend = blend_pixels[x, y]

                r = min(255, r_base * 255 // (r_blend if r_blend != 0 else 1))
                g = min(255, g_base * 255 // (g_blend if g_blend != 0 else 1))
                b = min(255, b_base * 255 // (b_blend if b_blend != 0 else 1))
                a = a_base

                result_pixels[x, y] = (r, g, b, a)
        return result_image


    def apply_red_channel_mask(mask_image, target_image):
        r, g, b, a = mask_image.split()
        result_image = Image.new('RGBA', target_image.size)
        for y in range(target_image.height):
            for x in range(target_image.width):
                pixel_a = target_image.getpixel((x, y))
                mask_value = r.getpixel((x, y))

                new_pixel = (pixel_a[0], pixel_a[1], pixel_a[2], mask_value)
                result_image.putpixel((x, y), new_pixel)
        return result_image


    def config_verify(config_detail: str, config_value):
        logger.debug(f'正在校验{config_detail}')
        if config_detail == 'brightness_enhancement':
            try:
                num = float(config_value)
                if 0 <= num <= 100:
                    logger.debug(f'Brightness Enhancment: {config_value}')
                    return True
                else:
                    logger.error(f'{config_detail} out of range(0~100)')
                    return False
            except ValueError:
                logger.error(f'{config_detail} is not a number')
                return False
        if config_detail == 'brightness_reduction':
            try:
                num = float(config_value)
                if -100 <= num <= 0:
                    logger.debug(f'Brightness Reduction: {config_value}')
                    return True
                else:
                    logger.error(f'{config_detail} out of range(0~100)')
                    return False
            except ValueError:
                logger.error(f'{config_detail} is not a number')
                return False


    def open_and_select(file_name):
        if getattr(sys, 'frozen', False):
            file_folder_path = os.path.dirname(sys.executable)
        else:
            file_folder_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(file_folder_path, file_name)
        logger.debug(f'file_path: {file_path}')

        subprocess.run(f'explorer /select,"{file_path}"')

        

    # if __name__ == '__main__':
    #     default_config = '''brightness_enhancment: 50
    # #↑范围0~100
    # brightness_reduction: -50
    # #↑范围-100~0

    # auto_open_folder: True
    # auto_quit: False

    # debug_mode: False'''
    #     config = read_config(default_config)
    #     logger = logger_initialize(config['debug_mode'])
    #     try:
    #         logger.debug('读取配置: ')
    #         if not config_verify('brightness_enhancement', config['brightness_enhancment']):
    #             logger.info(f'brightness_enhancement使用默认值50')
    #             config['brightness_enhancment'] = 50
    #         if not config_verify('brightness_reduction', config['brightness_reduction']):
    #             logger.info(f'brightness_reduction使用默认值-50')
    #             config['brightness_reduction'] = -50
    #         logger.debug(f'Auto Quit: {config["auto_quit"]}')
    #         logger.debug(f'Debug Mode: {config["debug_mode"]}')
    #         logger.info('请选择表图...')
    #         logger.debug('等待一秒')
    #         time.sleep(1)
    #         surface_image = select_image()
    #         if surface_image is None:
    #             logger.info('未选择图片，退出程序...')
    #             if not config['auto_quit']:
    #                 logger.info('Press Enter to continue...')
    #                 input()
    #             sys.exit()
    #         logger.info('表图已选择，请选择里图...')
    #         logger.debug('等待一秒')
    #         time.sleep(1)

    #         inner_image = select_image()
    #         if inner_image is None:
    #             logger.info('未选择图片，退出程序')
    #             if not config['auto_quit']:
    #                 logger.info('Press Enter to continue...')
    #                 input()
    #             sys.exit()
    #         logger.info('里图已选择，正在处理')

    #         logger.info('正在调整图片尺寸...')
    #         resized_surface_image, resized_inner_image = resize_image(surface_image, inner_image)

    #         logger.info('正在调整灰度...')
    #         gray_surface, gray_inner = (desaturate_image_with_alpha(resized_surface_image),
    #                                     desaturate_image_with_alpha(resized_inner_image))

    #         logger.info('正在调整明度...')
    #         # if config['brightness_enhancment'] < 0 or config['brightness_enhancment'] > 100:
    #         #     logger.error('明度提升配置错误，使用默认值(50)')
    #         #     config['brightness_enhancment'] = 50
    #         #
    #         # if config['brightness_reduction'] > 0 or config['brightness_reduction'] < -100:
    #         #     logger.error('明度减弱配置错误，使用默认值(-50)')
    #         #     config['brightness_reduction'] = -50

    #         brighten_surface = brighten_image(gray_surface, config['brightness_enhancment'])
    #         final_inner = brighten_image(gray_inner, config['brightness_reduction'])

    #         logger.info('正在将图片反相...')
    #         final_surface = invert_image(brighten_surface)

    #         logger.info('正在合并图层...')
    #         logger.info('正在叠加线性减淡...')
    #         linear_dodged_image = linear_dodge(final_surface, final_inner)

    #         logger.info('正在添加划分叠加模式...')
    #         divided_image = divide_image(final_inner, linear_dodged_image)

    #         logger.info('正在套用通道模板...')
    #         phantom_tank = apply_red_channel_mask(linear_dodged_image, divided_image)

    #         logger.info('正在保存图片...')
    #         file_name = 'PhantomTank' + time.strftime('_%y%m%d_%H%M%S', time.localtime()) + '.png'
    #         phantom_tank.save(file_name)
    #         logger.info('保存成功！')
    #         logger.info(f'文件名为: {file_name}')
    #         if config['auto_open_folder']:
    #             logger.info('正在打开保存目录...')
    #             open_and_select(file_name)
    #         if not config['auto_quit']:
    #             logger.info('Press Enter to continue...')
    #             input()

    #     except KeyboardInterrupt:
    #         logger.info('用户终止程序')

    # pyinstaller --onefile --icon=main/resources/atri.ico main/phantomTank/make/PhantomTankMake_SelfChoose.py

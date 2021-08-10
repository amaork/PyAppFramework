# -*- coding: utf-8 -*-
import io
import os
import ctypes
import struct
from typing import Tuple, Callable, Optional, Union
from PIL import Image, GifImagePlugin, ImageDraw, ImageFont

from ..misc.settings import Color
from ..core.datatype import BasicTypeLE
__all__ = ['GifExtract', 'BitmapFileHeader', 'BitmapInfoHeader', 'ScrollingTextGifMaker',
           'bmp_to_24bpp', 'bmp_to_16bpp', 'pixel_888_to_565', 'pixel_888_to_555', 'ImageColor']

Pixel = Tuple[int, int, int]
ImageColor = Union[str, int, Color]
BmpProcess = Callable[[Image.Image], bytes]
PixelProcess = Callable[[Pixel], int]


class BitmapFileHeader(BasicTypeLE):
    _fields_ = [
        ('type', ctypes.c_char * 2),
        ('size', ctypes.c_uint32),
        ('reserved1', ctypes.c_uint16),
        ('reserved2', ctypes.c_uint16),
        ('offset', ctypes.c_uint32),
    ]

    def __str__(self):
        return "{}: {}, {}".format(self.type, self.size, self.offset)

    def __init__(self):
        super(BitmapFileHeader, self).__init__()
        self.type = b'BM'
        self.offset = 54
        self.reserved1 = 0
        self.reserved2 = 0


class BitmapInfoHeader(BasicTypeLE):
    _fields_ = [
        ('header_size', ctypes.c_uint32),
        ('width', ctypes.c_int32),
        ('height', ctypes.c_int32),
        ('plane', ctypes.c_uint16),
        ('bpp', ctypes.c_uint16),
        ('compression', ctypes.c_uint32),
        ('pixel_size', ctypes.c_uint32),
        ('h_ppm', ctypes.c_int32),
        ('v_ppm', ctypes.c_int32),
        ('palette_colors', ctypes.c_uint32),
        ('important_colors ', ctypes.c_uint32),
    ]

    def __str__(self):
        return '{}x{}: {}bpp, size: {}'.format(self.width, self.height, self.bpp, self.pixel_size)

    def __init__(self, width: int = 0, height: int = 0, bpp: int = 24):
        super(BitmapInfoHeader, self).__init__()
        self.header_size = ctypes.sizeof(self)
        self.bpp = bpp
        self.width = width
        self.height = height
        self.pixel_size = width * height * (bpp // 8)

        self.plane = 1
        self.compression = 0
        self.h_ppm = self.v_ppm = 0
        self.palette_colors = self.important_colors = 0


def pixel_888_to_555(pixel: Pixel) -> int:
    b, g, r = [(x & 0xff) >> 3 for x in pixel]
    return (b << 10) | (g << 5) | r


def pixel_888_to_565(pixel: Pixel) -> int:
    b, g, r = [x & 0xff for x in pixel]
    return ((b >> 3) << 11) | ((g >> 2) << 5) | (r >> 3)


def bmp_to_24bpp(im: Image.Image) -> bytes:
    output = io.BytesIO()
    nim = im.convert('RGB')
    nim.save(output, 'bmp')
    return output.getvalue()


def bmp_to_16bpp(im: Image.Image,
                 reverse: bool = True, with_header: bool = False,
                 pixel_process: PixelProcess = pixel_888_to_555) -> bytes:
    if not callable(pixel_process):
        raise TypeError("'pixel_process' must be callable")

    nim = im.convert('RGB')

    bpp16 = list()
    original = nim.tobytes()
    width, height = nim.size
    file_header = BitmapFileHeader()
    info_header = BitmapInfoHeader(width=width, height=height, bpp=16)

    v_list = range(height)
    v_list = v_list if reverse else v_list.__reversed__()

    for v in v_list:
        for h in range(width):
            # Already handle the width can't divisible by 4 issue
            offset = (height - v - 1) * width * 3 + h * 3
            bpp16.append(pixel_process(original[offset: offset + 3]))

    header = file_header.raw + info_header.raw if with_header else bytes()
    return header + struct.pack("<{}H".format(width * height), *tuple(bpp16))


class GifExtract(object):
    def __init__(self, gif: str):
        self._path = gif
        self._gif = Image.open(gif)
        if not isinstance(self._gif, Image.Image):
            raise TypeError("Open {} error".format(gif))

        if not isinstance(self._gif, GifImagePlugin.GifImageFile):
            raise TypeError('It not gif image: {}'.format(self._gif.format))

        try:
            self._loop = self._gif.info['loop']
            self._frame_count = self._gif.n_frames
            self._duration = self._gif.info['duration']
        except KeyError:
            raise TypeError("It's not animation gif")

        print("{}: {}, {}, frame count: {}, duration: {}, loop: {}".format(
            gif, self._gif.format, self._gif.size, self._gif.n_frames, self._duration, self._loop
        ))

    def __repr__(self):
        return "{}: {}, {}, frame count: {}, duration: {}, loop: {}".format(
            self._path, self._gif.format, self._gif.size, self.frame_count, self.duration, self.loop
        )

    @property
    def loop(self) -> int:
        return self._loop

    @property
    def path(self) -> str:
        return self._path

    @property
    def size(self) -> Tuple[int, int]:
        return self._gif.size

    @property
    def duration(self) -> int:
        return self._duration

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def extract_all(self, output_dir: str, process: Optional[BmpProcess] = None) -> bool:
        try:
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)

            for frame in range(self.frame_count):
                data = self.extract(frame, process=process)
                with open(os.path.join(output_dir, "{}.bmp".format(frame)), 'wb') as fp:
                    fp.write(data)

            return True
        except (EOFError, OSError) as e:
            print('Extract gifs error: {}'.format(e))
            return False

    def extract_all_as_bin(self, process: BmpProcess = bmp_to_16bpp) -> bytes:
        data = bytes()
        for frame in range(self.frame_count):
            data += self.extract(frame, process=process)

        return data

    def extract(self, frame: int, fmt: str = 'bmp', process: Optional[BmpProcess] = None) -> Optional[bytes]:
        try:
            self._gif.seek(frame)

            if callable(process):
                return process(self._gif.copy())
            else:
                output = io.BytesIO()
                self._gif.seek(frame)
                self._gif.save(output, fmt)
                return output.getvalue()
        except (EOFError, AttributeError, OSError) as e:
            print("Extract gif frame failed: {}".format(e))
            return None


class ScrollingTextGifMaker(object):
    def __init__(self, size: Tuple[int, int], margin: int, background: ImageColor = 'black'):
        self.margin = margin
        self.background = background
        self.im = Image.new('RGB', size, color=background)

    def isEnding(self, im: Image.Image, space_width: int) -> bool:
        width, height = im.size
        bg = im.getpixel((0, 0))
        for x in range(self.margin + space_width):
            if not all([im.getpixel((width - x - 1, y)) == bg for y in range(height)]):
                return False

        return True

    def calcFontSize(self, text: str, font: str) -> int:
        size = 10
        draw = ImageDraw.Draw(self.im)
        canvas_width, canvas_height = self.im.size

        while True:
            font_obj = ImageFont.truetype(font, size, encoding='unic')
            text_width, text_height = draw.textsize(text, font=font_obj)
            if text_width + self.margin >= canvas_width or text_height + self.margin >= canvas_height:
                return size
            else:
                size += 1

    def drawStaticText(self, text: str, path: str,
                       bg: ImageColor = 'black', fg: ImageColor = 'white', font: str = 'simsun.ttc', size: int = 0):
        size = size or self.calcFontSize(text, font)
        im = Image.new('RGB', self.im.size, color=bg)
        font = ImageFont.truetype(font, size, encoding='unic')

        draw = ImageDraw.Draw(im)
        canvas_width, canvas_height = im.size
        text_width, text_height = draw.textsize(text, font=font)

        draw.text(((canvas_width - text_width) // 2, (canvas_height - text_height) // 2), text, fg, font)
        im.save(path)

    def drawAnimationFrame(self, start: Tuple[int, int],
                           text: str, font: ImageFont.FreeTypeFont,
                           bg: ImageColor = 'black', fg: ImageColor = 'white') -> Image.Image:
        im = Image.new('RGB', self.im.size, color=bg)
        draw = ImageDraw.Draw(im)
        draw.text(start, text, fg, font)

        return im

    def createScrollTextGifAnimation(self, text: str, path: str,
                                     char_count_per_frame: int, move_pixel_per_frame: int,
                                     duration: int = 200, wait_frame_count: int = 0, blank_frame_count: int = 0,
                                     font: str = 'simsun.ttc', bg: ImageColor = 'black', fg: ImageColor = 'white'):
        """
        Create gif animation from #text specified text and save it to #path specified path
        :param text: text to stroll display
        :param path: gif file save path
        :param char_count_per_frame: how many chars will display on each frame(screen)
        :param move_pixel_per_frame: how many pixels will moved on each frame
        :param duration: gif duration
        :param wait_frame_count: how many frames it will wait at then end
        :param blank_frame_count: how many blank frames it will display at the end
        :param font: display text
        :param bg: background color
        :param fg: foreground color(the text)
        :return:
        """
        images = list()
        draw = ImageDraw.Draw(self.im)
        canvas_width, canvas_height = self.im.size
        font = ImageFont.truetype(font, self.calcFontSize("汉" * char_count_per_frame, font=font), encoding='unic')

        single_char_width, single_char_height = draw.textsize("汉", font=font)
        v_start = (canvas_height - single_char_height) // 2
        space_char_width = draw.textsize(" ", font=font)[0]
        current_render = 0

        while text[current_render:]:
            # Dynamically handle per text
            frame_count_per_char = draw.textsize(text[current_render], font=font)[0] // move_pixel_per_frame

            for i in range(frame_count_per_char):
                h_start = -move_pixel_per_frame * i
                images.append(self.drawAnimationFrame((h_start, v_start), text[current_render:], font, bg, fg))

                if self.isEnding(images[-1], space_char_width):
                    break

            if self.isEnding(images[-1], space_char_width):
                break

            current_render += 1

        for _ in range(blank_frame_count):
            images.append(Image.new('RGB', self.im.size, color=bg))

        for _ in range(wait_frame_count):
            images.append(self.drawAnimationFrame((self.margin, v_start), text, font, bg, fg))

        images[0].save(path, save_all=True,  append_images=images[1:], optimize=False, duration=duration, loop=0)

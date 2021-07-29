# -*- coding: utf-8 -*-
import io
import os
import ctypes
import struct
from typing import Tuple, Callable, Optional
from PIL import Image, GifImagePlugin
from .datatype import BasicTypeLE
__all__ = ['GifExtract', 'BitmapFileHeader', 'BitmapInfoHeader',
           'bmp_to_24bpp', 'bmp_to_16bpp', 'pixel_888_to_565', 'pixel_888_to_555']

Pixel = Tuple[int, int, int]
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
    return (r << 10) | (g << 5) | b


def pixel_888_to_565(pixel: Pixel) -> int:
    b, g, r = [x & 0xff for x in pixel]
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


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
    v_list = v_list.__reversed__() if reverse else v_list

    for v in v_list:
        for h in range(width):
            # Already handle the width can't divisible by 4 issue
            offset = (height - v - 1) * width * 3 + h * 3
            bpp16.append(pixel_process(original[offset: offset + 3]))

    header = file_header.raw + info_header.raw if with_header else bytes()
    return header + struct.pack("<{}H".format(width * height), *tuple(bpp16))


class GifExtract(object):
    def __init__(self, gif: str):
        self.path = gif
        self.gif = Image.open(gif)
        if not isinstance(self.gif, Image.Image):
            raise TypeError("Open {} error".format(gif))

        if not isinstance(self.gif, GifImagePlugin.GifImageFile):
            raise TypeError('It not gif image: {}'.format(self.gif.format))

        self._loop = self.gif.info['loop']
        self._frame_count = self.gif.n_frames
        self._duration = self.gif.info['duration']
        print("{}: {}, {}, frame count: {}, duration: {}, loop: {}".format(
            gif, self.gif.format, self.gif.size, self.gif.n_frames, self._duration, self._loop
        ))

    def __repr__(self):
        return "{}: {}, {}, frame count: {}, duration: {}, loop: {}".format(
            self.path, self.gif.format, self.gif.size, self.frame_count, self.duration, self.loop
        )

    @property
    def loop(self) -> int:
        return self._loop

    @property
    def size(self) -> Tuple[int, int]:
        return self.gif.size

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
            self.gif.seek(frame)

            if callable(process):
                return process(self.gif.copy())
            else:
                output = io.BytesIO()
                self.gif.seek(frame)
                self.gif.save(output, fmt)
                return output.getvalue()
        except EOFError as e:
            print("Extract gif frame failed: {}".format(e))
            return None

# -*- coding: utf-8 -*-
import platform
import subprocess
from typing import NamedTuple, Tuple
__all__ = ['get_win_dpi', 'get_program_scale_factor', 'scale_x', 'scale_y', 'scale_size', 'DPI', 'ScaleFactor',
           'show_file_in_explorer']

Size = Tuple[int, int]
DPI = NamedTuple('DPI', [('x', int), ('y', int)])
ScaleFactor = NamedTuple('ScaleFactor', [('x', float), ('y', float)])


def get_win_dpi() -> DPI:
    """ this function get the dpi on X and Y axis of default Windows desktop.

    In:
    none

    Out:
    x_dpi: dpi on x-axis. [int]
    y_dpi: dpi on y-axis. [int]

    """

    para_x = 88  # magic number of Windows API for x-axis
    para_y = 90  # magic number of Windows API for y-axis

    if platform.system().lower() == "windows" and int(platform.release()) <= 7:
        try:
            import win32gui
            import win32print

            hdc = win32gui.GetDC(0)
            x_dpi = win32print.GetDeviceCaps(hdc, para_x)
            y_dpi = win32print.GetDeviceCaps(hdc, para_y)
            return DPI(x_dpi, y_dpi)
        except (NameError, AttributeError):
            return DPI(96, 96)
    else:
        return DPI(96, 96)


def get_program_scale_factor() -> ScaleFactor:
    """ This function calculate the scale factor based on the current DPI setting.

    In:
    none

    Out:
    scale_x: scale factor on x-axis. [float]
    scale_y: scale factor on y-axis. [float]

    """

    default_dpi_x = 96.0  # default x-axis dpi setting for windows
    default_dpi_y = 96.0  # default y-axis dpi setting for windows

    current_dpi_x, current_dpi_y = get_win_dpi()
    current_dpi_x = float(current_dpi_x)
    current_dpi_y = float(current_dpi_y)

    return ScaleFactor(current_dpi_x / default_dpi_x, current_dpi_y / default_dpi_y)


def scale_x(width: int) -> int:
    factor = get_program_scale_factor()
    return int(factor.x * width)


def scale_y(height: int) -> int:
    factor = get_program_scale_factor()
    return int(factor.y * height)


def scale_size(size: Size) -> Size:
    factor = get_program_scale_factor()
    width, height = size
    return int(factor.x * width), int(factor.y * height)


def show_file_in_explorer(filepath: str):
    filepath = filepath.replace('/', '\\').replace('\\\\', '\\')
    subprocess.Popen(rf'explorer /select,"{filepath}"')


if __name__ == '__main__':
    # Test
    scale_x, scale_y = get_program_scale_factor()
    print(scale_x, scale_y, get_win_dpi())

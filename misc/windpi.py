# -*- coding: utf-8 -*-
import typing
import platform
import subprocess
from .process import launch_program, subprocess_startup_info
__all__ = ['get_win_dpi', 'get_program_scale_factor', 'scale_x', 'scale_y', 'scale_size', 'DPI', 'ScaleFactor',
           'system_open_file', 'show_file_in_explorer', 'copy_str_to_clip', 'is_windows',
           'get_windows_app_handles', 'switch_windows_app_to_foreground', 'get_windows_app_handle_by_title']

Size = typing.Tuple[int, int]
DPI = typing.NamedTuple('DPI', [('x', int), ('y', int)])
ScaleFactor = typing.NamedTuple('ScaleFactor', [('x', float), ('y', float)])


def is_windows() -> bool:
    return platform.system().lower() == "windows"


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

    if is_windows() and int(platform.release()) <= 7:
        try:
            # noinspection PyPackageRequirements
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


def system_open_file(filepath: str):
    launch_program('start {}', filepath, console_mode=False)


def copy_str_to_clip(data: str):
    subprocess.Popen(f'echo {data} | clip', shell=True, startupinfo=subprocess_startup_info(False))


def show_file_in_explorer(filepath: str):
    filepath = filepath.replace('/', '\\').replace('\\\\', '\\')
    subprocess.Popen(rf'explorer /select,"{filepath}"')


def get_windows_app_handles() -> typing.Dict[int, str]:
    if not is_windows():
        return dict()

    import win32gui

    def impl(hwnd, *_args):
        if win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd):
            if win32gui.GetWindowText(hwnd):
                hmap.update({hwnd: win32gui.GetWindowText(hwnd)})

    hmap = dict()
    win32gui.EnumWindows(impl, 0)
    return hmap


def get_windows_app_handle_by_title(app_title: str) -> int:
    hmap = get_windows_app_handles()
    for handle, title in hmap.items():
        if title != app_title:
            continue

        return handle

    return -1


def switch_windows_app_to_foreground(app_title: str) -> bool:
    if not is_windows():
        return False

    import win32gui
    import win32con

    hmap = get_windows_app_handles()
    for handle, title in hmap.items():
        if title != app_title:
            continue

        # win32gui.ShowWindow(handle, win32con.SW_RESTORE)

        try:
            win32gui.BringWindowToTop(handle)
            win32gui.SetForegroundWindow(handle)
            win32gui.ShowWindow(handle, win32con.SW_RESTORE)
        except Exception as e:
            print(f'switch_windows_app_to_foreground failed: {app_title},{e}')
            return False

        return True

    return False


if __name__ == '__main__':
    # Test
    scale_x, scale_y = get_program_scale_factor()
    print(scale_x, scale_y, get_win_dpi())

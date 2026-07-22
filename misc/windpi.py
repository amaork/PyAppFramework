# -*- coding: utf-8 -*-
import time
import typing
import platform
import subprocess
import contextlib
from .process import launch_program, subprocess_startup_info
__all__ = ['get_win_dpi', 'get_program_scale_factor', 'scale_x', 'scale_y', 'scale_size', 'DPI', 'ScaleFactor',
           'system_open_file', 'show_file_in_explorer', 'copy_str_to_clip', 'is_windows',
           'get_windows_app_handles', 'switch_windows_app_to_foreground', 'get_windows_app_handle_by_title',
           'get_windows_app_process_names', 'find_windows_app_handle', 'get_window_process_name',
           'get_window_rect', 'thread_dpi_awareness', 'send_key_to_window', 'get_thread_focus_window',
           'parse_key_sequence', 'send_key_sequence_to_window']

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


def get_window_process_name(handle: int) -> str:
    if not is_windows():
        return ''

    import psutil
    import pywintypes
    import win32process

    try:
        _, pid = win32process.GetWindowThreadProcessId(handle)
        return psutil.Process(pid).name()
    except (psutil.Error, pywintypes.error):
        return ''


def get_windows_app_process_names() -> typing.List[str]:
    names = {get_window_process_name(handle) for handle in get_windows_app_handles()}
    names.discard('')
    return sorted(names, key=str.lower)


def find_windows_app_handle(app_title: str, app_process: str = '') -> typing.Tuple[int, str]:
    """Find window handle, returns (handle, matched_by), matched_by: title/title(sub)/process, empty if not found"""
    hmap = get_windows_app_handles()

    # Exact title match first, then substring match
    for matched_by, title_match in (('title', lambda t: t == app_title),
                                    ('title(sub)', lambda t: app_title and app_title in t)):
        for handle, title in hmap.items():
            if title_match(title):
                return handle, matched_by

    # Fallback: match by process name (case-insensitive), prefer the largest window if multiple
    if app_process:
        best_handle, best_area = -1, -1
        for handle in hmap:
            if get_window_process_name(handle).lower() != app_process.lower():
                continue

            rect = get_window_rect(handle)
            area = abs((rect[2] - rect[0]) * (rect[3] - rect[1])) if rect else 0
            if area > best_area:
                best_handle, best_area = handle, area

        if best_handle != -1:
            return best_handle, 'process'

    return -1, ''


def get_window_rect(handle: int) -> tuple:
    if not is_windows():
        return ()

    import win32gui

    try:
        return win32gui.GetWindowRect(handle)
    except Exception:
        return ()


@contextlib.contextmanager
def thread_dpi_awareness():
    """Make mouse coordinates physical pixels regardless of app high-dpi setting (Win10 1607+)"""
    if not is_windows():
        yield
        return

    import ctypes

    # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE
    try:
        old_context = ctypes.windll.user32.SetThreadDpiAwarenessContext(-2)
    except (AttributeError, OSError):
        old_context = None

    try:
        yield
    finally:
        if old_context:
            ctypes.windll.user32.SetThreadDpiAwarenessContext(old_context)


def switch_windows_app_to_foreground(app_title: str, app_process: str = '', retries: int = 2) -> bool:
    if not is_windows():
        return False

    import win32api
    import win32con
    import win32gui
    import win32process

    handle, _ = find_windows_app_handle(app_title, app_process)
    if handle == -1:
        return False

    for attempt in range(retries + 1):
        try:
            # Only restore when minimized, keep maximized/normal size unchanged
            if win32gui.IsIconic(handle):
                win32gui.ShowWindow(handle, win32con.SW_RESTORE)

            # AttachThreadInput improves SetForegroundWindow success rate
            foreground = win32gui.GetForegroundWindow()
            foreground_tid, current_tid = 0, win32api.GetCurrentThreadId()
            if foreground:
                foreground_tid, _ = win32process.GetWindowThreadProcessId(foreground)

            attached = foreground_tid and foreground_tid != current_tid
            try:
                if attached:
                    win32process.AttachThreadInput(current_tid, foreground_tid, True)

                win32gui.BringWindowToTop(handle)
                win32gui.SetForegroundWindow(handle)
            finally:
                if attached:
                    win32process.AttachThreadInput(current_tid, foreground_tid, False)
        except Exception as e:
            print(f'switch_windows_app_to_foreground failed: {app_title},{e}')

        if win32gui.GetForegroundWindow() == handle:
            return True

        time.sleep(0.1 * (attempt + 1))

    print(f'switch_windows_app_to_foreground give up: {app_title}')
    return False


def key_name_to_vk(name: str) -> typing.Optional[int]:
    """Convert key name (case-insensitive, e.g. 'ctrl', 't', 'f5') to virtual key code"""
    import win32api

    name = name.strip().lower()
    if len(name) == 1:
        vk = win32api.VkKeyScan(name)
        return vk & 0xFF if vk != -1 else None

    if name.startswith('f') and name[1:].isdigit() and 1 <= int(name[1:]) <= 12:
        return 0x70 + int(name[1:]) - 1

    return {
        'ctrl': 0x11, 'control': 0x11, 'shift': 0x10, 'alt': 0x12, 'menu': 0x12,
        'win': 0x5B, 'enter': 0x0D, 'return': 0x0D, 'esc': 0x1B, 'escape': 0x1B,
        'tab': 0x09, 'space': 0x20, 'backspace': 0x08, 'del': 0x2E, 'delete': 0x2E,
        'ins': 0x2D, 'insert': 0x2D, 'home': 0x24, 'end': 0x23,
        'pageup': 0x21, 'pagedown': 0x22, 'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
    }.get(name)


def parse_key_sequence(sequence: str) -> typing.List[tuple]:
    """Parse key sequence 'F5, 500, CTRL+T' to [('keys', 'f5'), ('delay', 500), ('keys', 'ctrl+t')].

    Comma separated steps, a pure number step means delay in milliseconds (clamped to 60s).
    """
    steps = []
    for step in sequence.lower().split(','):
        step = step.strip()
        if not step:
            continue

        if step.isdigit():
            steps.append(('delay', min(int(step), 60000)))
        else:
            steps.append(('keys', step))

    return steps


def send_key_sequence_to_window(handle: int, sequence: str, interval: float = 0.03) -> bool:
    """Send key sequence (e.g. 'F5, 500, ENTER') to window, see parse_key_sequence for syntax"""
    for step_type, step_value in parse_key_sequence(sequence):
        if step_type == 'delay':
            time.sleep(step_value / 1000)
        elif not send_key_to_window(handle, step_value, interval):
            return False

    return True


def get_thread_focus_window(handle: int) -> int:
    """Get the window with keyboard focus in the thread owning handle, 0 if none"""
    if not is_windows():
        return 0

    import win32api
    import win32gui
    import win32process

    target_tid, _ = win32process.GetWindowThreadProcessId(handle)
    current_tid = win32api.GetCurrentThreadId()
    if target_tid == current_tid:
        return win32gui.GetFocus()

    try:
        # GetFocus works on the shared input queue after attaching
        win32process.AttachThreadInput(current_tid, target_tid, True)
        try:
            return win32gui.GetFocus()
        finally:
            win32process.AttachThreadInput(current_tid, target_tid, False)
    except Exception:
        return 0


def send_key_to_window(handle: int, keys: str, interval: float = 0.03) -> bool:
    """Post key sequence (e.g. 'CTRL+T') to window message queue directly.

    Keys are posted to the focused child window if any, many apps handle keys on child controls.
    Note: apps reading raw input (DirectInput, low-level hooks, Chromium) ignore posted keys.
    """
    if not is_windows():
        return False

    import win32api
    import win32con
    import win32gui

    focus = get_thread_focus_window(handle)
    if focus and focus != handle:
        print(f'send_key_to_window, redirect to focus window: {focus}')
        handle = focus

    vk_list = []
    for name in keys.split('+'):
        vk = key_name_to_vk(name)
        if vk is None:
            print(f'send_key_to_window, unknown key: {name}')
            return False

        vk_list.append(vk)

    modifiers = (win32con.VK_CONTROL, win32con.VK_SHIFT, win32con.VK_MENU, win32con.VK_LWIN, win32con.VK_RWIN)
    pressed = [vk for vk in vk_list if vk in modifiers]
    mains = [vk for vk in vk_list if vk not in modifiers]

    class TargetWindowGone(Exception):
        pass

    def post(vk, keyup):
        # Target window may be destroyed by the key itself (e.g. enter closed the tab)
        if not win32gui.IsWindow(handle):
            raise TargetWindowGone()

        scan_code = win32api.MapVirtualKey(vk, 0)
        lparam = 1 | (scan_code << 16)
        if keyup:
            lparam |= 0xC0000000

        win32gui.PostMessage(handle, win32con.WM_KEYUP if keyup else win32con.WM_KEYDOWN, vk, lparam)
        time.sleep(interval)

    try:
        if pressed:
            # Posted messages don't change target thread key state, so press modifiers physically
            # with AttachThreadInput to share input state with target thread.
            # Note: modifiers are really pressed and affect the foreground window briefly.
            import win32process

            target_tid, _ = win32process.GetWindowThreadProcessId(handle)
            current_tid = win32api.GetCurrentThreadId()
            attached = target_tid != current_tid

            try:
                if attached:
                    win32process.AttachThreadInput(current_tid, target_tid, True)

                for vk in pressed:
                    win32api.keybd_event(vk, 0, 0, 0)
                    time.sleep(interval)

                for vk in mains:
                    post(vk, False)
                    post(vk, True)
            finally:
                for vk in reversed(pressed):
                    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(interval)

                if attached:
                    win32process.AttachThreadInput(current_tid, target_tid, False)
        else:
            for vk in mains:
                post(vk, False)
                post(vk, True)
    except TargetWindowGone:
        print('send_key_to_window, target window closed during sending, keys were delivered')
        return True
    except Exception as e:
        print(f'send_key_to_window failed: {e}')
        return False

    return True


if __name__ == '__main__':
    # Test
    scale_x, scale_y = get_program_scale_factor()
    print(scale_x, scale_y, get_win_dpi())

# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import random
import typing
import shutil
import pathlib
import tempfile
import datetime
import contextlib
from xml.dom import minidom
from typing import List, Dict
import xml.etree.ElementTree as XmlElementTree
from xml.etree.ElementTree import Element as XmlElement
__all__ = [
    'awk_query', 'xml_format', 'qt_rcc_generate', 'qt_rcc_search', 'qt_file_fmt_convert', 'simulate_value',
    'get_timestamp_str', 'auto_deletion_tempdir', 'get_today_date', 'wait_timeout', 'get_newest_file_after',
    'size_convert', 'create_file_if_not_exist', 'utf8_truncate', 'has_chinese', 'is_frozen', 'is_script_mode'
]


def awk_query(cmd: str, keyword: str, position: int) -> str:
    """Execute #cmd specified command, then using grep search #keyword,
    finally using awk query the #position specified position values

    :param cmd: command to execute
    :param keyword: grep search keyword
    :param position: awk query position
    :return: query result
    """
    ret = os.popen("{0:s} | grep {1:s} | awk '{{print ${2:d}}}'".format(cmd, keyword, position))
    return ret.read().strip()


def xml_format(element: XmlElement, with_version: bool = True) -> str:
    """Return a pretty-printed XML string for the Element.

    :param element: XmlElement
    :param with_version: add xml version info: <?xml version="1.0" ?>
    :return: formatted xml string
    """
    rough_string = XmlElementTree.tostring(element, 'utf-8')
    re_parsed = minidom.parseString(b''.join([x.strip() for x in rough_string.split(b'\n')]))
    return re_parsed.toprettyxml(indent="\t", newl="\n")[0 if with_version else 23:]


def qt_file_fmt_convert(fmt: str) -> typing.Tuple[str, str]:
    """
    Convert Qt file format convert
    "Image(*.png *.bmp *.jpg *.jpeg)" ===> (Image, *.png *.bmp *.jpg *.jpeg)
    """
    pattern = r'\(.*?\)'
    return re.sub(pattern, '', fmt), re.search(pattern, fmt)[0][1:-1]


def qt_rcc_generate(res: Dict[str, List[str]]) -> str:
    """Generate Qt resources xml

    :param res: dict {resource prefix: resource file list}
    :return: return qt qrc file string
    """
    root = XmlElementTree.Element("RCC")

    for tag, items in res.items():
        if not len(items):
            continue

        # noinspection SpellCheckingInspection
        doc = XmlElementTree.SubElement(root, "qresource", prefix=tag)

        for file in items:
            XmlElementTree.SubElement(doc, "file").text = file

    return xml_format(root, with_version=False)


def qt_rcc_search(path: str, rules: Dict[str, str]) -> Dict[str, List[str]]:
    """Auto search qt resources with #rules specified rule

    :param path: search path
    :param rules: search rule {resource prefix: resource extensions}
    :return: resource pass to qt_rcc_generate to generate qrc xml file
    """
    def get_path(x):
        return x if path in ('.', './') else os.path.join(path, x)

    return {
        prefix: [get_path(x) for x in os.listdir(path) if os.path.splitext(x)[-1] == extensions]
        for prefix, extensions in rules.items()
    }


def get_today_date(hexadecimal: bool = False) -> int:
    """Date ===> hex number: Dec 5, 2022 ==> 20221205"""
    today = time.strftime('%Y%m%d')
    return int(today, 16) if hexadecimal else int(today)


def get_timestamp_str(ts: float, fmt: str = '%Y/%m/%d %H:%M:%S', fs_valid: bool = False) -> str:
    data_str = datetime.datetime.fromtimestamp(ts).strftime(fmt)
    return data_str.replace('/', '-').replace(' ', '_').replace(':', '') if fs_valid else data_str


def get_newest_file_after(watch_dir: str, watch_suffix: str, timestamp: float) -> typing.Sequence[str]:
    watch = pathlib.Path(watch_dir)
    files = [f'{x}' for x in watch.iterdir() if x.suffix == watch_suffix and x.lstat().st_ctime > timestamp]
    return sorted(files, key=lambda x: os.path.getctime(x))


def simulate_value(sv: int, rv: int, ss: typing.Tuple[int, int], increase: bool = True, env_sv: int = 0):
    v = random.randint(*ss)

    if increase:
        return rv + v if rv <= sv else rv - v
    else:
        return rv - v if rv >= env_sv else rv + v


def wait_timeout(condition: typing.Callable[[], bool], timeout: float,
                 desc: str, exception_cls: typing.Optional[typing.Type] = RuntimeError, interval: float = 0.1):
    if condition():
        return True

    end = time.perf_counter() + timeout
    interval = (timeout + 0.01) if interval >= timeout else interval
    while time.perf_counter() <= end:
        if condition():
            return True

        time.sleep(interval)

    if condition():
        return True

    try:
        if exception_cls is not None and issubclass(exception_cls, Exception):
            raise exception_cls(desc)
    except TypeError:
        return False

    return False


def size_convert(size: int, decimals: typing.Dict[str, int] = None) -> str:
    decimals = decimals or dict()
    # noinspection SpellCheckingInspection
    units = 'BKMGTPEZY'

    for i, unit in enumerate(units):
        if 2 ** (i * 10) <= size < 2 ** ((i + 1) * 10):
            return f'{size / (2 ** (i * 10)):.{decimals.get(unit, i + 1)}f}{unit}'

    return f'{size}'


def create_file_if_not_exist(name: str, data: bytes) -> str:
    """Create file if it's not exist

    :param name: filename
    :param data: filedata
    :return: filename
    """
    try:
        if not pathlib.Path(name).stat().st_size:
            raise RuntimeError('file is empty')
    except (OSError, RuntimeError):
        try:
            os.makedirs(os.path.dirname(name), 0o755, True)
            with open(name, 'wb') as fp:
                fp.write(data)
        except OSError:
            return ''

    return name


@contextlib.contextmanager
def auto_deletion_tempdir(catch_exceptions: typing.Sequence[typing.Type],
                          exception_callback: typing.Callable[[str], None],
                          ready_for_delete: typing.Callable[[], bool], **kwargs):
    """Create a temporary directory after using automatic delete it

    :param catch_exceptions: will handle exceptions
    :param exception_callback: when exceptions occur will invoke this function
    :param ready_for_delete: after use invoke this function to check if needed to delete this temporary directory
    :param kwargs: tempfile.mkdtemp kwargs
    :return:
    """

    tempdir = tempfile.mkdtemp(**kwargs)
    try:
        yield tempdir
    except tuple(catch_exceptions) as e:
        exception_callback(f'{e}')
    finally:
        try:
            if ready_for_delete() and os.path.isdir(tempdir):
                shutil.rmtree(tempdir)
                print(f'auto_deletion_tempdir: {tempdir} deleted')
        except shutil.Error as e:
            print(f'auto_deletion_tempdir: {tempdir} delete error, {e}')


def has_chinese(check_str: str) -> bool:
    try:
        check_str.encode('ascii')
    except UnicodeEncodeError:
        return True
    else:
        return False


def utf8_truncate(input_str: str, length: int) -> str:
    return input_str.encode('utf-8')[:length].decode(errors='ignore')


def is_frozen():
    return getattr(sys, 'frozen', False)


def is_script_mode():
    return not is_frozen()

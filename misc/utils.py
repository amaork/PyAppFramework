# -*- coding: utf-8 -*-
import os
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
__all__ = ['awk_query', 'xml_format', 'qt_rcc_generate', 'qt_rcc_search', 'simulate_value',
           'get_timestamp_str', 'auto_deletion_tempdir', 'get_today_date', 'wait_timeout', 'get_newest_file_after']


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
    re_parsed = minidom.parseString(rough_string)
    return re_parsed.toprettyxml(indent="\t", newl="\n")[0 if with_version else 23:]


def qt_rcc_generate(res: Dict[str, List[str]]) -> str:
    """Generate Qt resources xml

    :param res: dict {resource prefix: resource file list}
    :return: return qt qrc file string
    """
    root = XmlElementTree.Element("RCC")

    for tag, items in res.items():
        if not len(items):
            continue

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
                 desc: str, exception_cls: typing.Type = RuntimeError, interval: float = 0.1):
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

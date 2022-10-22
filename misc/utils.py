# -*- coding: utf-8 -*-
import os
import typing
import shutil
import tempfile
import datetime
import contextlib
from xml.dom import minidom
from typing import List, Dict
import xml.etree.ElementTree as XmlElementTree
from xml.etree.ElementTree import Element as XmlElement
__all__ = ['awk_query', 'xml_format', 'qt_rcc_generate', 'qt_rcc_search', 'get_timestamp_str', 'auto_deletion_tempdir']


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


def get_timestamp_str(ts: float, fmt: str = '%Y/%m/%d %H:%M:%S', fs_valid: bool = False) -> str:
    data_str = datetime.datetime.fromtimestamp(ts).strftime(fmt)
    return data_str.replace('/', '-').replace(' ', '_').replace(':', '') if fs_valid else data_str


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

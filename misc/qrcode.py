# -*- coding: utf-8 -*-
import io
import os
import qrcode
from PIL import Image
from typing import Optional
from pyzbar.pyzbar import Decoded
from pyzbar.pyzbar import decode as qr_decode
from ..core.datatype import DynamicObject
__all__ = ['qrcode_save_and_verify', 'qrcode_generate', 'qrcode_decode']


class QRCodeOption(DynamicObject):
    _properties = {'version', 'box_size', 'error_correction', 'border', 'fit', 'back_color', 'fill_color'}

    def __init__(self, **kwargs):
        kwargs.setdefault('fit', True)
        kwargs.setdefault('border', 4)
        kwargs.setdefault('version', 1)
        kwargs.setdefault('box_size', 5)
        kwargs.setdefault('back_color', 'white')
        kwargs.setdefault('fill_color', 'black')
        kwargs.setdefault('error_correction', qrcode.constants.ERROR_CORRECT_M)
        super(QRCodeOption, self).__init__(**kwargs)


def qrcode_save_and_verify(encode_data: bytes, path: str, option: Optional[QRCodeOption] = None) -> bool:
    """Save data to qr code and decode verify"""
    try:
        with open(path, "wb") as fp:
            fp.write(qrcode_generate(encode_data=encode_data, option=option, fmt=os.path.splitext(path)[-1][1:]))

        return qrcode_decode(path) == encode_data
    except (OSError, IndexError, KeyError) as e:
        print("{!r}: error: {}".format('qrcode_save_and_verify', e))
        return False


def qrcode_generate(encode_data: bytes, option: Optional[QRCodeOption] = None, fmt: str = 'png') -> bytes:
    option = option if isinstance(option, QRCodeOption) else QRCodeOption()
    qr = qrcode.QRCode(
        border=option.border,
        version=option.version,
        box_size=option.box_size,
        error_correction=option.error_correction
    )

    qr.add_data(encode_data)
    qr.make(fit=option.fit)

    img = qr.make_image(back_color=option.back_color, fill_color=option.fill_color)
    with io.BytesIO() as output:
        img.save(output, fmt)
        return output.getvalue()


def qrcode_decode(path: str) -> bytes:
    try:
        decode_data = qr_decode(Image.open(path))[0]
        if not isinstance(decode_data, Decoded):
            return bytes()

        return decode_data.data
    except (OSError, AttributeError, IndexError):
        return bytes()

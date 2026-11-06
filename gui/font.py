# -*- coding: utf-8 -*-
"""Font helpers shared by the framework GUI widgets.

Pixel-sized fonts (``setPixelSize``) scale together with the pixel-based
layout geometry at any screen scale factor. Point-sized fonts are resolved
against the screen logical DPI instead, so on 125%/150% display scaling they
grow relative to the layout and overflow (Qt High-DPI scaling enabled).
"""
from PySide2.QtGui import QFont

__all__ = ['make_pixel_font']


def make_pixel_font(family: str, px: int, weight: int = QFont.Normal) -> QFont:
    """Return a pixel-sized font: DPI-scale independent (pt * 96/72)."""
    font = QFont(family)
    font.setPixelSize(px)
    font.setWeight(weight)
    return font

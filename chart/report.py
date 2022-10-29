# -*- coding: utf-8 -*-
import os
import shutil
import typing
import tempfile
import contextlib
import collections
from reportlab.lib import colors
import reportlab.lib.pagesizes as ps
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, PageBreak

# Register font
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('SimSun', 'SimSun.ttf'))
__all__ = ['ReportlabGenerator', 'TableHeader']

from .canvas import CustomCanvas, ChartAxesAttribute
TableHeader = collections.namedtuple('TableHeader', 'header width')


class ReportlabGenerator:
    TABLE_DEF_STYLE = TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'LEFT'),
        ('VALIGN', (1, 1), (-1, -1), 'MIDDLE'),
        ('FACE', (0, 0), (-1, -1), 'SimSun'),
        ('SIZE', (0, 0), (-1, -1), 12),
    ])

    def __init__(self, landscape=ps.A3):
        self.story = list()
        self.landscape = landscape
        self.tempdir = tempfile.mkdtemp('reportlab_')

        # Customize style
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(
            name='CustomTitle', parent=self.styles['Title'], fontName='SimSun', leading=32, fontSize=36
        ))

        self.styles.add(ParagraphStyle(
            name='CustomHeading', parent=self.styles['Heading1'], fontName='SimSun', fontSize=26
        ))

        self.styles.add(ParagraphStyle(
            name='CustomAbstract', parent=self.styles['Heading2'], fontName='SimSun', fontSize=16
        ))

    def __del_tempdir(self):
        try:
            shutil.rmtree(self.tempdir)
        except OSError as e:
            print(f'{self.__class__.__name__}.__del_tempdir: {e}')

    def append_page_break(self):
        self.story.append(PageBreak())

    def append_story(self, story):
        self.story.append(story)

    def append_empty_line(self, count: int = 1):
        for i in range(count):
            self.append_paragraph('', 'CustomHeading')

    def append_stories(self, stories: typing.Sequence):
        self.story.extend(stories)

    def append_paragraph(self, content: str, style: str):
        self.story.append(Paragraph(content, style=self.styles[style]))

    def append_abstract(self, abstract: typing.Sequence[str], style: str = 'CustomAbstract'):
        for content in abstract:
            self.append_paragraph(content, style)

    def append_title(self, title: str, style: str = 'CustomTitle'):
        self.append_paragraph(title, style)

    def append_heading(self, heading: str, style: str = 'CustomHeading'):
        self.append_paragraph(heading, style)

    def append_table(self, table: typing.List, header: typing.Sequence[TableHeader],
                     style: typing.Optional[TableStyle] = None, row_height: int = 20):
        table.insert(0, [x.header for x in header])
        table = Table(table, colWidths=[x.width for x in header], rowHeights=[row_height] * len(table))
        table.setStyle(style or self.TABLE_DEF_STYLE)
        self.append_story(table)

    def append_plot_chart(self, xdata, ydata, attr: ChartAxesAttribute, **kwargs):
        canvas = CustomCanvas(**kwargs)
        chart = canvas.generatePlotAndSave(xdata, ydata, os.path.join(self.tempdir, 'plot.png'), attr)
        self.append_story(Image(chart))

    def append_pie_chart(self, values, ingredients: typing.Sequence[str], attr: ChartAxesAttribute, **kwargs):
        canvas = CustomCanvas(**kwargs)
        chart = canvas.generatePieAndSave(values, ingredients, os.path.join(self.tempdir, 'pie.png'), attr)
        self.append_story(Image(chart))

    def generate_report(self, path: str):
        doc = SimpleDocTemplate(path)
        doc.pagesize = self.landscape
        doc.build(self.story)
        self.__del_tempdir()
        return path

    @contextlib.contextmanager
    def paragraph(self, heading: str = '', before: int = 2, after: int = 2):
        if heading:
            self.append_heading(heading)

        self.append_empty_line(before)
        yield
        self.append_empty_line(after)

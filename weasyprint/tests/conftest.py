"""
    weasyprint.tests.conftest
    -------------------------

    Configuration for WeasyPrint tests.

    This module adds a PNG export based on GhostScript. As GhostScript is
    released under AGPL, the whole testing suite is released under AGPL.

"""

import io
import os
import shutil
from subprocess import PIPE, run

import pytest
from PIL import Image

from .. import HTML
from ..document import Document


def document_write_png(self, target=None, resolution=96, antialiasing=1):
    # TODO: don’t crash if GhostScript can’t be found
    # TODO: fix that for Windows
    command = [
        'gs', '-q', '-dNOPAUSE', '-dSAFER',
        '-sstdout=%%stderr' if os.name == 'nt' else '-sstdout=%stderr',
        f'-dTextAlphaBits={antialiasing}',
        f'-dGraphicsAlphaBits={antialiasing}', '-sDEVICE=png16m',
        f'-r{resolution}', '-sOutputFile=-', '-']
    command = run(command, input=self.write_pdf(), stdout=PIPE)
    pngs = command.stdout
    magic_number = b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'

    # TODO: use a different way to find PNG files in stream
    if pngs.count(magic_number) == 1:
        if target is None:
            return pngs
        png = io.BytesIO(pngs)
    else:
        images = []
        for i, png in enumerate(pngs[8:].split(magic_number)):
            images.append(Image.open(io.BytesIO(magic_number + png)))

        width = max(image.width for image in images)
        height = sum(image.height for image in images)
        output_image = Image.new('RGBA', (width, height))
        top = 0
        for image in images:
            output_image.paste(
                image, (int((width - image.width) / 2), top))
            top += image.height
        png = io.BytesIO()
        output_image.save(png, format='png')

    png.seek(0)

    if target is None:
        return png.read()

    if hasattr(target, 'write'):
        shutil.copyfileobj(png, target)
    else:
        with open(target, 'wb') as fd:
            shutil.copyfileobj(png, fd)


def html_write_png(self, target=None, stylesheets=None, resolution=96,
                   presentational_hints=False, optimize_images=False,
                   font_config=None, counter_style=None, image_cache=None):
    return self.render(
        stylesheets, presentational_hints=presentational_hints,
        optimize_images=optimize_images, font_config=font_config,
        counter_style=counter_style, image_cache=image_cache).write_png(
            target, resolution)


@pytest.fixture(autouse=True)
def monkey_write_png(monkeypatch):
    Document.write_png = document_write_png
    HTML.write_png = html_write_png

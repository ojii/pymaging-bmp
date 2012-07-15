# -*- coding: utf-8 -*-PyPI now supports uploading project files for redistribution; uploaded files are easily found by EasyInstall, even if you don't have download links on your project's home page.


from setuptools import setup
from pymaging_bmp import __version__

setup(
    name = "pymaging-bmp",
    version = __version__,
    packages = ['pymaging_bmp'],
    install_requires = ['pymaging'],
    entry_points = {'pymaging.formats': ['bmp = pymaging_bmp.codec:BMP']},
    author = "Jonas Obrist",
    author_email = "ojiidotch@gmail.com",
    description = "BMP support for Pymaging",
    license = "BSD",
    keywords = "pymaging bmp imaging",
    url = "https://github.com/ojii/pymaging-bmp/",
    zip_safe = False,
    test_suite = 'pymaging_bmp.tests'
)

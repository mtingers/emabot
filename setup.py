from distutils.core import setup
import setuptools
from setuptools import find_packages

setup(
    name='EmaBot',
    version='1.0.0',
    author='Matth Ingersoll',
    author_email='matth@mtingers.com',
    packages=find_packages(),
    license='GPLv3',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url='https://github.com/mtingers/emabot',
    install_requires=[
        'cbpro',
        'numpy',
        'pandas',
        'pandas-ta',
        'requests',
        'PyYAML',
        'wheel',
    ],
    entry_points={
        'console_scripts': [
            'emabot=emabot.bot:main',
        ],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)

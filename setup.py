from distutils.core import setup
import setuptools
from setuptools import find_packages

setup(
    name='EmaBot',
    version='2.0.0',
    author='Matth Ingersoll',
    author_email='matth@mtingers.com',
    packages=find_packages(),
    license='MIT',
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
        'tabulate',
        'tqdm',
    ],
    entry_points={
        'console_scripts': [
            'emabot=emabot.bot:main',
            'backtest=emabot.backtest:main',
            'dumppickle=emabot.dumppickle:main',
        ],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)

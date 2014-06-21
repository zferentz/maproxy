import os
from setuptools import setup


setup(name='maproxy',

    version = "0.0.6",
    author = "Zvika Ferentz",
    author_email = "zvika dot ferentz at gmail",
    description = ("My first attempt to create a simple and awesome "
                   "TCP proxy using Tornado"),
    #long_description=open('README').read(),


    py_modules=['src/maproxy'],

    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Topic :: Internet :: Proxy Servers"]
      )

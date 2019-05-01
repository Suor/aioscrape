from setuptools import setup


README = open('README.rst').read()

setup(
    name='aioscrape',
    version='0.0.1',
    author='Alexander Schepanovski',
    author_email='suor.web@gmail.com',

    description='Async scraping library',
    long_description=README,
    url='http://github.com/Suor/aioscrape',
    license='BSD',

    install_requires=[
        'aiohttp>=3.5.4',
        'aiocontextvars;python_version<"3.7"',
        'parsechain',
        'funcy>=1.11,<2.0',
    ],
    extras_require={
        'cache': ['aiocache', 'aiofilecache'],
    },
    packages=['aioscrape'],

    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',

        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
    ]
)

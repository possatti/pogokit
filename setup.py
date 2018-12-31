from setuptools import setup

setup(
    name='pogokit',
    version='0.1',
    description='Pokémon Go number cruncher',
    url='https://github.com/possatti/pogokit',
    author='Lucas Possatti',
    keywords='pokemon',
    license='MIT',

    packages=['pogokit'],
    install_requires=[
        'numpy>=1.14',
        'pandas>=0.23',
        'requests>=2.18',
        'fuzzywuzzy[speedup]>=0.17.0',
    ],
    entry_points={
        'console_scripts': ['pogo=pogokit.pogo:main'],
    },
    zip_safe=False)

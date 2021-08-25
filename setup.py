from setuptools import setup

setup(
    name='netscool',
    version='1',
    description='netscool',
    packages=['netscool'],
    install_requires=[
        'scapy',
        'IPython',
        'pytest',
        'sphinx',
        'sphinx_rtd_theme'],
    zip_safe=False)

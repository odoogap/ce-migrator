from setuptools import setup

setup(
    name='cemigrate',
    version='1.0.1',
    url='https://github.com/odoogap/ce-migrator.git',
    author='Diogo Duarte',
    author_email='dduarte@erpgap.com',
    description='Migration tool for Odoo Community Edition',
    packages=["cemigrate"],
    install_requires=['odoo-client-lib==1.2.2'],
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
    ],
)

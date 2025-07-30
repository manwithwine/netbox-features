from setuptools import setup, find_packages

setup(
    name="netbox-config-backup",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'paramiko>=2.7.1',
    ],
)

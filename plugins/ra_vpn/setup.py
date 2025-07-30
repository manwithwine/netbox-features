from setuptools import setup, find_packages

setup(
    name="ra_vpn",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'ra_vpn': ['templates/ra_vpn/*.html'],
    },
    install_requires=[],
)

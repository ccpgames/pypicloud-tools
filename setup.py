"""pypicloud-tools setup.py"""


from setuptools import setup


setup(
    name="pypicloud-tools",
    version="0.0.2",
    author="Adam Talsma",
    author_email="se-adam.talsma@ccpgames.com",
    packages=["pypicloud_tools"],
    entry_points={"console_scripts": [
        "upload = pypicloud_tools.upload:main",
        "download = pypicloud_tools.download:main",
        "list = pypicloud_tools.lister:main",
    ]},
    install_requires=["boto", "futures", "filechunkio", "requests"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Topic :: System :: Software Distribution",
        "Topic :: Utilities",
    ],
)

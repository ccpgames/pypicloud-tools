"""pypicloud-tools setup.py"""


import io
from setuptools import setup
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    """TestCommand subclass to use pytest with setup.py test."""

    def finalize_options(self):
        """Find our package name and test options to fill out test_args."""

        TestCommand.finalize_options(self)
        self.test_args = ['-v', '-rx', '--cov', 'pypicloud_tools',
            '--cov-report', 'term-missing']
        self.test_suite = True

    def run_tests(self):
        """Taken from http://pytest.org/latest/goodpractises.html."""

        # have to import here, outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        raise SystemExit(errno)


with io.open("README.rst", "r", encoding="utf-8") as openreadme:
    long_description = openreadme.read()


setup(
    name="pypicloud-tools",
    version="0.0.8",
    author="Adam Talsma",
    author_email="se-adam.talsma@ccpgames.com",
    packages=["pypicloud_tools"],
    entry_points={"console_scripts": [
        "upload = pypicloud_tools.upload:main",
        "download = pypicloud_tools.download:main",
        "list = pypicloud_tools.lister:main",
        "rehost = pypicloud_tools.rehost:main",
    ]},
    install_requires=[
        "boto >= 2.38.0",
        "futures >= 2.2.0, < 3.0.0",
        "filechunkio >= 1.6",
        "requests >= 2.6.2",
        "setuptools >= 15.0",
    ],
    tests_require=["pytest", "pytest-cov", "mock"],
    cmdclass={"test": PyTest},
    description="Tools to bypass PyPICloud and work with S3 directly",
    long_description=long_description,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Topic :: System :: Software Distribution",
        "Topic :: Utilities",
    ],
)

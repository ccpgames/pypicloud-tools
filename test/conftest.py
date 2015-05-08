"""Common pytest fixtures used in multiple tests."""


import os
import glob
import mock
import pytest
import tempfile

from boto.s3.key import Key


class TestFile(object):
    @staticmethod
    def filename(force_new=False):
        if not hasattr(TestFile, "_filename") or force_new:
            TestFile._filename = tempfile.mktemp(prefix="pypicloud_test-1-")
        return TestFile._filename


@pytest.fixture
def config_file(request):
    """Creates a new tempfile for this test."""

    request.addfinalizer(config_file_cleanup)
    return TestFile.filename(force_new=True)


def config_file_cleanup():
    """Remove the tempfile used in the previous test."""

    for filename in glob.glob("{}*".format(TestFile.filename())):
        try:
            os.remove(filename)
        except:
            pass


@pytest.fixture
def key_list():
    """Returns a list of mock objects usable as S3 Key objects."""

    def make_key(name):
        """Creates a mock S3 Key object."""
        key = mock.Mock(spec=Key)
        key.name = name
        return key

    return [
        make_key("package-one/package-one-1.2.3-alpha1-py2.py3-none-any.whl"),
        make_key("package-one/package-one-1.2.3-py2.py3-none-any.whl"),
        make_key("package-one/package-one-1.2.4-py2.py3-none-any.whl"),
        make_key("package-one/package-one-1.2.4.post1-py2.py3-none-any.whl"),
        make_key("package_two/package_two-0.0.1.dev1-py2.py3-none-any.whl"),
        make_key("package_two/package_two-0.0.1.dev2-py2.py3-none-any.whl"),
        make_key("package_two/package_two-0.0.1-py2.py3-none-any.whl"),
        make_key("package_two/package_two-0.0.1.tar.gz"),
        make_key("package_two/package_two-0.0.1-py2.7.egg"),
        make_key("error_pkg/error_pkg-2.3.4-py2.py3-none-any.whl"),
        make_key("error_pkg/error_pkg-2.3.4-py2-none-any.whl"),
        make_key("error_pkg/error_pkg-2.3.4.tar.gz"),
    ]


@pytest.fixture
def bucket_and_keys(key_list):
    """Returns a mock S3 bucket object with get_all_keys() and key_list."""

    bucket = mock.Mock()
    bucket.get_all_keys = mock.Mock(return_value=key_list)
    return bucket, key_list

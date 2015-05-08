"""Ensure the download functions work as expected."""


import sys
import mock
import pytest

if sys.version_info.major == 2:
    import __builtin__ as builtins
else:
    import builtins

import pypicloud_tools
from pypicloud_tools import download


@pytest.fixture
def argv_cleanup(request, autouse=True, scope="function"):
    """Adds a finalizer to clean up sys.argv in download."""

    sys._argv = sys.argv
    request.addfinalizer(argv_cleaner)


def argv_cleaner():
    """Reset download.sys.argv."""

    sys.argv = sys._argv
    del sys._argv


@pytest.fixture
def isatty_cleanup(request):
    """Adds a finalizer to clean up sys.stdout.isatty in download."""

    sys.stdout._isatty = sys.stdout.isatty
    request.addfinalizer(isatty_cleaner)


def isatty_cleaner():
    """Reset download.sys.stdout.isatty."""

    sys.stdout._isatty = sys.stdout.isatty
    del sys.stdout._isatty


def test_main():
    """Mocks everything to ensure the main entry point program flow."""

    bucket = mock.Mock()
    settings = mock.Mock()
    settings.items = ["faked"]

    with mock.patch.object(download, "get_settings", return_value=settings) as settings_patch:
        with mock.patch.object(download, "get_bucket_conn", return_value=bucket) as get_bucket_patch:
            with mock.patch.object(download, "download_package") as download_patch:
                with mock.patch.object(download, "parse_package", return_value=(1, 2)) as parse_patch:
                    download.main()

    settings_patch.assert_called_once_with(download=True)
    get_bucket_patch.assert_called_once_with(settings.s3)
    download_patch.assert_called_once_with(bucket, 1, 2)
    parse_patch.assert_called_once_with("faked")


def test_main_buries_errors(capfd):
    """Any Exception thrown in download_package should be handled."""

    bucket = mock.Mock()
    settings = mock.Mock()
    settings.items = ["faked"]

    with mock.patch.object(download, "get_settings", return_value=settings) as settings_patch:
        with mock.patch.object(download, "get_bucket_conn", return_value=bucket) as get_bucket_patch:
            with mock.patch.object(download, "download_package", side_effect=IOError) as download_patch:
                with mock.patch.object(download, "parse_package", return_value=(1, 2)) as parse_patch:
                    download.main()

    settings_patch.assert_called_once_with(download=True)
    get_bucket_patch.assert_called_once_with(settings.s3)
    download_patch.assert_called_once_with(bucket, 1, 2)
    parse_patch.assert_called_once_with("faked")

    out, err = capfd.readouterr()
    assert not out
    assert "Error downloading faked: " in err


def test_download_package__specific(bucket_and_keys):
    """Verify the calls made to succesfully download a specific package."""

    bucket, keys = bucket_and_keys

    with mock.patch.object(download, "write_key") as patched_write:
        download.download_package(bucket, "package-one", "1.2.3-alpha1")

    patched_write.assert_called_once_with(keys[0])


def test_download_package__not_found(bucket_and_keys):
    """SystemExit should be raised when the package is not found."""

    with pytest.raises(SystemExit) as exit_error:
        download.download_package(bucket_and_keys[0], "package-unknown")

    assert "Package package-unknown not found" in exit_error.value.args

    with pytest.raises(SystemExit) as specific_error:
        download.download_package(bucket_and_keys[0], "something", "1.2.3")

    assert "Package something=1.2.3 not found" in specific_error.value.args


def test_download_package__perfers_wheels(bucket_and_keys):
    """When multiple versions are available, by default prefer wheels."""

    bucket, keys = bucket_and_keys

    with mock.patch.object(download, "write_key") as patched_write:
        download.download_package(bucket, "package_two", "0.0.1")

    patched_write.assert_called_once_with(keys[6])


def test_download_package__prefer_egg(bucket_and_keys, argv_cleanup):
    """Ensure you can receive an egg if you request one."""

    bucket, keys = bucket_and_keys
    download.sys.argv = ["download", "package_two=0.0.1", "--egg"]

    with mock.patch.object(download, "write_key") as patched_write:
        download.download_package(bucket, "package_two", "0.0.1")

    patched_write.assert_called_once_with(keys[8])


def test_download_package__prefer_src(bucket_and_keys, argv_cleanup):
    """Ensure you can receive a source package if it's requested."""

    bucket, keys = bucket_and_keys
    download.sys.argv = ["download", "package_two=0.0.1", "--src"]

    with mock.patch.object(download, "write_key") as patched_write:
        download.download_package(bucket, "package_two", "0.0.1")

    patched_write.assert_called_once_with(keys[7])


def test_download_package__too_many_packages(bucket_and_keys):
    """If requesting a package with too many options, raise SystemExit."""

    bucket, keys = bucket_and_keys
    with pytest.raises(SystemExit) as exit_error:
        what = download.prefer_wheels(keys, "error_pkg")

    expected = (
        "Found too many results for error_pkg:\n"
        "  error_pkg/error_pkg-2.3.4-py2.py3-none-any.whl\n"
        "  error_pkg/error_pkg-2.3.4-py2-none-any.whl\n"
        "  error_pkg/error_pkg-2.3.4.tar.gz"
    )
    assert expected in exit_error.value.args

    with pytest.raises(SystemExit) as exit_error:
        what = download.prefer_wheels(keys, "error_pkg", "2.3.4")

    expected = (
        "Found too many results for error_pkg=2.3.4:\n"
        "  error_pkg/error_pkg-2.3.4-py2.py3-none-any.whl\n"
        "  error_pkg/error_pkg-2.3.4-py2-none-any.whl\n"
        "  error_pkg/error_pkg-2.3.4.tar.gz"
    )
    assert expected in exit_error.value.args


def test_write_key__to_file(capfd, isatty_cleanup):
    """Verify the calls made to write a S3 key to file."""

    download.sys.stdout.isatty = mock.Mock(return_value=True)
    key = mock.Mock()
    key.name = "mock_pkg/mock_pkg-1.0.2-dev1.tar.gz"

    with mock.patch.object(builtins, "open") as open_patch:
        download.write_key(key)

    key.get_contents_to_file.assert_called_once_with(open_patch().__enter__())
    out, err = capfd.readouterr()
    assert not err
    assert "mock_pkg-1.0.2-dev1.tar.gz" in out


def test_write_key__to_stdout(isatty_cleanup):
    """When sys.stdout is being piped/redicrected, print contents to it."""

    download.sys.stdout.isatty = mock.Mock(return_value=False)
    key = mock.Mock()
    download.write_key(key)
    key.get_contents_to_file.assert_called_once_with(download.sys.stdout)


@pytest.mark.parametrize("flag", ("--url", "--url-only"))
def test_write_key__generate_url(flag, capfd, argv_cleanup):
    """Ensure that we print a url when asked."""

    key = mock.Mock()
    download.sys.argv = ["download", flag]
    download.write_key(key)
    key.generate_url.assert_called_once_with(300)  # 5 minute URLs
    out, err = capfd.readouterr()
    assert not err
    assert str(key.generate_url(300)) in out


if __name__ == "__main__":
    pytest.main(["-v", "-rx", "--pdb", __file__])

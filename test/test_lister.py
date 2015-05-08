"""Ensure the pypicloud_tools lister functions work as expected."""


import mock
import pytest

import pypicloud_tools
from pypicloud_tools import lister


def test_main():
    """Mock all calls and verify the main lister application flow."""

    bucket = mock.Mock()
    settings = mock.Mock()
    settings.items = ["faked"]

    with mock.patch.object(lister, "get_settings", return_value=settings) as settings_patch:
        with mock.patch.object(lister, "get_bucket_conn", return_value=bucket) as get_bucket_patch:
            with mock.patch.object(lister, "list_package") as lister_patch:
                with mock.patch.object(lister, "parse_package", return_value=(1, 2)) as parse_patch:
                    lister.main()

    settings_patch.assert_called_once_with(listing=True)
    get_bucket_patch.assert_called_once_with(settings.s3)
    lister_patch.assert_called_once_with(bucket, 1, 2)
    parse_patch.assert_called_once_with("faked")


def test_main_buries_errors(capfd):
    """Any Exception thrown in list_package should be handled."""

    bucket = mock.Mock()
    settings = mock.Mock()
    settings.items = ["faked"]

    with mock.patch.object(lister, "get_settings", return_value=settings) as settings_patch:
        with mock.patch.object(lister, "get_bucket_conn", return_value=bucket) as get_bucket_patch:
            with mock.patch.object(lister, "list_package", side_effect=IOError) as lister_patch:
                with mock.patch.object(lister, "parse_package", return_value=(1, 2)) as parse_patch:
                    lister.main()

    settings_patch.assert_called_once_with(listing=True)
    get_bucket_patch.assert_called_once_with(settings.s3)
    lister_patch.assert_called_once_with(bucket, 1, 2)
    parse_patch.assert_called_once_with("faked")

    out, err = capfd.readouterr()
    assert not out
    assert "Error listing faked: " in err


def test_print_versioned__in_order(capfd):
    releases = [
        "some_thing-0.0.1",
        "some_thing-1.2.4",
        "some_thing-1.5.2.dev1",
        "some_thing-2.4.3",
        "some_thing-1.5.2",
        "some_thing-1.7.5",
    ]
    expected = [
        "some_thing=2.4.3",
        "some_thing=1.7.5",
        "some_thing=1.5.2",
        "some_thing=1.5.2.dev1",
        "some_thing=1.2.4",
        "some_thing=0.0.1",
    ]
    lister.print_versioned(releases, "some_thing")
    out, err = capfd.readouterr()
    assert not err
    assert "\n".join(expected) in out


def test_list_packages__all_packages(capfd, bucket_and_keys):
    """If no package is provided, all base names should be listed."""

    lister.list_package(bucket_and_keys[0], None)
    out, err = capfd.readouterr()
    assert not err
    assert "error_pkg\npackage-one\npackage_two" in out


def test_list_packages__specific(capfd, bucket_and_keys):
    """Verify the exact release is listed if requested."""

    with mock.patch.object(lister, "print_versioned") as patched_print:
        lister.list_package(bucket_and_keys[0], "package_two", "0.0.1")

    patched_print.assert_called_once_with(
        [
            "package_two-0.0.1.dev1-py2.py3-none-any.whl",
            "package_two-0.0.1.dev2-py2.py3-none-any.whl",
            "package_two-0.0.1-py2.py3-none-any.whl",
            "package_two-0.0.1.tar.gz",
            "package_two-0.0.1-py2.7.egg",
        ],
        "package_two",
    )


if __name__ == "__main__":
    pytest.main(["-v", "-rx", "--pdb", __file__])

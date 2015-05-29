"""Ensure the pypicloud_tools lister functions work as expected."""


import mock
import pytest

from pypicloud_tools import lister
from pypicloud_tools.utils import parse_package


def test_main():
    """Mock all calls and verify the main lister application flow."""

    bucket = mock.Mock()
    settings = mock.Mock()
    settings.items = ["faked"]

    mock_s = mock.patch.object(lister, "get_settings", return_value=settings)
    mock_b = mock.patch.object(lister, "get_bucket_conn", return_value=bucket)

    with mock_s as settings_patch:
        with mock_b as get_bucket_patch:
            with mock.patch.object(lister, "list_package") as lister_patch:
                with mock.patch.object(lister, "parse_package") as parse_patch:
                    lister.main()

    settings_patch.assert_called_once_with(listing=True)
    get_bucket_patch.assert_called_once_with(settings.s3)
    parse_patch.assert_called_once_with("faked")
    lister_patch.assert_called_once_with(bucket, parse_patch())


def test_main_buries_errors(capfd):
    """Any Exception thrown in list_package should be handled."""

    bucket = mock.Mock()
    settings = mock.Mock()
    settings.items = ["faked"]

    mock_s = mock.patch.object(lister, "get_settings", return_value=settings)
    mock_b = mock.patch.object(lister, "get_bucket_conn", return_value=bucket)
    mock_l = mock.patch.object(lister, "list_package", side_effect=IOError)

    with mock_s as settings_patch:
        with mock_b as get_bucket_patch:
            with mock_l as lister_patch:
                with mock.patch.object(lister, "parse_package") as parse_patch:
                    lister.main()

    settings_patch.assert_called_once_with(listing=True)
    get_bucket_patch.assert_called_once_with(settings.s3)
    parse_patch.assert_called_once_with("faked")
    lister_patch.assert_called_once_with(bucket, parse_patch())

    out, err = capfd.readouterr()
    assert not out
    assert "Error listing faked: " in err


def test_print_versioned__in_order(capfd):
    releases = [
        "some_thing-0.0.1-py2.py3-none-any.whl",
        "some_thing-1.2.4.egg",
        "some_thing-1.5.2.dev1.tar.gz",
        "some_thing-2.4.3.tar.gz",
        "some_thing-1.5.2-py2.py3-none-any.whl",
        "some_thing-1.7.5.tar.gz",
    ]
    expected = [
        "some-thing==2.4.3 : some_thing-2.4.3.tar.gz",
        "some-thing==1.7.5 : some_thing-1.7.5.tar.gz",
        "some-thing==1.5.2 : some_thing-1.5.2-py2.py3-none-any.whl",
        "some-thing==1.5.2.dev1 : some_thing-1.5.2.dev1.tar.gz",
        "some-thing==1.2.4 : some_thing-1.2.4.egg",
        "some-thing==0.0.1 : some_thing-0.0.1-py2.py3-none-any.whl",
    ]

    lister.print_versioned(releases, parse_package("some_thing"))

    out, err = capfd.readouterr()
    assert not err
    assert "\n".join(expected) in out


def test_list_packages__all_packages(capfd, bucket_and_keys):
    """If no package is provided, all base names should be listed."""

    lister.list_package(bucket_and_keys[0], None)
    out, err = capfd.readouterr()
    assert not err
    assert "error-pkg\npackage-one\npackage-two" in out


def test_list_packages__specific(capfd, bucket_and_keys):
    """Verify the exact release is listed if requested."""

    parsed_pkg = parse_package("package_two==0.0.1")
    with mock.patch.object(lister, "print_versioned") as patched_print:
        lister.list_package(bucket_and_keys[0], parsed_pkg)

    patched_print.assert_called_once_with(
        [
            "package-two-0.0.1-py2.py3-none-any.whl",
            "package_two-0.0.1.tar.gz",
            "package-two-0.0.1-py2.7.egg",
        ],
        parsed_pkg,
    )


def test_list_packages__ranges(capfd, bucket_and_keys):
    """Ensure we can use gt/lt/ge/le type ranges for listing."""

    parsed_pkg = parse_package("package_one < 1.2.4")
    with mock.patch.object(lister, "print_versioned") as patched_print:
        lister.list_package(
            bucket_and_keys[0],
            parsed_pkg,
        )

    patched_print.assert_called_once_with(
        [
            "package-one-1.2.3-alpha1-py2.py3-none-any.whl",
            "package-one-1.2.3-py2.py3-none-any.whl",
        ],
        parsed_pkg,
    )


if __name__ == "__main__":
    pytest.main(["-v", "-rx", "--pdb", __file__])

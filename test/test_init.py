"""Test the common functions found in the __init__ module."""


import os
import mock
import pytest

import pypicloud_tools


DEFAULT_CONFIG = os.path.join(os.path.expanduser("~"), ".pypirc")


def test_get_bucket_conn():
    """Tests the calls to boto to get our bucket object."""

    mock_config = mock.MagicMock(spec=pypicloud_tools.S3Config)
    mock_boto = mock.Mock()
    mock_bucket = mock.Mock()
    mock_boto.get_bucket = mock.Mock(return_value=mock_bucket)

    with mock.patch.object(pypicloud_tools.boto, "connect_s3", return_value=mock_boto) as patched_boto:
        bucket = pypicloud_tools.get_bucket_conn(mock_config)

    assert bucket == mock_bucket
    patched_boto.assert_called_once_with(mock_config.access, mock_config.secret)
    mock_boto.get_bucket.assert_called_once_with(mock_config.bucket)


def test_settings_from_config(config_file):
    """Ensure that the settings are correctly being read from config."""

    mock_options = mock.Mock()
    del mock_options.acl  # unset acl from command line
    mock_options.config = [config_file]
    with open(config_file, "w") as openconf:
        openconf.write("\n".join([
            "[pypicloud]",
            "repository:http://test-server/pypi",
            "username:test-username",
            "password:test-password",
            "bucket:test-bucket-name",
            "access:test-access-key",
            "secret:test-secret-key",
            "acl:test-acl",
        ]))

    expected_s3 = pypicloud_tools.S3Config(
        "test-bucket-name", "test-access-key", "test-secret-key", "test-acl"
    )
    expected_pypi = pypicloud_tools.PyPIConfig(
        "http://test-server/pypi", "test-username", "test-password"
    )

    s3, pypi = pypicloud_tools.settings_from_config(mock_options)

    assert s3 == expected_s3
    assert pypi == expected_pypi


def test_settings_from_config__no_key(config_file):
    """If there is no [pypicloud] key, we should receive None, None."""

    mock_options = mock.Mock()
    mock_options.config = config_file
    with open(config_file, "w") as openconf:
        openconf.writelines("\n".join([
            "[something]",
            "repository:http://fake.com/pypi",
            "username:joe",
            "password:hunter7",
        ]))

    assert pypicloud_tools.settings_from_config(mock_options) == (None, None)


def test_settings_from_config__cmdline_acl(config_file):
    """Ensure the command line acl overrides whatever is in the config."""

    mock_options = mock.Mock()
    mock_options.acl = ["override-acl"]
    mock_options.config = [config_file]
    with open(config_file, "w") as openconf:
        openconf.write("\n".join([
            "[pypicloud]",
            "repository:http://test-server/pypi",
            "username:test-username",
            "password:test-password",
            "extravals:are-ignored",
            "bucket:bucket-name",
            "access:access-key",
            "secret:secret-key",
            "acl:test-acl",
        ]))

    expected_s3 = pypicloud_tools.S3Config(
        "bucket-name", "access-key", "secret-key", "override-acl"
    )
    expected_pypi = pypicloud_tools.PyPIConfig(
        "http://test-server/pypi", "test-username", "test-password"
    )

    s3, pypi = pypicloud_tools.settings_from_config(mock_options)

    assert s3 == expected_s3
    assert pypi == expected_pypi


def test_settings_from_config__no_acl(config_file):
    """Ensure the acl is None when no acl is configured."""

    mock_options = mock.Mock()
    del mock_options.acl
    mock_options.config = [config_file]
    with open(config_file, "w") as openconf:
        openconf.write("\n".join([
            "[pypicloud]",
            "repository:http://test-server/pypi",
            "username:test-username",
            "password:test-password",
            "extravals:are-ignored",
            "bucket:bucket-name",
            "access:access-key",
            "secret:secret-key",
        ]))

    expected_s3 = pypicloud_tools.S3Config(
        "bucket-name", "access-key", "secret-key", None,
    )
    expected_pypi = pypicloud_tools.PyPIConfig(
        "http://test-server/pypi", "test-username", "test-password"
    )

    s3, pypi = pypicloud_tools.settings_from_config(mock_options)

    assert s3 == expected_s3
    assert pypi == expected_pypi


def test_settings_from_config__read_errors(config_file, capfd):
    """Ensure behaviour if/when there's an error reading the config file."""

    mock_options = mock.Mock()
    mock_options.config = config_file
    with open(config_file, "w") as openconf:
        openconf.write("[malform[ed]]\n**&&&$$$$----\nyes=yes\n")

    assert pypicloud_tools.settings_from_config(mock_options) == (None, None)
    out, err = capfd.readouterr()

    assert "File contains parsing errors:" in err
    assert not out


def test_parse_args__list_package():
    """Ensure the parser is setup correctly for listing a package."""

    pypicloud_tools.sys.argv = ["list", "test_package"]
    options, parser = pypicloud_tools.parse_args(listing=True)

    assert isinstance(parser, pypicloud_tools.argparse.ArgumentParser)
    assert isinstance(options, pypicloud_tools.argparse.Namespace)

    expected_options = {
        "packages": ["test_package"],
        "bucket": False,
        "server": False,
        "access": False,
        "secret": False,
        "user": False,
        "password": False,
        "config": DEFAULT_CONFIG,
    }
    assert vars(options) == expected_options
    assert "List package(s) from S3, bypassing PyPICloud" in str(parser)


def test_parse_args__list_all():
    """Ensure the parser is setup correctly for listing all packages."""

    pypicloud_tools.sys.argv = ["list", "--config", "fake.config"]
    options, parser = pypicloud_tools.parse_args(listing=True)

    assert isinstance(parser, pypicloud_tools.argparse.ArgumentParser)
    assert isinstance(options, pypicloud_tools.argparse.Namespace)

    expected_options = {
        "packages": [],
        "bucket": False,
        "server": False,
        "access": False,
        "secret": False,
        "user": False,
        "password": False,
        "config": ["fake.config"],
    }
    assert vars(options) == expected_options


def test_parse_args__upload():
    """Ensure the upload keys are populated in the argument parser."""

    pypicloud_tools.sys.argv = ["upload", "--acl", "fake-acl", "fake_file.tar"]
    options, parser = pypicloud_tools.parse_args(upload=True)

    assert isinstance(parser, pypicloud_tools.argparse.ArgumentParser)
    assert isinstance(options, pypicloud_tools.argparse.Namespace)

    expected_options = {
        "files": ["fake_file.tar"],
        "bucket": False,
        "server": False,
        "access": False,
        "acl": ["fake-acl"],
        "secret": False,
        "user": False,
        "password": False,
        "config": DEFAULT_CONFIG,
    }
    assert vars(options) == expected_options
    assert "Upload package(s) to S3, bypassing PyPICloud" in str(parser)


def test_parse_args__download():
    """Ensure the parser is properly configured for downloads."""

    pypicloud_tools.sys.argv = ["download", "--secret", "abc", "fake_package"]
    options, parser = pypicloud_tools.parse_args(download=True)

    assert isinstance(parser, pypicloud_tools.argparse.ArgumentParser)
    assert isinstance(options, pypicloud_tools.argparse.Namespace)

    expected_options = {
        "packages": ["fake_package"],
        "bucket": False,
        "server": False,
        "access": False,
        "secret": ["abc"],
        "user": False,
        "password": False,
        "config": DEFAULT_CONFIG,
    }
    assert vars(options) == expected_options
    assert "Download package(s) from S3, bypassing PyPICloud" in str(parser)


def test_get_settings__no_args():
    """get_settings() requires one boolean and only one boolean to be True."""

    with pytest.raises(RuntimeError):
        pypicloud_tools.get_settings()
    with pytest.raises(RuntimeError):
        pypicloud_tools.get_settings(True, False, True)


@pytest.mark.parametrize("direction", ("upload", "download"))
def test_get_settings__needs_remainders(direction):
    """When not listing, the user must provide a package or filename."""

    pypicloud_tools.sys.argv = [direction]
    with pytest.raises(SystemExit):
        pypicloud_tools.get_settings(download=True)


@pytest.mark.parametrize("direction, acl", [("upload", "fake-acl"), ("download", None)])
def test_get_settings__s3_overrides(direction, acl, config_file):
    """If s3 options are given on the command line, they take precedence."""

    with open(config_file, "w") as openconf:
        openconf.write("\n".join([
            "[pypicloud]",
            "repository:http://test-server/pypi",
            "username:test-username",
            "password:test-password",
            "bucket:bucket-name",
            "access:access-key",
            "secret:secret-key",
        ]))

    pypicloud_tools.sys.argv = [direction]

    if acl:
        pypicloud_tools.sys.argv.extend(["--acl", acl])

    pypicloud_tools.sys.argv.extend([
        "--bucket",
        "fake-bucket",
        "--access",
        "fake-access",
        "--secret",
        "fake-secret",
        "--config",
        config_file,
        "some_file",
        "some_other_file",
    ])

    settings = pypicloud_tools.get_settings(**{direction: True})
    expected_s3 = pypicloud_tools.S3Config(
        "fake-bucket", "fake-access", "fake-secret", acl,
    )
    expected_pypi = pypicloud_tools.PyPIConfig(
        "http://test-server/pypi", "test-username", "test-password"
    )

    assert settings.s3 == expected_s3
    assert settings.pypi == expected_pypi
    assert settings.items == ["some_file", "some_other_file"]


@pytest.mark.parametrize("direction", ("upload", "download"))
def test_get_settings__pypi_overrides(direction, config_file):
    """If pypi options are given on the command line, they take precedence."""

    with open(config_file, "w") as openconf:
        openconf.write("\n".join([
            "[pypicloud]",
            "repository:http://test-server/pypi",
            "username:test-username",
            "password:test-password",
            "bucket:bucket-name",
            "access:access-key",
            "secret:secret-key",
        ]))

    pypicloud_tools.sys.argv = [
        direction,
        "--server",
        "http://some-server/pypi",
        "--user",
        "some-user",
        "--password",
        "some-passwd",
        "--config",
        config_file,
        "some_file",
        "some_other_file",
    ]

    settings = pypicloud_tools.get_settings(**{direction: True})
    expected_s3 = pypicloud_tools.S3Config(
        "bucket-name", "access-key", "secret-key", None,
    )
    expected_pypi = pypicloud_tools.PyPIConfig(
        "http://some-server/pypi", "some-user", "some-passwd"
    )

    assert settings.s3 == expected_s3
    assert settings.pypi == expected_pypi
    assert settings.items == ["some_file", "some_other_file"]


def test_get_settings__config_fillins(config_file):
    """Ensure the config file fills in any missing arguments."""

    with open(config_file, "w") as openconf:
        openconf.write("\n".join([
            "[pypicloud]",
            "repository:http://test-server/pypi",
            "username:test-username",
            "password:test-password",
            "bucket:bucket-name",
            "access:access-key",
            "secret:secret-key",
        ]))

    pypicloud_tools.sys.argv = [
        "list",
        "--config",
        config_file,
        "some_file",
        "some_other_file",
    ]
    expected_s3 = pypicloud_tools.S3Config(
        "bucket-name", "access-key", "secret-key", None,
    )
    expected_pypi = pypicloud_tools.PyPIConfig(
        "http://test-server/pypi", "test-username", "test-password"
    )

    settings = pypicloud_tools.get_settings(listing=True)

    assert settings.s3 == expected_s3
    assert settings.pypi == expected_pypi
    assert settings.items == ["some_file", "some_other_file"]


def test_get_settings__no_s3_config(config_file, capfd):
    """If no s3 config is found, ensure get_settings raises an error."""

    pypicloud_tools.sys.argv = ["list", "--config", config_file]
    with pytest.raises(SystemExit):
        pypicloud_tools.get_settings(listing=True)

    out, err = capfd.readouterr()
    assert "ERROR: Could not determine S3 settings." in err
    assert DEFAULT_CONFIG in out  # stdout should be a help message...


@pytest.mark.parametrize(
    "package, pkg_name, pkg_ver",
    [
        ("foo-bar", "foo-bar", None),
        ("foo-bar=0.0.1", "foo-bar", "0.0.1"),
        (
            "foo-bar.baz[stuff]=1.2.beta-FINAL.release.2.tar.gz",
            "foo-bar.baz[stuff]",
            "1.2.beta-FINAL.release.2.tar.gz",
        ),
    ],
    ids=("no version", "simple version", "long exact"),
)
def test_parse_package(package, pkg_name, pkg_ver):
    """Ensure package strings are properly parsed."""

    pkg, ver = pypicloud_tools.parse_package(package)
    assert pkg == pkg_name
    assert ver == pkg_ver


if __name__ == "__main__":
    pytest.main(["-v", "-rx", "--pdb", __file__])

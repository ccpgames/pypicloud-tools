"""Verify the calls made during rehost."""


import os
import mock
import pytest
import tempfile

from pypicloud_tools import rehost
from pypicloud_tools import Settings
from pypicloud_tools import S3Config
from pypicloud_tools import PyPIConfig


@pytest.mark.parametrize("include_deps", (True, False))
def test_cleanup_tempdir(include_deps):
    """Ensure the tempdir used is removed afterwards."""

    starting = os.listdir(tempfile.tempdir)
    fake_s3 = S3Config("fake_bucket", "fake_access", "fake_secret", "fake_acl")
    fake_pypi = PyPIConfig("fake_server", "fake_user", "fake_passwd")
    fake_args = mock.Mock()
    fake_args.deps = include_deps
    fake_settings = Settings(fake_s3, fake_pypi, ["requests"], fake_args)

    with mock.patch.object(rehost.pip, "main") as patched_pip:
        with mock.patch.object(rehost, "upload_files") as patched_upload:
            with mock.patch.object(rehost, "get_bucket_conn") as patched_conn:
                with mock.patch.object(rehost, "get_settings", return_value=fake_settings):
                    rehost.main()

    assert len(starting) == len(os.listdir(tempfile.tempdir))

    pip_args = patched_pip.mock_calls[0][1][0]
    assert pip_args[0] == "install"
    assert pip_args[1] == "--download"
    assert pip_args[2].startswith(tempfile.tempdir)
    assert pip_args[3] == "requests"

    # items should be empty here because we've mocked downloading anything
    patched_upload.assert_called_once_with(
        Settings(fake_s3, fake_pypi, [], fake_args),
        patched_conn(),
    )


def test_rehost_filters():
    """Files with unsupported pip extensions in the tempdir are ignored."""

    # files without supported extensions should be ignored
    junk_file = "000-Flask-000.pdf"

    # you can recreate this list with:
    #  pip install --download . Flask==0.9 Flask-SQLAlchemy==0.16
    # it's a good example of dependency munging. we pin them here, but they're
    # obviously not pinned upstream, so we end up with two versions locally
    fake_files = [
        junk_file,
        "Flask-0.10.1.tar.gz",
        "Flask-0.9.tar.gz",
        "Flask-SQLAlchemy-0.16.tar.gz",
        "itsdangerous-0.24.tar.gz",
        "Jinja2-2.7.3.tar.gz",
        "MarkupSafe-0.23.tar.gz",
        "setuptools-16.0-py2.py3-none-any.whl",
        "SQLAlchemy-1.0.4.tar.gz",
        "Werkzeug-0.10.4-py2.py3-none-any.whl",
    ]

    with rehost.TempDir() as storage:
        for fake_file in fake_files:
            with open(os.path.join(storage.dir, fake_file), "w") as openfile:
                openfile.write("here be data")

        user_input = ["Flask==0.9", "Flask-SQLAlchemy==0.16"]
        expected = [os.path.join(storage.dir, file_) for file_ in
            ("Flask-0.9.tar.gz", "Flask-SQLAlchemy-0.16.tar.gz")]
        with mock.patch.object(rehost.logging, "info") as patched_info_log:
            with mock.patch.object(rehost.os, "listdir", return_value=fake_files):
                assert rehost.find_downloaded(user_input, storage.dir) == expected

        patched_info_log.assert_any_call(
            "file %s skipped, unsupported extension",
            junk_file,
        )


if __name__ == "__main__":
    pytest.main(["-v", "-rx", "--pdb", __file__])

"""Verify the calls made during rehost."""


import os
import mock
import pytest
import tempfile

from pypicloud_tools import rehost
from pypicloud_tools import Settings
from pypicloud_tools import S3Config
from pypicloud_tools import PyPIConfig


def test_cleanup_tempdir():
    """Ensure the tempdir used is removed afterwards."""

    starting = os.listdir(tempfile.tempdir)
    fake_s3 = S3Config("fake_bucket", "fake_access", "fake_secret", "fake_acl")
    fake_pypi = PyPIConfig("fake_server", "fake_user", "fake_passwd")
    fake_settings = Settings(fake_s3, fake_pypi, ["requests"])

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
        Settings(fake_s3, fake_pypi, []),
        patched_conn(),
    )


if __name__ == "__main__":
    pytest.main(["-v", "-rx", "--pdb", __file__])

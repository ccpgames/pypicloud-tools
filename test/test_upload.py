"""Tests to ensure the pypicloud_tools upload functions work as expected."""


import os
import mock
import pytest

import pypicloud_tools
from pypicloud_tools import upload


def test_main(capfd):
    """Mock all calls, ensure the command line entry point flow."""

    bucket = mock.Mock()
    settings = mock.Mock()
    settings.items = ["faked"]

    with mock.patch.object(upload, "get_settings", return_value=settings) as settings_patch:
        with mock.patch.object(upload, "get_bucket_conn", return_value=bucket) as bucket_patch:
            with mock.patch.object(upload, "upload_file") as upload_patch:
                with mock.patch.object(upload, "update_cloud") as cloud_patch:
                    upload.main()

    settings_patch.assert_called_once_with(upload=True)
    bucket_patch.assert_called_once_with(settings.s3)
    cloud_patch.assert_called_once_with(settings.pypi)
    upload_patch.assert_called_once_with("faked", bucket, settings.s3)
    out, err = capfd.readouterr()
    assert not err
    assert "PyPICloud server at {} updated".format(settings.pypi.server) in out


def test_main__buries_error(capfd):
    """PyPICloud should only be updated on success."""

    bucket = mock.Mock()
    settings = mock.Mock()
    settings.items = ["faked"]

    with mock.patch.object(upload, "get_settings", return_value=settings):
        with mock.patch.object(upload, "get_bucket_conn", return_value=bucket):
            with mock.patch.object(upload, "upload_file", side_effect=IOError):
                with mock.patch.object(upload, "update_cloud") as cloud_patch:
                    upload.main()

    out, err = capfd.readouterr()
    assert "Error uploading faked: " in err
    assert not out
    assert not cloud_patch.called


def test_update_cloud():
    """Ensure the proper request calls are used to update the PyPICloud API."""

    mock_get = mock.Mock()
    mock_get.raise_for_status = mock.Mock()
    mock_auth = mock.Mock()
    pypi = pypicloud_tools.PyPIConfig("http://fake/pypi/", "joe", "hunter2")

    with mock.patch.object(upload.requests.auth, "HTTPBasicAuth", return_value=mock_auth) as auth_patch:
        with mock.patch.object(upload.requests, "get", return_value=mock_get) as get_patch:
            assert upload.update_cloud(pypi) == mock_get.ok

    mock_get.raise_for_status.assert_called_once_with()
    auth_patch.assert_called_once_with("joe", "hunter2")
    get_patch.assert_called_once_with("http://fake/admin/rebuild", auth=mock_auth)


def test_upload_file(capfd, config_file):
    """Verify the calls made to upload a file to S3."""

    bucket = mock.Mock()
    bucket_key = mock.Mock()
    bucket.get_key = mock.Mock(return_value=bucket_key)
    mock_multipart = mock.Mock()
    mock_multipart.get_all_parts = mock.Mock(return_value=["one"])
    bucket.initiate_multipart_upload = mock.Mock(return_value=mock_multipart)

    s3_config = mock.Mock()
    file_contents = "some content inside this file..."
    with open(config_file, "w") as openfile:
        openfile.write(file_contents)

    with mock.patch.object(upload, "_upload_chunk") as patched_chunk_uploader:
        upload.upload_file(config_file, bucket, s3_config)

    out, err = capfd.readouterr()

    f_name = os.path.basename(config_file)
    expected_name = "{}/{}".format(f_name[:f_name.index("-")], f_name)
    assert "Uploading {} ...".format(expected_name) in out
    assert "done!" in out
    assert "failed!" not in out
    mock_multipart.complete_upload.assert_called_once_with()
    bucket.get_key.assert_called_once_with(expected_name)
    bucket_key.set_acl.assert_called_once_with(s3_config.acl)
    patched_chunk_uploader.assert_called_once_with(
        bucket,
        mock_multipart.id,   # multipart upload id
        1,                   # 50MB chunk number this is
        config_file,         # file to send
        0,                   # start of file
        len(file_contents),  # to the end of file
    )
    bucket.initiate_multipart_upload.assert_called_once_with(
        expected_name, headers={"Content-Type": "application/octet-stream"}
    )


def test_upload_file__failure(capfd, config_file):
    """Ensure the multipart upload is cancelled on error."""

    expected_name = os.path.basename(config_file)
    if "-" in expected_name:
        expected_name = expected_name[:expected_name.index("-")]
    config_file = "{}-0.0.1.tar.gz".format(config_file)
    expected_name = "/".join([expected_name, os.path.basename(config_file)])
    bucket = mock.Mock()
    bucket_key = mock.Mock()
    bucket.get_key = mock.Mock(return_value=bucket_key)
    mock_multipart = mock.Mock()
    mock_multipart.get_all_parts = mock.Mock(return_value=[])
    bucket.initiate_multipart_upload = mock.Mock(return_value=mock_multipart)

    s3_config = mock.Mock()
    file_contents = "some content inside this file..."
    with open(config_file, "w") as openfile:
        openfile.write(file_contents)

    with mock.patch.object(upload, "_upload_chunk") as patched_chunk_uploader:
        upload.upload_file(config_file, bucket, s3_config)

    out, err = capfd.readouterr()

    assert "Uploading {} ...".format(expected_name) in out
    assert "done!" not in out
    assert "failed! :(" in out
    mock_multipart.cancel_upload.assert_called_once_with()
    patched_chunk_uploader.assert_called_once_with(
        bucket,
        mock_multipart.id,   # multipart upload id
        1,                   # 50MB chunk number this is
        config_file,         # file to send
        0,                   # start of file
        len(file_contents),  # to the end of file
    )
    bucket.initiate_multipart_upload.assert_called_once_with(
        expected_name, headers={"Content-Type": "application/octet-stream"}
    )


def test_upload_chunk(capfd):
    """Ensure the chunk uploader is working as expected."""

    bucket = mock.Mock()
    mp_upload = mock.Mock()
    mp_upload.id = 1234
    bucket.get_all_multipart_uploads = mock.Mock(return_value=[mp_upload])

    with mock.patch.object(upload, "FileChunkIO") as patched_filechunkio:
        upload._upload_chunk(bucket, 1234, 1, "some-fake-file", 0, 50)

    patched_filechunkio.assert_called_once_with("some-fake-file", "rb", offset=0, bytes=50)

    mp_upload.upload_part_from_file.assert_called_once_with(
        fp=patched_filechunkio().__enter__(), part_num=1, cb=upload.print_dot
    )

    out, err = capfd.readouterr()
    assert not err
    assert "1" in out


def test_upload_chunks__errors():
    """It should try up to three additional times to upload each chunk."""

    bucket = mock.Mock()
    mp_upload = mock.Mock()
    mp_upload.id = 1234
    mp_upload.upload_part_from_file = mock.Mock(side_effect=IOError)
    bucket.get_all_multipart_uploads = mock.Mock(return_value=[mp_upload])

    with mock.patch.object(upload, "FileChunkIO") as patched_filechunkio:
        with pytest.raises(IOError):
            upload._upload_chunk(bucket, 1234, 1, "some-fake-file", 0, 50)

    assert bucket.get_all_multipart_uploads.call_count == 4


if __name__ == "__main__":
    pytest.main(["-v", "-rx", "--pdb", __file__])

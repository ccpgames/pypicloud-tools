"""Rehosts packages from PyPI in pypicloud.

Copyright (c) 2015 CCP Games. Released for use under the MIT license.
"""


import os
import pip
import shutil
import tempfile

from . import Settings
from . import get_settings
from . import get_bucket_conn
from .upload import upload_files


class TempDir(object):
    """Context manager for storing the in-transit files in temp storage."""
    def __init__(self):
        self.dir = tempfile.mkdtemp()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        shutil.rmtree(self.dir)


def main():
    """Entry point for rehosting PyPI packages on pypicloud."""

    settings = get_settings(rehost=True)
    bucket = get_bucket_conn(settings.s3)

    with TempDir() as storage:
        for package in settings.items:
            pip.main(["install", "--download", storage.dir, package])

        upload_settings = Settings(
            settings.s3,
            settings.pypi,
            [os.path.join(storage.dir, f) for f in os.listdir(storage.dir)],
        )
        upload_files(upload_settings, bucket)

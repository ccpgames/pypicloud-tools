"""Rehosts packages from PyPI in pypicloud."""


import os
import pip
import shutil
import logging
import tempfile
from pip.index import egg_info_matches
from pkg_resources import SetuptoolsVersion
from pkg_resources import parse_requirements

from . import Settings
from . import get_settings
from . import get_bucket_conn
from . import OPERATORS
from . import SUPPORTED_EXTENSIONS
from .upload import upload_files


class TempDir(object):
    """Context manager for storing the in-transit files in temp storage."""
    def __init__(self):
        self.dir = tempfile.mkdtemp()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        shutil.rmtree(self.dir)


def find_downloaded(packages, storage_dir):
    """Filters out the requested packages' dependencies in storage_dir.

    Args::

        packages: list of package names, perhaps version specific
        storage_dir: full string filepath to the temporary storage

    Returns:
        a list of string full file paths of package releases to upload
    """

    to_upload = []
    files_on_disk = os.listdir(storage_dir)
    for package in packages:
        parsed = list(parse_requirements(package))[0]
        for file_ in files_on_disk:
            if parsed.project_name not in file_:
                continue
            for ext in SUPPORTED_EXTENSIONS:
                if file_.endswith(ext):
                    file_ver = SetuptoolsVersion(egg_info_matches(
                        file_.split(ext)[0],
                        parsed.project_name,
                        file_,
                    ))
                    break
            else:
                logging.info("file %s skipped, unsupported extension", file_)
                continue
            for spec in parsed.specs:
                req_ver = SetuptoolsVersion(spec[1])
                if not OPERATORS[spec[0]](file_ver, req_ver):
                    logging.info("downloaded file %s is not %s %s", file_,
                                 spec[0], spec[1])
                    break
            else:
                to_upload.append(os.path.join(storage_dir, file_))
                break

    return to_upload


def main():
    """Entry point for rehosting PyPI packages on pypicloud."""

    settings = get_settings(rehost=True)
    bucket = get_bucket_conn(settings.s3)

    with TempDir() as storage:
        for package in settings.items:
            pip.main(["install", "--download", storage.dir, package])

        if settings.parsed.deps:
            up_files = [
                os.path.join(storage.dir, f) for f in os.listdir(storage.dir)
            ]
        else:
            up_files = find_downloaded(settings.items, storage.dir)

        upload_settings = Settings(
            settings.s3,
            settings.pypi,
            up_files,
            settings.parsed,
        )
        upload_files(upload_settings, bucket)

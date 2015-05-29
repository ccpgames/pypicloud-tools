"""PyPICloud list tool to bypass PyPICloud and list directly from S3.

Copyright (c) 2015 CCP Games. Released for use under the MIT license.
"""


from __future__ import print_function

import sys
from collections import defaultdict
from pkg_resources import safe_name

from . import get_settings
from . import get_bucket_conn
from .utils import parse_package
from .utils import parse_package_file


def list_package(bucket, package):
    """List the available releases a package, optionally package+release.

    Args::

        bucket: a connected S3 bucket object to look for package in
        package: parsed package object requested

    Returns:
        string URL to download the package at release or latest
    """

    # figure out key name from package and release requested and what's
    # available in the bucket...
    pkg_name = None if package is None else package.project_name
    package_releases = []
    for key in bucket.get_all_keys():
        if package is None or key.name.startswith("{}/".format(pkg_name)):
            package_base, _, pkg_full_name = key.name.partition("/")
            if not pkg_full_name:
                continue
            if package is None:
                if package_base not in package_releases:
                    package_releases.append(package_base)
            elif pkg_name == safe_name(package_base):
                key_pkg = parse_package_file(pkg_full_name, package)
                for spec in package.specs:
                    if not spec[0](key_pkg.specs[0][1], spec[1]):
                        break
                else:
                    package_releases.append(pkg_full_name)

    if package is None:
        package_releases.sort()
        print("\n".join(package_releases))
    else:
        print_versioned(package_releases, package)


def print_versioned(package_releases, package):
    """Prints package releases to stdout in order of version number."""

    # sort them via pkg_resources' version sorting
    versioned = defaultdict(list)
    for package_file in package_releases:
        package_release = parse_package_file(package_file, package)

        versioned[package_release.specs[0][1]].append(("{}=={} : {}".format(
            package_release.project_name,
            package_release.specs[0][1],
            package_file,
        )))

    # finally print them to stdout in order of newest first
    ver_order = sorted(versioned)
    for version_releases in reversed(ver_order):
        for version_release in versioned[version_releases]:
            print(version_release)


def main():
    """Main command line entry point for listing."""

    settings = get_settings(listing=True)
    bucket = get_bucket_conn(settings.s3)

    for package in settings.items or [None]:
        try:
            list_package(bucket, parse_package(package))
        except Exception as err:
            print("Error listing {}: {}".format(package, err),
                  file=sys.stderr)
            break

"""PyPICloud list tool to bypass PyPICloud and list directly from S3.

Copyright (c) 2015 CCP Games. Released for use under the MIT license.
"""


from __future__ import print_function

import sys
from collections import defaultdict

from . import get_settings, get_bucket_conn, parse_package, get_package_version


def list_package(bucket, package, release=None):
    """List the available releases a package, optionally package+release.

    Args::

        bucket: a connected S3 bucket object to look for package in
        package: string package name without version
        release: string release version to get or None for the latest

    Returns:
        string URL to download the package at release or latest
    """

    # figure out key name from package and release requested and what's
    # available in the bucket...
    package_releases = []
    for key in bucket.get_all_keys():
        if key.name.startswith("{}/".format(package)) or package is None:
            package_base, _, pkg_full_name = key.name.partition("/")
            if package is None:
                if package_base not in package_releases:
                    package_releases.append(package_base)
            elif release is None or release in pkg_full_name:
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
    for package_release in package_releases:
        version = get_package_version(package_release, package)
        versioned[version].append("{}={}".format(
            package_release[:len(package)],
            package_release[len(package) + 1:],
        ))

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
            list_package(bucket, *parse_package(package))
        except Exception as err:
            print("Error listing {}: {}".format(package, err),
                  file=sys.stderr)
            break

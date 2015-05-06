"""PyPICloud list tool to bypass PyPICloud and list directly from S3.

Copyright (c) 2015 CCP Games. Released for use under the MIT license.
"""


from __future__ import print_function

import re
import sys
from collections import defaultdict
from pkg_resources import SetuptoolsVersion, parse_version

from . import get_settings, get_bucket_conn, parse_package


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
        if key.name.startswith("{}/".format(package)):
            pkg_full_name = key.name.partition("/")[2]
            if release is None or release in pkg_full_name:
                package_releases.append(pkg_full_name)

    # sort them via pkg_resources' version sorting
    versioned = defaultdict(list)
    for package_release in package_releases:
        version = re.split(
            "\.|-",
            package_release[len(package) + 1:],
        )
        pkg_ver = ""
        for section in version:
            new_ver = "{}{}{}".format(
                pkg_ver,
                "." if pkg_ver else "",
                section,
            )
            if isinstance(parse_version(new_ver), SetuptoolsVersion):
                pkg_ver = new_ver
            else:
                break

        versioned[parse_version(pkg_ver)].append(package_release)

    # finally print them to stdout in order of newest first
    ver_order = sorted(versioned)
    for version_releases in reversed(ver_order):
        for version_release in versioned[version_releases]:
            print(version_release)


def main():
    """Main command line entry point for listing."""

    settings = get_settings(list=True)
    bucket = get_bucket_conn(settings.s3)

    for package in settings.items:
        try:
            list_package(bucket, *parse_package(package))
        except Exception as err:
            print("Error listing {}: {}".format(package, err), file=sys.stderr)
            break


if __name__ == "__main__":
    main()

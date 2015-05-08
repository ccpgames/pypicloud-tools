"""PyPICloud downloader tool to bypass PyPICloud and pull directly from S3.

Copyright (c) 2015 CCP Games. Released for use under the MIT license.
"""


from __future__ import print_function

import sys
from collections import defaultdict

from . import get_settings, get_bucket_conn, parse_package, get_package_version


def prefer_wheels(package_releases, package, release=None):
    """Given a list of packages, prefer a single wheel if not overridden.

    Args::

        package_releases: a list of S3 keys for package releases
        package: string package name (used for error reporting)
        release: string release requested or None (used for error reporting)

    Returns:
        a single key if it was possible to reduce to one, or None
    """

    versioned = defaultdict(list)
    for package_release in package_releases:
        package_version = get_package_version(package_release, package)
        versioned[package_version].append(package_release)

    # compare versions with pkg_resources.parse_version, find newest
    ver_order = sorted(versioned)
    packages = versioned[ver_order[-1]]

    wheels = []
    eggs = []
    sources = []
    for pkg in packages:
        if pkg.name.endswith(".whl"):
            wheels.append(pkg)
        elif pkg.name.endswith(".egg"):
            eggs.append(pkg)
        else:
            sources.append(pkg)

    if ("--src" in sys.argv and len(sources) == 1) or len(packages) == 1:
        return sources[0]
    elif (not wheels or "--egg" in sys.argv) and len(eggs) == 1:
        return eggs[0]
    elif len(wheels) == 1:
        return wheels[0]
    else:
        raise SystemExit("Found too many results for {}{}:\n  {}".format(
            package,
            "={}".format(release) if release else "",
            "\n  ".join([key.name for key in packages]),
        ))


def download_package(bucket, package, release=None):
    """Gets the download URL for a package, optionally package+release.

    Args:
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
            if release is None or release in key.name.partition("/")[2]:
                package_releases.append(key)

    if len(package_releases) == 1:
        package_key = package_releases[0]
    elif package_releases:
        package_key = prefer_wheels(package_releases, package, release)
    else:
        raise SystemExit("Package {}{} not found".format(
            package,
            "={}".format(release) if release else "",
        ))

    write_key(package_key)


def write_key(key):
    """Writes the key to file or sys.stdout.

    If it can write to a file, it will print the filename to stdout.
    """

    if "--url-only" in sys.argv or "--url" in sys.argv:
        print(key.generate_url(300))  # good for 5 minutes
    else:
        if sys.stdout.isatty():
            # open a file and stream the content into it
            filename = key.name.split("/")[1]
            with open(filename, "wb") as openpackage:
                key.get_contents_to_file(openpackage)
            print(filename)
        else:
            # stdout is being piped/redirected somewhere, write to it directly
            key.get_contents_to_file(sys.stdout)


def main():
    """Main command line entry point for downloading."""

    settings = get_settings(download=True)
    bucket = get_bucket_conn(settings.s3)

    for package in settings.items:
        try:
            download_package(bucket, *parse_package(package))
        except Exception as error:
            print("Error downloading {}: {}".format(package, error),
                  file=sys.stderr)
            break

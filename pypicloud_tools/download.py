"""PyPICloud downloader tool to bypass PyPICloud and pull directly from S3."""


from __future__ import print_function

import sys
from collections import defaultdict
from pkg_resources import safe_name

from . import get_settings
from . import get_bucket_conn
from .utils import parse_package
from .utils import parse_package_file


def prefer_wheels(package_releases, package):
    """Given a list of packages, prefer a single wheel if not overridden.

    Args::

        package_releases: a list of S3 keys for package releases
        package: parsed package object requested

    Returns:
        a single key if it was possible to reduce to one, or None
    """

    versioned = defaultdict(list)
    for package_release in package_releases:
        package_version = parse_package_file(package_release, package)
        if package_version:
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

    if "--src" in sys.argv and len(sources) == 1:
        return sources[0]
    elif (not wheels or "--egg" in sys.argv) and len(eggs) == 1:
        return eggs[0]
    elif len(wheels) == 1:
        return wheels[0]
    else:
        raise SystemExit("Found too many results for {}{}:\n  {}".format(
            package.project_name,
            package.specifier,
            "\n  ".join([key.name for key in packages]),
        ))


def download_package(bucket, package):
    """Gets the download URL for a package, optionally package+release.

    Args:
        bucket: a connected S3 bucket object to look for package in
        package: parsed package object

    Returns:
        string URL to download the package at release or latest
    """

    # figure out key name from package and release requested and what's
    # available in the bucket...
    package_releases = []
    for key in bucket.get_all_keys():
        key_base, _, key_name = key.name.partition("/")
        if not key_name or safe_name(key_base) != package.project_name:
            continue
        key_pkg = parse_package_file(key_name, package)
        if package.project_name == key_pkg.project_name:
            for spec in package.specs:
                if not spec[0](key_pkg.specs[0][1], spec[1]):
                    break
            else:
                package_releases.append(key)

    if len(package_releases) == 1:
        package_key = package_releases[0]
    elif package_releases:
        package_key = prefer_wheels(package_releases, package)
    else:
        raise SystemExit("Package {}{} not found".format(
            package.project_name,
            package.specifier,
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
            download_package(bucket, parse_package(package))
        except Exception as error:
            print("Error downloading {}: {}".format(package, error),
                  file=sys.stderr)
            break

"""Contstants and helpers common to multiple operations.

Copyright (c) 2015 CCP Games. Released for use under the MIT license.
"""


from __future__ import print_function

import os
import re
import sys
import boto
import argparse
import ConfigParser
from boto.s3.key import Key
from collections import namedtuple
from pkg_resources import SetuptoolsVersion, parse_version


# standarized config objects
S3Config = namedtuple("S3Config", ("bucket", "access", "secret", "acl"))
PyPIConfig = namedtuple("PyPIConfig", ("server", "user", "password"))
Settings = namedtuple("Settings", ("s3", "pypi", "items"))


# used as a callback to show some progress to stdout
print_dot = lambda x, y : print(".", end="")


# command line usage
USAGE="""
    {called_as} [options] <FILE> [FILE] ...

Reads {pypirc} (override with --config) for the section and extra keys:

[pypicloud]
    repository:http://your.pypicloud.server/pypi
    username:admin
    password:hunter7
    bucket:your_bucket
    access:some_key
    secret:other_key
    acl:optional_acl

Note:

    To talk directly to S3, you need the `bucket`, `access` and `secret` values
    filled in. The ACL defined here is your default, you can override per file
    via the --acl flag, which takes precendence.
""".format(
    called_as=os.path.basename(sys.argv[0]),
    pypirc=os.path.join(os.path.expanduser("~"), ".pypirc")
)


def get_bucket_conn(s3_config):
    """Uses a S3Config and boto to return a bucket connection object."""

    s3_conn = boto.connect_s3(s3_config.access, s3_config.secret)
    return s3_conn.get_bucket(s3_config.bucket)


def settings_from_config(options):
    """Try to read config file and parse settings.

    Args:
        options: parsed NameSpace, with `config` and maybe `acl` values

    Returns:
        tuple of S3Config and PyPIConfig objects, or Nones when missing values
    """

    parser = ConfigParser.RawConfigParser()

    if isinstance(options.config, list):
        config_file = options.config[0]
    else:
        config_file = options.config

    try:
        parser.read(config_file)
    except Exception as error:
        print(error, file=sys.stderr)

    key = "pypicloud"  # config section key
    if not key in parser.sections():
        return None, None

    s3_conf = None
    pypi_conf = None

    s3_required = ("bucket", "access", "secret")
    pypi_required = ("repository", "username", "password")

    if all([parser.has_option(key, opt) for opt in s3_required]):
        if getattr(options, "acl", None):
            acl = options.acl[0]
        elif parser.has_option(key, "acl"):
            acl = parser.get(key, "acl")
        else:
            acl = None

        s3_conf = S3Config(
            parser.get(key, "bucket"),
            parser.get(key, "access"),
            parser.get(key, "secret"),
            acl,
        )

    if all([parser.has_option(key, opt) for opt in pypi_required]):
        pypi_conf = PyPIConfig(
            parser.get(key, "repository"),
            parser.get(key, "username"),
            parser.get(key, "password"),
        )

    return s3_conf, pypi_conf


def parse_args(upload=False, download=False, listing=False):
    """Builds an argparse ArgumentParser.

    Returns:
        tuple of parse settings and argument parser object
    """

    if upload:
        verb = "upload"
        direction = "to"
        s3_flags = ("access", "bucket", "secret", "acl")
        remainders = ("files", " to PyPICloud's S3 bucket directly")
    else:
        verb = "download" if download else "list"
        direction = "from"
        s3_flags = ("access", "bucket", "secret")
        remainders = ("packages", ", use Package=N.N.N for a specific version")

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description="{} package(s) {} S3, bypassing PyPICloud".format(
            verb.title(),
            direction,
        ),
        usage=USAGE,
    )

    for flag in s3_flags:
        parser.add_argument(
            "--{}".format(flag),
            metavar=flag.upper(),
            help="Specify the S3 {} key value for this {}".format(flag, verb),
            nargs=1,
            type=str,
            default=False,
        )

    for flag in ("server", "user", "password"):
        parser.add_argument(
            "--{}".format(flag),
            metavar=flag.upper(),
            help="Specify the PyPICloud {} for this {}".format(flag, verb),
            nargs=1,
            type=str,
            default=False,
        )

    parser.add_argument(
        "--config",
        metavar="FILE",
        nargs=1,
        type=str,
        default=os.path.join(os.path.expanduser("~"), ".pypirc"),
        help="Specify a config file (default: %(default)s)",
    )

    parser.add_argument(
        dest=remainders[0],
        metavar=remainders[0].upper(),
        help="{}(s) to {}{}".format(
            remainders[0].title(),
            verb,
            remainders[1],
        ),
        nargs=argparse.REMAINDER,
    )

    return parser.parse_args(sys.argv[1:]), parser


def get_settings(upload=False, download=False, listing=False):
    """Gathers both settings for S3 and PyPICloud.

    Args:
        upload: boolean of if this is an upload
        download: boolean of if this is a download
        listing: boolean of if this is a listing

    Returns:
        a Settings object with `s3` and `pypi` attributes
    """

    if len([key for key in (upload, download, listing) if key]) != 1:
        raise RuntimeError("Expecting a single boolean argument to be True!")

    args, parser = parse_args(upload, download, listing)

    if hasattr(args, "files"):
        remainders = args.files
    else:
        remainders = args.packages

    # ignore --long-opts which might be used per-module inline from sys.argv
    remainders = [rem for rem in remainders if not rem.startswith("--")]

    if not remainders and not listing:
        raise SystemExit(parser.print_help())

    if args.bucket and args.access and args.secret:
        if hasattr(args, "acl") and args.acl:
            acl = args.acl[0]
        else:
            acl = None
        s3_config = S3Config(args.bucket[0], args.access[0], args.secret[0], acl)
    else:
        s3_config = None

    if args.server and args.user and args.password:
        pypi_config = PyPIConfig(args.server[0], args.user[0], args.password[0])
    else:
        pypi_config = None

    configfile_s3, configfile_pypi = settings_from_config(args)
    if configfile_s3 and s3_config is None:
        s3_config = configfile_s3
    if configfile_pypi and pypi_config is None:
        pypi_config = configfile_pypi

    if s3_config is None:
        print("ERROR: Could not determine S3 settings.", file=sys.stderr)
        raise SystemExit(parser.print_help())

    return Settings(s3_config, pypi_config, remainders)


def parse_package(package):
    """Parse `package` string to package name and package version."""

    if package and "=" in package:
        # would like to use left-side unpacking, but old python support :`(
        p_split = package.split("=")
        return p_split[0].strip(), p_split[-1].strip()
    else:
        return package, None


def get_package_version(key, package):
    """Parse out pkg_resources.SetuptoolsVersion objects from key.name.

    Args:
        key: a S3 Key object from boto or a string filename
        package: the string package name without version
    """

    pattern = "\.|-"
    if isinstance(key, Key):
        version = re.split(pattern, key.name[(len(package) * 2) + 2:])
    else:
        version = re.split(pattern, key[len(package) + 1:])

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

    return parse_version(pkg_ver)

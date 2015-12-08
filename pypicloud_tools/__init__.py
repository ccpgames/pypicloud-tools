"""Contstants and helpers common to multiple operations."""


from __future__ import print_function

import os
import sys
import boto
import argparse
import datetime
import operator
import pkg_resources
from collections import namedtuple
from pip.utils import SUPPORTED_EXTENSIONS
from boto.exception import NoAuthHandlerFound

try:
    from configparser import RawConfigParser  # python 3+
except ImportError:  # pragma: no cover
    from ConfigParser import RawConfigParser


# standarized config objects
PyPIConfig = namedtuple("PyPIConfig", ("server", "user", "password"))
Settings = namedtuple("Settings", ("s3", "pypi", "items", "parsed"))
S3Config = namedtuple(
    "S3Config",
    ("bucket", "access", "secret", "acl", "region"),
)

# Supported Extensions for uploading, downloading, listing, rehosting..
SUPPORTED_EXTENSIONS = tuple(list(SUPPORTED_EXTENSIONS) +
                             [".egg", ".exe", ".msi"])

# used to preform version comparisons
OPERATORS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
}

# used as a callback to show some progress to stdout
print_dot = lambda x, y: print(".", end="")


# command line usage
USAGE = """
    {called_as} [options] <FILE> [FILE] ...

Reads {pypirc} (override with --config) for the section and extra keys:

[pypicloud]
    repository:http://your.pypicloud.server/pypi
    username:admin
    password:hunter7
    bucket:your_bucket
    access:some_key
    secret:other_key
    region:aws_region
    acl:optional_acl

Note:

    To talk directly to S3, you need the `bucket`, `region` and/or `access`
    and `secret` values filled in. The ACL defined here is your default, you
    can override per file via the --acl flag, which takes precendence.

    AWS Access_Key and Secret_Key can also optionally be read from your
    credentials file at ~/.aws/credentials.
""".format(
    called_as=os.path.basename(sys.argv[0]),
    pypirc=os.path.join(os.path.expanduser("~"), ".pypirc")
)


def get_bucket_conn(s3_config):
    """Uses a S3Config and boto to return a bucket connection object."""

    no_auth_error = ("Could not authenticate with S3. Check your "
                     "~/.aws/credentials or pass --access and --secret flags.")

    if s3_config.region is None:
        func = boto.connect_s3
        args = (s3_config.access, s3_config.secret)
    else:
        func = boto.s3.connect_to_region
        args = (s3_config.region,)

    try:
        s3_conn = func(*args)
    except NoAuthHandlerFound:
        raise SystemExit(no_auth_error)

    return s3_conn.get_bucket(s3_config.bucket)


def settings_from_config(options):
    """Try to read config file and parse settings.

    Args:
        options: parsed NameSpace, with `config` and maybe `acl` values

    Returns:
        tuple of S3Config and PyPIConfig objects, or Nones when missing values
    """

    parser = RawConfigParser()

    if isinstance(options.config, list):
        config_file = options.config[0]
    else:
        config_file = options.config

    try:
        parser.read(config_file)
    except Exception as error:
        print(error, file=sys.stderr)

    key = "pypicloud"  # config section key
    if key not in parser.sections():
        return None, None

    s3_conf = None
    pypi_conf = None

    pypi_required = ("repository", "username", "password")

    if parser.has_option(key, "bucket"):
        acl = access = secret = region = None
        if getattr(options, "acl", None):
            acl = options.acl[0]
        elif parser.has_option(key, "acl"):
            acl = parser.get(key, "acl")

        if parser.has_option(key, "region"):
            region = parser.get(key, "region")

        if parser.has_option(key, "secret"):
            secret = parser.get(key, "secret")

        if parser.has_option(key, "access"):
            access = parser.get(key, "access")

        s3_conf = S3Config(
            parser.get(key, "bucket"),
            access,
            secret,
            acl,
            region,
        )

    if all([parser.has_option(key, opt) for opt in pypi_required]):
        pypi_conf = PyPIConfig(
            parser.get(key, "repository"),
            parser.get(key, "username"),
            parser.get(key, "password"),
        )

    return s3_conf, pypi_conf


def parse_args(upload=False, download=False, listing=False, rehost=False):
    """Builds an argparse ArgumentParser.

    Returns:
        tuple of parse settings and argument parser object
    """

    if upload:
        verb = "upload"
        direction = "to"
        s3_flags = ("bucket", "access", "secret", "acl", "region")
        remainders = ("files", " to PyPICloud's S3 bucket directly")
    elif rehost:
        verb = "rehost"
        direction = "to"
        s3_flags = ("bucket", "access", "secret", "acl", "region")
        remainders = ("packages", ", use ==N.N.N for a specific version")
    else:
        verb = "download" if download else "list"
        direction = "from"
        s3_flags = ("bucket", "access", "secret", "region")
        remainders = ("packages", ", use ==N.N.N for a specific version")

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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

    if rehost:
        parser.add_argument(
            "--deps", "--with-deps",
            action="store_true",
            help="Rehost the package(s) dependencies as well",
        )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=(
            "pypicloud-tools %(prog)s v{}\n"
            "Copyright (c) {} CCP hf.\n"
            "Released for use under the MIT license."
        ).format(
            pkg_resources.get_distribution("pypicloud-tools").version,
            datetime.datetime.now().year,
        ),
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


def get_settings(upload=False, download=False, listing=False, rehost=False):
    """Gathers both settings for S3 and PyPICloud.

    Args:
        upload: boolean of if this is an upload
        download: boolean of if this is a download
        listing: boolean of if this is a listing

    Returns:
        a Settings object with `s3` and `pypi` attributes
    """

    if len([key for key in (upload, download, listing, rehost) if key]) != 1:
        raise RuntimeError("Expecting a single boolean argument to be True!")

    args, parser = parse_args(upload, download, listing, rehost)

    if hasattr(args, "files"):
        remainders = args.files
    else:
        remainders = args.packages

    # ignore --long-opts which might be used per-module inline from sys.argv
    remainders = [rem for rem in remainders if not rem.startswith("--")]

    if not remainders and not listing:
        raise SystemExit(parser.print_help())

    if args.bucket:
        acl = access = secret = region = None
        if hasattr(args, "region") and args.region:
            region = args.region[0]
        if hasattr(args, "access") and args.access:
            access = args.access[0]
        if hasattr(args, "secret") and args.secret:
            secret = args.secret[0]
        if hasattr(args, "acl") and args.acl:
            acl = args.acl[0]
        s3_config = S3Config(args.bucket[0], access, secret, acl, region)
    else:
        s3_config = None

    if args.server and args.user and args.password:
        pypi_config = PyPIConfig(
            args.server[0],
            args.user[0],
            args.password[0],
        )
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

    return Settings(s3_config, pypi_config, remainders, args)

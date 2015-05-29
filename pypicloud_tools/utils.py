"""Pypicloud-tools common utility functions."""


from boto.s3.key import Key
from pip.wheel import Wheel
from pip.wheel import wheel_ext
from pip.index import egg_info_matches
from pkg_resources import safe_name
from pkg_resources import SetuptoolsVersion
from pkg_resources import parse_requirements

from . import OPERATORS
from . import SUPPORTED_EXTENSIONS


def parse_package(package):
    """Parse `package` string to package name and package specs.

    Args:
        package: a string, maybe with acceptable version specification(s)

    Returns:
        parsed package requirement object
    """

    if not package:
        return None

    parsed = list(parse_requirements(package))[0]
    specs = []
    for spec in parsed.specs:
        specs.append((OPERATORS[spec[0]], SetuptoolsVersion(spec[1])))
    parsed.specs = specs
    return parsed


def parse_package_file(file_name, package):
    """Builds a parsed package requirement object from a filename.

    Args:
        file_name: a string filename or boto Key object
        package: parsed package requirement object this file is part of
    """

    if isinstance(file_name, Key):
        file_name = file_name.name.partition("/")[2]

    if not file_name or package.project_name not in safe_name(file_name):
        return

    for ext in SUPPORTED_EXTENSIONS:
        if not file_name.endswith(ext):
            continue
        # specifically not using os.path.split to get .tar.gz
        file_ = file_name.rsplit(ext)[0]

        if ext == wheel_ext:
            wheel = Wheel(file_name)

            # wheel won't consider -alpha -dev, etc.. in the version
            ver = wheel.version
            for tag_group in wheel.file_tags:
                for tag in tag_group:
                    try:
                        ver = SetuptoolsVersion("{}-{}".format(ver, tag))
                    except:
                        break
                break

            return parse_package("{}=={}".format(wheel.name, ver))
        else:
            pkg_name = package.project_name
            firstrun = True
            while "-" in file_ or firstrun:
                firstrun = False
                try:
                    return parse_package("{}=={}".format(
                        pkg_name,
                        egg_info_matches(file_, pkg_name, pkg_name),
                    ))
                except Exception:
                    file_ = file_.rpartition("-")[0]

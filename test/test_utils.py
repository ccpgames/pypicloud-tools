import pytest
from pkg_resources import SetuptoolsVersion

from pypicloud_tools import OPERATORS
from pypicloud_tools.utils import parse_package


@pytest.mark.parametrize(
    "package, pkg_name, extras, version",
    [
        ("foo-bar", "foo-bar", (), []),
        ("foo-bar==0.0.1", "foo-bar", (), [("==", "0.0.1")]),
        (
            "foo-bar.baz[stuff]==1.2.3",
            "foo-bar.baz",
            ("stuff",),
            [("==", "1.2.3")],
        ),
    ],
    ids=("no version", "simple version", "with extra"),
)
def test_parse_package(package, pkg_name, extras, version):
    """Ensure package strings are properly parsed."""

    pkg = parse_package(package)
    assert pkg.project_name == pkg_name
    assert pkg.extras == extras

    specs = []
    for spec in version:
        specs.append((OPERATORS[spec[0]], SetuptoolsVersion(spec[1])))
    assert pkg.specs == specs


def test_parse_package__empty_string():
    """Parsing an empty string should result in a None object."""

    assert parse_package("") is None


if __name__ == "__main__":
    pytest.main(["-v", "-rx", "--pdb", __file__])

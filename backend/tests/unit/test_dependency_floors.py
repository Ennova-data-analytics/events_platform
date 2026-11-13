"""
The web stack must not slide back below the releases that fixed the
multipart/form-data denial-of-service advisories: the recruitment and upload
forms are public. If a lock-file change downgrades one of these, this fails.
"""
from importlib.metadata import version

import pytest

FLOORS = {
    "fastapi": (0, 162, 0),
    "starlette": (1, 10, 0),
    "python-multipart": (0, 0, 33),
}


def as_tuple(text):
    return tuple(int(part) for part in text.split(".")[:3] if part.isdigit())


@pytest.mark.parametrize("package, floor", FLOORS.items())
def test_installed_version_is_at_least_the_patched_one(package, floor):
    assert as_tuple(version(package)) >= floor, f"{package} {version(package)} is older than {floor}"


def test_as_tuple_compares_numerically():
    assert as_tuple("0.0.33") > as_tuple("0.0.9")
    assert as_tuple("1.10.0") > as_tuple("1.9.4")

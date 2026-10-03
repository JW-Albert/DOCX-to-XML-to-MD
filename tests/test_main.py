import pytest
from main import add, greet


# --- Basic tests ---
def test_add_positive():
    assert add(1, 2) == 3


def test_add_negative():
    assert add(-1, -2) == -3


def test_add_zero():
    assert add(0, 0) == 0


# --- Parametrize example ---
@pytest.mark.parametrize("a, b, expected", [
    (1, 2, 3),
    (0, 5, 5),
    (-3, 3, 0),
    (100, -1, 99),
])
def test_add_parametrized(a, b, expected):
    assert add(a, b) == expected


# --- Fixture example ---
@pytest.fixture
def default_name():
    return "World"


def test_greet_with_fixture(default_name):
    assert greet(default_name) == "Hello, World!"


def test_greet_custom():
    assert greet("Alice") == "Hello, Alice!"

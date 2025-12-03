"""
Simple example to demonstrate how pytest works
"""

# ============================================
# EXAMPLE 1: Basic Test
# ============================================
def test_addition():
    """Pytest will find and run this automatically"""
    result = 1 + 1
    assert result == 2  # ✅ This passes
    print("✅ Addition test passed!")


# ============================================
# EXAMPLE 2: Test That Fails
# ============================================
def test_will_fail():
    """This test will fail to show what happens"""
    result = 10 / 2
    assert result == 10  # ❌ This will fail (5 != 10)


# ============================================
# EXAMPLE 3: Test Class with Multiple Tests
# ============================================
class TestMath:
    """Group related tests together"""

    def test_multiplication(self):
        """Test multiplication"""
        assert 3 * 4 == 12  # ✅ Pass

    def test_division(self):
        """Test division"""
        assert 10 / 2 == 5  # ✅ Pass

    def test_subtraction(self):
        """Test subtraction"""
        assert 10 - 3 == 7  # ✅ Pass


# ============================================
# EXAMPLE 4: Using Fixtures (Setup)
# ============================================
import pytest

@pytest.fixture
def sample_data():
    """This runs BEFORE each test that uses it"""
    print("🔧 Setting up test data...")
    data = {"name": "Test", "value": 42}
    return data

def test_with_fixture(sample_data):
    """Pytest automatically provides sample_data"""
    assert sample_data["name"] == "Test"
    assert sample_data["value"] == 42


# ============================================
# EXAMPLE 5: Testing Exceptions
# ============================================
def test_exception_handling():
    """Test that code raises expected errors"""
    with pytest.raises(ZeroDivisionError):
        result = 1 / 0  # This SHOULD raise an error


# ============================================
# Functions pytest IGNORES (don't start with test_)
# ============================================
def helper_function():
    """Pytest ignores this - it's just a helper"""
    return "I'm not a test!"

class RegularClass:
    """Pytest ignores this - doesn't start with 'Test'"""
    def some_method(self):
        pass

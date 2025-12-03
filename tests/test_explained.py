"""
Detailed walkthrough of how a real test works
"""
import pytest
import json
from pathlib import Path

# ============================================
# STEP 1: Define a simple function to test
# ============================================
def calculate_packet_loss(sent, received):
    """Calculate packet loss percentage"""
    if sent == 0:
        return 100.0
    loss = ((sent - received) / sent) * 100
    return round(loss, 2)


# ============================================
# STEP 2: Write tests for this function
# ============================================
class TestPacketLoss:
    """
    When pytest runs:
    1. Creates instance: test_obj = TestPacketLoss()
    2. Finds all methods starting with 'test_'
    3. Calls each: test_obj.test_no_loss()
    """

    def test_no_loss(self):
        """Test when all packets received"""
        # Execute the function
        result = calculate_packet_loss(sent=10, received=10)

        # Check result
        assert result == 0.0  # ✅ Should be 0% loss
        print(f"   📊 No loss: {result}%")

    def test_partial_loss(self):
        """Test when some packets lost"""
        result = calculate_packet_loss(sent=100, received=95)

        assert result == 5.0  # ✅ Should be 5% loss
        print(f"   📊 Partial loss: {result}%")

    def test_total_loss(self):
        """Test when all packets lost"""
        result = calculate_packet_loss(sent=10, received=0)

        assert result == 100.0  # ✅ Should be 100% loss
        print(f"   📊 Total loss: {result}%")

    def test_edge_case_zero_sent(self):
        """Test edge case: no packets sent"""
        result = calculate_packet_loss(sent=0, received=0)

        assert result == 100.0  # ✅ Edge case handled
        print(f"   📊 Zero sent: {result}%")


# ============================================
# STEP 3: Using Fixtures (Advanced)
# ============================================
@pytest.fixture
def mock_ping_result():
    """
    This runs BEFORE each test that requests it
    Pytest automatically injects the return value
    """
    print("   🔧 Creating mock ping result...")
    return {
        "packets_sent": 20,
        "packets_received": 18,
        "min_ms": 10.5,
        "max_ms": 25.3,
        "avg_ms": 15.7
    }


def test_using_fixture(mock_ping_result):
    """
    Pytest sees 'mock_ping_result' parameter
    → Finds fixture with that name
    → Runs fixture function
    → Passes return value to test
    """
    print(f"   📦 Received data: {mock_ping_result}")

    # Now we can use the mock data
    assert mock_ping_result["packets_sent"] == 20
    assert mock_ping_result["packets_received"] == 18

    # Calculate loss from mock data
    loss = calculate_packet_loss(
        mock_ping_result["packets_sent"],
        mock_ping_result["packets_received"]
    )
    assert loss == 10.0  # ✅ (20-18)/20 * 100 = 10%
    print(f"   ✅ Calculated loss: {loss}%")


# ============================================
# STEP 4: Parametrized Tests (Run same test with different data)
# ============================================
@pytest.mark.parametrize("sent,received,expected", [
    (10, 10, 0.0),      # No loss
    (100, 95, 5.0),     # 5% loss
    (100, 50, 50.0),    # 50% loss
    (20, 0, 100.0),     # Total loss
])
def test_multiple_scenarios(sent, received, expected):
    """
    Pytest will run this test 4 times, once for each parameter set
    """
    result = calculate_packet_loss(sent, received)
    assert result == expected
    print(f"   📊 Sent:{sent}, Received:{received} → Loss:{result}% (expected:{expected}%)")


# ============================================
# STEP 5: What pytest IGNORES
# ============================================
def helper_calculate_average(numbers):
    """
    This is NOT a test (doesn't start with 'test_')
    Pytest ignores it - it's just a helper function
    """
    return sum(numbers) / len(numbers)


class DataProcessor:
    """
    This is NOT a test class (doesn't start with 'Test')
    Pytest ignores it completely
    """
    def process(self, data):
        return data * 2

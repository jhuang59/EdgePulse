"""
Your first test - try modifying this!
"""

def test_your_name():
    """Change this to test your own name"""
    my_name = "YOUR_NAME_HERE"  # ← Change this
    assert len(my_name) > 0
    assert isinstance(my_name, str)
    print(f"✅ Hello, {my_name}!")


def test_math():
    """Try changing the numbers"""
    x = 10
    y = 5
    assert x + y == 15
    assert x - y == 5
    assert x * y == 50
    print(f"✅ Math works: {x} + {y} = {x+y}")


def test_lists():
    """Test list operations"""
    my_list = [1, 2, 3]
    my_list.append(4)

    assert len(my_list) == 4
    assert 4 in my_list
    assert my_list[-1] == 4  # Last element
    print(f"✅ List is now: {my_list}")


# Try making this fail by changing the assertion!
def test_intentional_fail():
    """This should pass - try making it fail"""
    result = 100 / 10
    assert result == 10  # Change the number to make it fail!

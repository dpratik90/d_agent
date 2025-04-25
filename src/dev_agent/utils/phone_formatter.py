import re
from typing import Optional

def format_phone_number(phone_number: str) -> str:
    """
    Format a phone number into the standard US format (XXX-XXX-XXXX).
    
    Args:
        phone_number (str): The phone number to format. Can contain various separators
                           like spaces, dots, parentheses, or dashes.
    
    Returns:
        str: The formatted phone number in XXX-XXX-XXXX format.
    
    Raises:
        ValueError: If the phone number is invalid (not 10 digits after removing non-numeric characters).
    """
    # Remove all non-numeric characters
    digits = re.sub(r'\D', '', phone_number)
    
    # Check if number is valid according to NA format
    if len(digits) != 10:
        raise ValueError(
            f"Invalid phone number: '{phone_number}'. "
            "Please enter a 10-digit US phone number."
        )

    # Format phone number in XXX-XXX-XXXX format
    return '-'.join([digits[:3], digits[3:6], digits[6:]])

def validate_phone_number(phone_number: str) -> bool:
    """
    Validate if a phone number is in a valid US format.
    
    Args:
        phone_number (str): The phone number to validate.
    
    Returns:
        bool: True if the phone number is valid, False otherwise.
    """
    try:
        format_phone_number(phone_number)
        return True
    except ValueError:
        return False

if __name__ == "__main__":
    # Example usage
    test_numbers = [
        "(123) 456-7890",
        "123.456.7890",
        "1234567890",
        "12345",
        "1-800-555-1234"
    ]
    
    for number in test_numbers:
        try:
            formatted = format_phone_number(number)
            print(f"Input: {number:<15} -> Formatted: {formatted}")
        except ValueError as e:
            print(f"Input: {number:<15} -> Error: {str(e)}")
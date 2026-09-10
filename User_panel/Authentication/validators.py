import re
from django.core.validators import validate_email as django_validate_email
from django.core.exceptions import ValidationError


def validate_password(password, confirm_password=None):
    if not password:
        return "Password is required."

    if len(password) < 8:
        return "Password should contain minimum 8 characters."

    if len(password) > 128:
        return "Password cannot exceed 128 characters."

    if password != password.strip():
        return "Password cannot start or end with spaces."

    if not re.search(r"[A-Z]", password):
        return "Password should contain at least one uppercase letter."

    if not re.search(r"[a-z]", password):
        return "Password should contain at least one lowercase letter."

    if not re.search(r"\d", password):
        return "Password should contain at least one number."

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\[\]\\\/+=~`;\-]', password):
        return "Password should contain at least one special character."

    if confirm_password is not None and password != confirm_password:
        return "Passwords do not match."

    return None


def validate_name(name, field_name="Name"):
    name = name.strip()

    if not name:
        return f"Enter {field_name}."

    if len(name) < 3:
        return f"{field_name} should contain minimum 3 characters."

    if len(name) > 100:
        return f"{field_name} cannot exceed 100 characters."

    name_pattern = r"^[A-Za-z][A-Za-z\s'-]*$"

    if not re.fullmatch(name_pattern, name):
        return f"{field_name} can contain only letters, spaces, apostrophes and hyphens."

    return None


def validate_email_address(email):
    email = email.strip().lower()

    if not email:
        return "Enter Email."

    try:
        django_validate_email(email)
    except ValidationError:
        return "Invalid Email Address."

    if len(email) > 254:
        return "Email Address cannot exceed 254 characters."

    return None


def validate_phone_number(phone_number):
    phone_number = phone_number.strip()

    if not phone_number:
        return "Phone number is required."

    if not re.fullmatch(r"^[6-9]\d{9}$", phone_number):
        return "Phone number must be a valid 10-digit mobile number."

    return None


def validate_signup(fullname, email, password, confirm_password):
    fullname = fullname.strip()
    email = email.strip().lower()

    error = validate_name(fullname, "Name")

    if error:
        return error

    error = validate_email_address(email)

    if error:
        return error

    error = validate_password(
        password,
        confirm_password
    )

    if error:
        return error

    return None


def validate_address(data):
    full_name = data.get("full_name", "").strip()
    phone_number = data.get("phone_number", "").strip()
    address_line1 = data.get("address_line1", "").strip()
    address_line2 = data.get("address_line2", "").strip()
    city = data.get("city", "").strip()
    state = data.get("state", "").strip()
    pincode = data.get("pincode", "").strip()
    country = data.get("country", "").strip()
    address_type = data.get("type", "").strip()

    error = validate_name(full_name, "Full name")

    if error:
        return error

    error = validate_phone_number(phone_number)

    if error:
        return error

    if not address_line1:
        return "Street address is required."

    if len(address_line1) > 255:
        return "Street address cannot exceed 255 characters."

    if address_line2 and len(address_line2) > 255:
        return "Address Line 2 cannot exceed 255 characters."

    error = validate_name(city, "City")

    if error:
        return error

    error = validate_name(state, "State")

    if error:
        return error

    if not re.fullmatch(r"^\d{6}$", pincode):
        return "Pincode must contain exactly 6 digits."

    error = validate_name(country, "Country")

    if error:
        return error

    if address_type not in {"Home", "Office", "Other"}:
        return "Please select a valid address type."

    return None
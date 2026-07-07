import re


def validate_signup(fullname, email, password, confirm_password):
    fullname = fullname.strip()
    email = email.strip().lower()

    if fullname == "":
        return "Enter Full Name"

    if len(fullname) < 3:
        return "Name should contain minimum 3 characters"

    name_pattern = r"^[A-Za-z][A-Za-z\s'-]*$"

    if not re.fullmatch(name_pattern, fullname):
        return "Name can contain only letters, spaces, apostrophes and hyphens"

    if email == "":
        return "Enter Email"

    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

    if not re.fullmatch(email_pattern, email):
        return "Invalid Email Address"

    if len(password) < 8:
        return "Password should contain minimum 8 characters"

    if password != confirm_password:
        return "Passwords do not match"

    return None
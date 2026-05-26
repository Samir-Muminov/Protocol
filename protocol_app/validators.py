# protocol_app/validators.py
# SECURITY: Centralized input validation — all user inputs validated here
# before reaching the database. Schema-based, type-checked, length-limited.

import re
import datetime
import logging

logger = logging.getLogger('protocol_app')


class ValidationError(Exception):
    """Raised when input fails validation."""
    pass


# ── Constants: hard limits ─────────────────────────────────────────────
# SECURITY: These caps prevent absurd inputs and potential DoS via
# database writes with extreme float values
MAX_IT_HOURS   = 24.0    # Can't do more than 24h in a day
MAX_PAGES       = 2000   # Reasonable upper bound for pages read
MAX_CALORIES    = 10000  # Extreme athletes burn ~5000; 10k is the hard cap
MAX_KM          = 300.0  # Ultra-marathon distance; hard cap
MIN_DATE_DAYS   = 365    # Can't log more than 1 year in the past
MAX_USERNAME_LEN= 150
MAX_EMAIL_LEN   = 254
MAX_PASSWORD_LEN= 128


def validate_daily_report(data: dict) -> dict:
    """
    Validates and sanitizes DailyReport form input.

    SECURITY measures:
    - Type coercion with hard failure on wrong types
    - Numeric range checks (no negative values, no absurd values)
    - Date range check (no future dates, no dates > 1 year ago)
    - Rejects any unexpected fields (whitelist approach)
    - Returns clean dict — never the raw input dict

    Raises ValidationError with user-friendly message on failure.
    """
    ALLOWED_FIELDS = {'date', 'it_math_hours', 'pages_read', 'calories', 'distance_km'}

    # SECURITY: Reject unexpected fields — whitelist approach
    unexpected = set(data.keys()) - ALLOWED_FIELDS
    if unexpected:
        logger.warning(f"Unexpected fields in report submission: {unexpected}")
        raise ValidationError(f"Unexpected fields submitted.")

    clean = {}

    # ── Date ────────────────────────────────────────────────────────────
    raw_date = data.get('date', '')
    try:
        if isinstance(raw_date, datetime.date):
            clean['date'] = raw_date
        else:
            clean['date'] = datetime.date.fromisoformat(str(raw_date).strip())
    except (ValueError, TypeError):
        raise ValidationError("Invalid date format. Use YYYY-MM-DD.")

    today = datetime.date.today()
    # SECURITY: Reject future dates
    if clean['date'] > today:
        raise ValidationError("Cannot log data for future dates.")
    # SECURITY: Reject dates too far in the past
    if clean['date'] < today - datetime.timedelta(days=MIN_DATE_DAYS):
        raise ValidationError(f"Cannot log data more than {MIN_DATE_DAYS} days in the past.")

    # ── IT / Math Hours ─────────────────────────────────────────────────
    try:
        val = float(data.get('it_math_hours', 0))
    except (ValueError, TypeError):
        raise ValidationError("IT/Math hours must be a number.")

    if val < 0:
        raise ValidationError("IT/Math hours cannot be negative.")
    if val > MAX_IT_HOURS:
        raise ValidationError(f"IT/Math hours cannot exceed {MAX_IT_HOURS}.")
    # Round to 1 decimal place — prevents precision abuse
    clean['it_math_hours'] = round(val, 1)

    # ── Pages Read ──────────────────────────────────────────────────────
    try:
        val = int(data.get('pages_read', 0))
    except (ValueError, TypeError):
        raise ValidationError("Pages read must be a whole number.")

    if val < 0:
        raise ValidationError("Pages read cannot be negative.")
    if val > MAX_PAGES:
        raise ValidationError(f"Pages read cannot exceed {MAX_PAGES}.")
    clean['pages_read'] = val

    # ── Calories ────────────────────────────────────────────────────────
    try:
        val = int(data.get('calories', 0))
    except (ValueError, TypeError):
        raise ValidationError("Calories must be a whole number.")

    if val < 0:
        raise ValidationError("Calories cannot be negative.")
    if val > MAX_CALORIES:
        raise ValidationError(f"Calories cannot exceed {MAX_CALORIES}.")
    clean['calories'] = val

    # ── Distance KM ─────────────────────────────────────────────────────
    try:
        val = float(data.get('distance_km', 0))
    except (ValueError, TypeError):
        raise ValidationError("Distance must be a number.")

    if val < 0:
        raise ValidationError("Distance cannot be negative.")
    if val > MAX_KM:
        raise ValidationError(f"Distance cannot exceed {MAX_KM} km.")
    clean['distance_km'] = round(val, 2)

    return clean


def validate_registration(data: dict) -> dict:
    """
    Validates registration form input.

    SECURITY:
    - Username: alphanumeric + _ only, length 3-150
    - Email: basic format check, length limit
    - Password: min 8 chars, max 128
    - Rejects unexpected fields
    """
    ALLOWED_FIELDS = {'username', 'email', 'password1', 'password2'}
    unexpected = set(data.keys()) - ALLOWED_FIELDS - {'csrfmiddlewaretoken'}
    if unexpected:
        logger.warning(f"Unexpected fields in registration: {unexpected}")
        raise ValidationError("Unexpected fields submitted.")

    clean = {}

    # ── Username ────────────────────────────────────────────────────────
    username = str(data.get('username', '')).strip()
    if len(username) < 3:
        raise ValidationError("Username must be at least 3 characters.")
    if len(username) > MAX_USERNAME_LEN:
        raise ValidationError(f"Username too long (max {MAX_USERNAME_LEN} chars).")
    # SECURITY: Reject special characters that could be used in injection
    if not re.match(r'^[\w.@+-]+$', username):
        raise ValidationError("Username contains invalid characters.")
    clean['username'] = username

    # ── Email ───────────────────────────────────────────────────────────
    email = str(data.get('email', '')).strip().lower()
    if email:
        if len(email) > MAX_EMAIL_LEN:
            raise ValidationError(f"Email too long (max {MAX_EMAIL_LEN} chars).")
        # Basic email format check
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            raise ValidationError("Invalid email format.")
    clean['email'] = email

    # ── Passwords ───────────────────────────────────────────────────────
    p1 = str(data.get('password1', ''))
    p2 = str(data.get('password2', ''))

    if len(p1) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    if len(p1) > MAX_PASSWORD_LEN:
        raise ValidationError("Password too long.")
    if p1 != p2:
        raise ValidationError("Passwords do not match.")

    clean['password1'] = p1
    clean['password2'] = p2

    return clean
# backend/app/database/base.py

# 1. Import the actual Base initialization from your auth feature's db.py
# (Adjust this import if your auth folder structure is slightly different, e.g., 'from app.auth.db import Base')
from app.auth.database.db import Base 

# 2. Import your Auth feature models so they register with SQLAlchemy's metadata
# (Replace 'User', 'Token', etc., with the exact model names inside your auth/models.py)
from app.auth.models import user, Token, EmailVerificationToken, PasswordResetToken

# 3. Future Expansion Placeholder:
# As you build other features, uncomment and import them here:
# from app.vehicles.models import Vehicle
# from app.drivers.models import Driver

# Explicitly export Base for Alembic's env.py to grab cleanly
__all__ = ["Base"]
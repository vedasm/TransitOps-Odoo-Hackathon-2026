from logging.config import fileConfig
import os
import sys
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# 1. Load environment variables from the backend .env file
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# 2. Add backend root to sys.path so Python can resolve absolute imports starting with 'app.'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 3. Import your central database Base metadata and settings
from app.database.base import Base
from app.core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Provide Alembic access to your target metadata for auto-generation
target_metadata = Base.metadata

def get_url():
    # Prefer the app's settings-driven database URL, falling back to env values.
    if hasattr(settings, "DATABASE_URL"):
        return settings.DATABASE_URL
    return os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    # 1. Grab the generic configuration block from alembic.ini
    configuration = config.get_section(config.config_ini_section) or {}
    
    # 2. OVERWRITE the placeholder URL with your real environment variable
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
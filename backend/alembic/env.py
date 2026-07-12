from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# 1. Import your database Base metadata from your app core
# (Adjust this path depending on where your Base model is declared)
from app.database import Base  

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. Provide Alembic access to your target metadata for auto-generation
target_metadata = Base.metadata

def get_url():
    # Dynamically inject the URL from the environment matrix at runtime
    return os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/dbname")

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
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url() # Inject target string here
    
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
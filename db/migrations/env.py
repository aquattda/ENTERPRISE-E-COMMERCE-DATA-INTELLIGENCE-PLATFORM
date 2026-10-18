from alembic import context
from sqlalchemy import create_engine, pool

from commerce_data.config import get_settings
from commerce_data.storage.models import Base

url = get_settings().database_url.get_secret_value()
if context.is_offline_mode():
    context.configure(
        url=url, target_metadata=Base.metadata, literal_binds=True, include_schemas=True
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=Base.metadata, include_schemas=True
        )
        with context.begin_transaction():
            context.run_migrations()

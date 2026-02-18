from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Example new database URL
OTHER_DATABASE_URL = "postgresql+asyncpg://casino_hack_user:your_password@46.101.223.116:5432/casino_hack_db"

# Create new async engine and sessionmaker
other_engine = create_async_engine(OTHER_DATABASE_URL, echo=False, future=True)
OtherSessionLocal = sessionmaker(
    bind=other_engine,
    expire_on_commit=False,
    class_=AsyncSession
)

import os
from sqlalchemy import create_engine, text

# Load database URL from environment or use default
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dbname')

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    version = result.fetchone()
    if version:
        print(f"Current revision: {version[0]}")
    else:
        print("No alembic version found in database")

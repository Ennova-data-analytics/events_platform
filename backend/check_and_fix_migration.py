#!/usr/bin/env python3
"""Check and fix alembic migration state"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://ennova_test:ennova123@localhost:5432/ennova_db')

print(f"Connecting to database...")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check current version
    try:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.fetchone()
        if version:
            current_version = version[0]
            print(f"✓ Current database revision: {current_version}")

            # Check if it's the problematic revision
            if current_version == 'e1f2g3h4i5j6':
                print("\n⚠ Found problematic revision 'e1f2g3h4i5j6'")
                print("This revision file doesn't exist. Updating to latest valid revision...")

                # Update to the previous known good revision
                conn.execute(text("UPDATE alembic_version SET version_num = 'd9e0f1g2h3i4'"))
                conn.commit()
                print("✓ Updated database to revision 'd9e0f1g2h3i4' (ennova_member_support)")
                print("\nNow you can run: alembic upgrade head")
            else:
                print(f"✓ Revision looks valid")
                print("\nYou can proceed with: alembic upgrade head")
        else:
            print("⚠ No alembic version found in database")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\nDone!")

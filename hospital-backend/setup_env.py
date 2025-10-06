"""
Environment Setup Script for Hospital Management System
Helps create a secure .env file with proper secrets
"""

import os
import secrets
import string
from pathlib import Path


def generate_secret_key(length=64):
    """Generate a cryptographically secure secret key"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_password(length=32):
    """Generate a secure password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_user_input(prompt, default=None, secure=False):
    """Get user input with optional default"""
    if default:
        prompt_text = f"{prompt} [{default}]: "
    else:
        prompt_text = f"{prompt}: "

    if secure:
        prompt_text += "\n  (Leave blank to auto-generate a secure value)\n  > "
    else:
        prompt_text += ""

    user_input = input(prompt_text).strip()

    if not user_input and default:
        return default

    return user_input


def setup_env():
    """Interactive .env file setup"""
    print("=" * 80)
    print("HOSPITAL MANAGEMENT SYSTEM - ENVIRONMENT SETUP")
    print("=" * 80)
    print("\nThis script will help you create a secure .env file")
    print("Press Enter to use default values or enter custom values")
    print()

    # Check if .env already exists
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        response = input("\n.env file already exists! Overwrite? (y/N): ").strip().lower()
        if response != 'y':
            print("Setup cancelled. Your existing .env file is unchanged.")
            return

    config = {}

    # Database Configuration
    print("\n" + "=" * 80)
    print("DATABASE CONFIGURATION")
    print("=" * 80)

    config['DATABASE_HOST'] = get_user_input("Database Host", "localhost")
    config['DATABASE_PORT'] = get_user_input("Database Port", "5432")
    config['DATABASE_NAME'] = get_user_input("Database Name", "hospital_management")
    config['DATABASE_USER'] = get_user_input("Database User", "postgres")

    db_password = get_user_input("Database Password", secure=True)
    if not db_password:
        db_password = generate_password(32)
        print(f"  Generated secure password: {db_password}")
    config['DATABASE_PASSWORD'] = db_password

    # Construct database URL
    config['DATABASE_URL'] = (
        f"postgresql://{config['DATABASE_USER']}:{config['DATABASE_PASSWORD']}@"
        f"{config['DATABASE_HOST']}:{config['DATABASE_PORT']}/{config['DATABASE_NAME']}"
    )

    # TimescaleDB Configuration
    print("\n" + "=" * 80)
    print("TIMESCALEDB CONFIGURATION (for time-series vitals data)")
    print("=" * 80)
    print("Press Enter to use same credentials as main database")

    use_same_db = input("Use same database for TimescaleDB? (Y/n): ").strip().lower()
    if use_same_db in ('', 'y', 'yes'):
        config['TIMESCALEDB_HOST'] = config['DATABASE_HOST']
        config['TIMESCALEDB_PORT'] = config['DATABASE_PORT']
        config['TIMESCALEDB_NAME'] = config['DATABASE_NAME']
        config['TIMESCALEDB_USER'] = config['DATABASE_USER']
        config['TIMESCALEDB_PASSWORD'] = config['DATABASE_PASSWORD']
        config['TIMESCALEDB_URL'] = config['DATABASE_URL']
    else:
        config['TIMESCALEDB_HOST'] = get_user_input("TimescaleDB Host", "localhost")
        config['TIMESCALEDB_PORT'] = get_user_input("TimescaleDB Port", "5433")
        config['TIMESCALEDB_NAME'] = get_user_input("TimescaleDB Name", "hospital_timescale")
        config['TIMESCALEDB_USER'] = get_user_input("TimescaleDB User", "postgres")

        ts_password = get_user_input("TimescaleDB Password", secure=True)
        if not ts_password:
            ts_password = generate_password(32)
            print(f"  Generated secure password: {ts_password}")
        config['TIMESCALEDB_PASSWORD'] = ts_password

        config['TIMESCALEDB_URL'] = (
            f"postgresql://{config['TIMESCALEDB_USER']}:{config['TIMESCALEDB_PASSWORD']}@"
            f"{config['TIMESCALEDB_HOST']}:{config['TIMESCALEDB_PORT']}/{config['TIMESCALEDB_NAME']}"
        )

    # Security Configuration
    print("\n" + "=" * 80)
    print("SECURITY CONFIGURATION")
    print("=" * 80)

    secret_key = get_user_input("JWT Secret Key (min 32 chars)", secure=True)
    if not secret_key or len(secret_key) < 32:
        secret_key = generate_secret_key(64)
        print(f"  Generated secure key (64 chars): {secret_key}")
    config['SECRET_KEY'] = secret_key

    # API Configuration
    print("\n" + "=" * 80)
    print("API CONFIGURATION")
    print("=" * 80)

    config['API_V1_STR'] = get_user_input("API Version String", "/api/v1")
    config['PROJECT_NAME'] = get_user_input("Project Name", "Hospital Management System")

    # CORS Origins
    cors_origins = get_user_input("CORS Origins (comma-separated)", "http://localhost:3000")
    formatted_origins = cors_origins.replace(",", "\",\"")
    config['BACKEND_CORS_ORIGINS'] = f'["{formatted_origins}"]'

    # Environment
    print("\n" + "=" * 80)
    print("ENVIRONMENT SETTINGS")
    print("=" * 80)

    is_production = input("Is this a production environment? (y/N): ").strip().lower() == 'y'
    config['DEBUG'] = "False" if is_production else "True"
    config['TESTING'] = "False"
    config['LOG_LEVEL'] = "WARNING" if is_production else "INFO"

    # Write .env file
    print("\n" + "=" * 80)
    print("WRITING .env FILE")
    print("=" * 80)

    env_content = f"""# Hospital Management System - Environment Configuration
# Generated by setup_env.py
# DO NOT COMMIT THIS FILE TO VERSION CONTROL!

# ============================================
# DATABASE CONFIGURATION
# ============================================
DATABASE_URL={config['DATABASE_URL']}
DATABASE_HOST={config['DATABASE_HOST']}
DATABASE_PORT={config['DATABASE_PORT']}
DATABASE_NAME={config['DATABASE_NAME']}
DATABASE_USER={config['DATABASE_USER']}
DATABASE_PASSWORD={config['DATABASE_PASSWORD']}

# ============================================
# TIMESCALEDB CONFIGURATION
# ============================================
TIMESCALEDB_URL={config['TIMESCALEDB_URL']}
TIMESCALEDB_HOST={config['TIMESCALEDB_HOST']}
TIMESCALEDB_PORT={config['TIMESCALEDB_PORT']}
TIMESCALEDB_NAME={config['TIMESCALEDB_NAME']}
TIMESCALEDB_USER={config['TIMESCALEDB_USER']}
TIMESCALEDB_PASSWORD={config['TIMESCALEDB_PASSWORD']}

# ============================================
# SECURITY CONFIGURATION
# ============================================
SECRET_KEY={config['SECRET_KEY']}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ============================================
# API CONFIGURATION
# ============================================
API_V1_STR={config['API_V1_STR']}
PROJECT_NAME={config['PROJECT_NAME']}

# ============================================
# CORS CONFIGURATION
# ============================================
BACKEND_CORS_ORIGINS={config['BACKEND_CORS_ORIGINS']}

# ============================================
# ENVIRONMENT CONFIGURATION
# ============================================
DEBUG={config['DEBUG']}
TESTING={config['TESTING']}
LOG_LEVEL={config['LOG_LEVEL']}
"""

    with open(env_path, 'w') as f:
        f.write(env_content)

    print(f"\n✅ .env file created successfully at: {env_path}")
    print("\n" + "=" * 80)
    print("IMPORTANT SECURITY NOTES")
    print("=" * 80)
    print("1. Your .env file contains sensitive credentials")
    print("2. NEVER commit .env to version control")
    print("3. .gitignore is configured to exclude .env files")
    print("4. Keep your credentials secure and private")
    print("5. Use different credentials for production")
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Review your .env file")
    print("2. Ensure your PostgreSQL database is running")
    print("3. Create the database if it doesn't exist:")
    print(f"   createdb -U {config['DATABASE_USER']} {config['DATABASE_NAME']}")
    print("4. Run database migrations")
    print("5. Start the application")
    print("\n✅ Setup complete!")


if __name__ == "__main__":
    try:
        setup_env()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        print("Please try again or create .env file manually using .env.example as template")

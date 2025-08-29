import databases
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# PostgreSQL connection (for relational data)
database = databases.Database(settings.DATABASE_URL)
metadata = sa.MetaData()
Base = declarative_base()

# TimescaleDB connection (for time-series data)
timescale_db = databases.Database(settings.TIMESCALE_URL)
timescale_metadata = sa.MetaData()
TimescaleBase = declarative_base()

# Create engines
engine = sa.create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)

timescale_engine = sa.create_engine(
    settings.TIMESCALE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)

async def init_db():
    """Initialize database connections"""
    try:
        logger.info("Connecting to PostgreSQL...")
        await database.connect()
        logger.info("PostgreSQL connected successfully")
        
        try:
            logger.info("Connecting to TimescaleDB...")
            await timescale_db.connect()
            logger.info("TimescaleDB connected successfully")
        except Exception as e:
            logger.warning(f"TimescaleDB connection failed: {e}. Continuing with PostgreSQL only.")
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

async def close_db():
    """Close both database connections"""
    try:
        await database.disconnect()
        await timescale_db.disconnect()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
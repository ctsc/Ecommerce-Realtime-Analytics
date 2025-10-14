"""
Database initialization script.
Creates all tables and optionally seeds with sample data.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import db_manager
from src.storage.models import Base
from src.utils.logging_config import get_logger


logger = get_logger(__name__)


def init_database(drop_existing: bool = False):
    """
    Initialize the database schema.
    
    Args:
        drop_existing: If True, drop existing tables first
    """
    logger.info("Initializing database...")
    
    try:
        if drop_existing:
            logger.warning("Dropping existing tables...")
            db_manager.drop_tables()
        
        logger.info("Creating tables...")
        db_manager.create_tables()
        
        logger.info("Database initialized successfully!")
        
        # Print statistics
        stats = db_manager.get_database_stats()
        logger.info(f"Database statistics: {stats}")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize database")
    parser.add_argument(
        "--drop", 
        action="store_true",
        help="Drop existing tables before creating"
    )
    
    args = parser.parse_args()
    
    init_database(drop_existing=args.drop)



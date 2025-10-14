"""
Database management and operations for the e-commerce analytics pipeline.
Handles connections, schema creation, and data access patterns.
"""

from contextlib import contextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from src.storage.models import (
    Base, Transaction, Customer, Product, 
    FraudAlert, AnalyticsSummary, Recommendation
)
from src.utils.config import config
from src.utils.logging_config import get_logger


logger = get_logger(__name__)


class DatabaseManager:
    """
    Manages database connections and operations.
    Provides high-level API for data access.
    """
    
    def __init__(self, connection_string: str = None):
        """
        Initialize database manager.
        
        Args:
            connection_string: SQLAlchemy connection string
        """
        self.connection_string = connection_string or config.database.connection_string
        
        # Create engine with connection pooling
        self.engine = create_engine(
            self.connection_string,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Verify connections before using
            echo=False  # Set to True for SQL debugging
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info("Database manager initialized")
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables. Use with caution!"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Get a database session with automatic cleanup.
        
        Usage:
            with db.get_session() as session:
                # Use session
                pass
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def bulk_insert_transactions(self, transactions: List[Dict[str, Any]]) -> int:
        """
        Bulk insert transactions for better performance.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Number of transactions inserted
        """
        try:
            with self.get_session() as session:
                transaction_objects = [
                    Transaction(**tx) for tx in transactions
                ]
                session.bulk_save_objects(transaction_objects)
                session.commit()
                
            count = len(transactions)
            logger.info(f"Bulk inserted {count} transactions")
            return count
            
        except Exception as e:
            logger.error(f"Error in bulk insert: {e}")
            raise
    
    def get_recent_transactions(
        self, 
        limit: int = 100, 
        fraud_only: bool = False
    ) -> List[Transaction]:
        """
        Get recent transactions.
        
        Args:
            limit: Maximum number of transactions to return
            fraud_only: If True, only return fraudulent transactions
            
        Returns:
            List of Transaction objects
        """
        with self.get_session() as session:
            query = session.query(Transaction)
            
            if fraud_only:
                query = query.filter(Transaction.is_fraud == True)
            
            transactions = query.order_by(
                Transaction.timestamp.desc()
            ).limit(limit).all()
            
            return transactions
    
    def get_customer_stats(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get aggregated statistics for a customer.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Dictionary with customer statistics
        """
        with self.get_session() as session:
            customer = session.query(Customer).filter(
                Customer.customer_id == customer_id
            ).first()
            
            if not customer:
                return None
            
            return {
                "customer_id": customer.customer_id,
                "total_transactions": customer.total_transactions,
                "total_spent": customer.total_spent,
                "avg_order_value": customer.avg_order_value,
                "rfm_score": customer.rfm_score,
                "segment": customer.customer_segment,
                "lifetime_value": customer.lifetime_value
            }
    
    def get_fraud_alerts(
        self, 
        start_time: datetime = None, 
        unresolved_only: bool = True
    ) -> List[FraudAlert]:
        """
        Get fraud alerts.
        
        Args:
            start_time: Only get alerts after this time
            unresolved_only: If True, only return unresolved alerts
            
        Returns:
            List of FraudAlert objects
        """
        with self.get_session() as session:
            query = session.query(FraudAlert)
            
            if start_time:
                query = query.filter(FraudAlert.alert_timestamp >= start_time)
            
            if unresolved_only:
                query = query.filter(FraudAlert.investigated == False)
            
            alerts = query.order_by(
                FraudAlert.fraud_score.desc()
            ).all()
            
            return alerts
    
    def get_analytics_summary(
        self, 
        period_start: datetime, 
        period_end: datetime,
        granularity: str = 'hour'
    ) -> List[AnalyticsSummary]:
        """
        Get analytics summaries for a time period.
        
        Args:
            period_start: Start of period
            period_end: End of period
            granularity: Time granularity ('hour', 'day', 'week', 'month')
            
        Returns:
            List of AnalyticsSummary objects
        """
        with self.get_session() as session:
            summaries = session.query(AnalyticsSummary).filter(
                AnalyticsSummary.period_start >= period_start,
                AnalyticsSummary.period_end <= period_end,
                AnalyticsSummary.granularity == granularity
            ).order_by(AnalyticsSummary.period_start).all()
            
            return summaries
    
    def get_top_products(
        self, 
        limit: int = 10, 
        category: str = None
    ) -> List[Product]:
        """
        Get top-selling products.
        
        Args:
            limit: Number of products to return
            category: Optional category filter
            
        Returns:
            List of Product objects
        """
        with self.get_session() as session:
            query = session.query(Product)
            
            if category:
                query = query.filter(Product.category == category)
            
            products = query.order_by(
                Product.total_revenue.desc()
            ).limit(limit).all()
            
            return products
    
    def execute_raw_query(self, query: str) -> List[Dict]:
        """
        Execute a raw SQL query and return results.
        
        Args:
            query: SQL query string
            
        Returns:
            List of result dictionaries
        """
        with self.engine.connect() as connection:
            result = connection.execute(text(query))
            return [dict(row._mapping) for row in result]
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        with self.get_session() as session:
            stats = {
                "total_transactions": session.query(Transaction).count(),
                "total_customers": session.query(Customer).count(),
                "total_products": session.query(Product).count(),
                "fraud_alerts": session.query(FraudAlert).filter(
                    FraudAlert.investigated == False
                ).count(),
                "total_revenue": session.query(
                    text("SUM(total_amount)")
                ).select_from(Transaction).scalar() or 0.0
            }
            
            return stats


# Global database manager instance
db_manager = DatabaseManager()



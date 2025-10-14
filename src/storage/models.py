"""
Database models for the e-commerce analytics pipeline.
Defines SQLAlchemy ORM models for all data entities.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, Index, UniqueConstraint, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class Transaction(Base):
    """
    Main transaction table storing all e-commerce transactions.
    Optimized for high-volume inserts and analytical queries.
    """
    __tablename__ = 'transactions'
    
    # Primary key
    transaction_id = Column(String(50), primary_key=True)
    
    # Transaction details
    timestamp = Column(DateTime, nullable=False, index=True)
    customer_id = Column(String(50), nullable=False, index=True)
    product_id = Column(String(50), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False, index=True)
    
    # Customer information
    customer_email = Column(String(200))
    customer_location = Column(String(100))
    
    # Fraud detection
    is_fraud = Column(Boolean, default=False, index=True)
    fraud_score = Column(Float)
    fraud_reason = Column(String(500))
    
    # Metadata
    processing_timestamp = Column(DateTime, default=datetime.utcnow)
    batch_id = Column(String(50))
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_timestamp_customer', 'timestamp', 'customer_id'),
        Index('idx_timestamp_fraud', 'timestamp', 'is_fraud'),
        Index('idx_category_timestamp', 'category', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<Transaction(id={self.transaction_id}, amount={self.total_amount}, fraud={self.is_fraud})>"


class Customer(Base):
    """
    Customer dimension table with aggregated metrics.
    Used for customer analytics and segmentation.
    """
    __tablename__ = 'customers'
    
    customer_id = Column(String(50), primary_key=True)
    email = Column(String(200), unique=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    location = Column(String(100))
    
    # Registration info
    registration_date = Column(DateTime)
    
    # Aggregated metrics (updated periodically)
    total_transactions = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    avg_order_value = Column(Float, default=0.0)
    last_purchase_date = Column(DateTime)
    
    # RFM metrics
    recency_days = Column(Integer)  # Days since last purchase
    frequency = Column(Integer)     # Number of purchases
    monetary = Column(Float)        # Total spend
    rfm_score = Column(String(10))  # e.g., "555" for best customers
    customer_segment = Column(String(50))  # e.g., "Champions", "At Risk"
    
    # CLV (Customer Lifetime Value)
    lifetime_value = Column(Float)
    predicted_ltv = Column(Float)
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Customer(id={self.customer_id}, segment={self.customer_segment})>"


class Product(Base):
    """
    Product dimension table with performance metrics.
    """
    __tablename__ = 'products'
    
    product_id = Column(String(50), primary_key=True)
    product_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    unit_price = Column(Float, nullable=False)
    
    # Product metadata
    description = Column(Text)
    manufacturer = Column(String(200))
    
    # Performance metrics
    total_sold = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    avg_rating = Column(Float)
    
    # Inventory (simulated)
    stock_level = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Product(id={self.product_id}, name={self.product_name})>"


class FraudAlert(Base):
    """
    Fraud alerts table for suspicious transactions.
    Used for real-time monitoring and investigation.
    """
    __tablename__ = 'fraud_alerts'
    
    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(50), nullable=False, index=True)
    customer_id = Column(String(50), nullable=False, index=True)
    
    # Alert details
    alert_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    fraud_score = Column(Float, nullable=False)
    risk_level = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Reasons for alert
    reasons = Column(Text)  # JSON array of reasons
    
    # Investigation
    investigated = Column(Boolean, default=False)
    investigation_notes = Column(Text)
    confirmed_fraud = Column(Boolean)
    
    # Actions taken
    action_taken = Column(String(100))  # e.g., "Blocked", "Flagged", "Approved"
    resolved_at = Column(DateTime)
    
    def __repr__(self):
        return f"<FraudAlert(id={self.alert_id}, score={self.fraud_score}, level={self.risk_level})>"


class AnalyticsSummary(Base):
    """
    Pre-aggregated analytics summaries for dashboard performance.
    Updated periodically to avoid expensive real-time calculations.
    """
    __tablename__ = 'analytics_summaries'
    
    summary_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    granularity = Column(String(20))  # 'hour', 'day', 'week', 'month'
    
    # Transaction metrics
    total_transactions = Column(Integer)
    total_revenue = Column(Float)
    avg_order_value = Column(Float)
    
    # Customer metrics
    unique_customers = Column(Integer)
    new_customers = Column(Integer)
    returning_customers = Column(Integer)
    
    # Product metrics
    unique_products_sold = Column(Integer)
    top_category = Column(String(100))
    
    # Fraud metrics
    fraud_transactions = Column(Integer)
    fraud_rate = Column(Float)
    fraud_amount = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_period_granularity', 'period_start', 'granularity'),
        UniqueConstraint('period_start', 'granularity', name='uq_period_granularity'),
    )
    
    def __repr__(self):
        return f"<AnalyticsSummary(period={self.period_start}, revenue={self.total_revenue})>"


class Recommendation(Base):
    """
    Product recommendations for customers.
    Generated by the recommendation engine.
    """
    __tablename__ = 'recommendations'
    
    recommendation_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(50), nullable=False, index=True)
    product_id = Column(String(50), nullable=False)
    
    # Recommendation details
    score = Column(Float, nullable=False)  # Confidence score
    algorithm = Column(String(50))  # e.g., "collaborative_filtering", "content_based"
    
    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Tracking
    displayed = Column(Boolean, default=False)
    clicked = Column(Boolean, default=False)
    purchased = Column(Boolean, default=False)
    
    __table_args__ = (
        Index('idx_customer_score', 'customer_id', 'score'),
    )
    
    def __repr__(self):
        return f"<Recommendation(customer={self.customer_id}, product={self.product_id}, score={self.score})>"



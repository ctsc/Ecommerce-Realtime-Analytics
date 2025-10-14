"""
Configuration management for the e-commerce analytics pipeline.
Centralizes all configuration parameters for easy management.
"""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class KafkaConfig:
    """Kafka configuration parameters."""
    bootstrap_servers: str = "localhost:9092"
    topic_transactions: str = "ecommerce-transactions"
    topic_fraud_alerts: str = "fraud-alerts"
    consumer_group: str = "spark-consumer-group"
    auto_offset_reset: str = "latest"
    
    
@dataclass
class DatabaseConfig:
    """PostgreSQL database configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "ecommerce"
    user: str = "dataengineer"
    password: str = "SecurePass123!"
    
    @property
    def connection_string(self) -> str:
        """Generate SQLAlchemy connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class SparkConfig:
    """Spark configuration parameters."""
    app_name: str = "EcommerceRealtimeAnalytics"
    master: str = "local[*]"
    log_level: str = "WARN"
    shuffle_partitions: int = 4
    kafka_batch_duration: int = 5  # seconds
    checkpoint_location: str = "./checkpoints"
    

@dataclass
class GeneratorConfig:
    """Transaction generator configuration."""
    transactions_per_second: int = 100
    num_customers: int = 10000
    num_products: int = 500
    fraud_rate: float = 0.02  # 2% of transactions are fraudulent
    
    # Product categories
    categories: List[str] = None
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = [
                "Electronics", "Clothing", "Home & Garden", 
                "Books", "Sports", "Toys", "Food & Beverage",
                "Health & Beauty", "Automotive", "Office Supplies"
            ]


@dataclass
class FraudDetectionConfig:
    """Fraud detection model configuration."""
    contamination: float = 0.02  # Expected fraud rate
    n_estimators: int = 100
    random_state: int = 42
    features: List[str] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = [
                "amount",
                "hour_of_day",
                "day_of_week",
                "customer_transaction_count",
                "customer_avg_amount",
                "amount_deviation"
            ]


@dataclass
class DashboardConfig:
    """Dashboard configuration."""
    host: str = "0.0.0.0"
    port: int = 8050
    debug: bool = True
    refresh_interval: int = 5000  # milliseconds
    

class Config:
    """Main configuration class combining all configs."""
    
    def __init__(self):
        self.kafka = KafkaConfig()
        self.database = DatabaseConfig()
        self.spark = SparkConfig()
        self.generator = GeneratorConfig()
        self.fraud_detection = FraudDetectionConfig()
        self.dashboard = DashboardConfig()
        
        # Override with environment variables if present
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Kafka
        self.kafka.bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", 
            self.kafka.bootstrap_servers
        )
        
        # Database
        self.database.host = os.getenv("DB_HOST", self.database.host)
        self.database.port = int(os.getenv("DB_PORT", self.database.port))
        self.database.database = os.getenv("DB_NAME", self.database.database)
        self.database.user = os.getenv("DB_USER", self.database.user)
        self.database.password = os.getenv("DB_PASSWORD", self.database.password)
        
        # Spark
        self.spark.master = os.getenv("SPARK_MASTER", self.spark.master)


# Global configuration instance
config = Config()



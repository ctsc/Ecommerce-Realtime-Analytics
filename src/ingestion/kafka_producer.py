"""
Kafka producer for sending transaction data to Kafka topics.
Handles message serialization and delivery confirmation.
"""

import json
from typing import Dict, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError

from src.utils.config import config
from src.utils.logging_config import get_logger


logger = get_logger(__name__)


class KafkaTransactionProducer:
    """
    Kafka producer for transaction events.
    Serializes and sends transactions to Kafka topics.
    """
    
    def __init__(
        self,
        bootstrap_servers: str = None,
        topic: str = None
    ):
        """
        Initialize Kafka producer.
        
        Args:
            bootstrap_servers: Kafka broker address
            topic: Topic name for transactions
        """
        self.bootstrap_servers = bootstrap_servers or config.kafka.bootstrap_servers
        self.topic = topic or config.kafka.topic_transactions
        
        # Create producer with JSON serialization
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',  # Wait for all replicas to acknowledge
            retries=3,
            max_in_flight_requests_per_connection=1,
            compression_type='gzip',
            linger_ms=10,  # Batch messages for 10ms
            batch_size=16384  # 16KB batch size
        )
        
        self.success_count = 0
        self.error_count = 0
        
        logger.info(
            f"Kafka producer initialized: {self.bootstrap_servers}, "
            f"topic: {self.topic}"
        )
    
    def _on_send_success(self, record_metadata):
        """Callback for successful message delivery."""
        self.success_count += 1
        if self.success_count % 1000 == 0:
            logger.debug(
                f"Successfully sent {self.success_count} messages "
                f"(topic: {record_metadata.topic}, "
                f"partition: {record_metadata.partition})"
            )
    
    def _on_send_error(self, exc):
        """Callback for failed message delivery."""
        self.error_count += 1
        logger.error(f"Error sending message to Kafka: {exc}")
    
    def send_transaction(
        self, 
        transaction: Dict,
        key: Optional[str] = None
    ) -> bool:
        """
        Send a transaction to Kafka.
        
        Args:
            transaction: Transaction dictionary
            key: Optional message key (for partitioning)
            
        Returns:
            True if sent successfully (or queued), False otherwise
        """
        try:
            # Use customer_id as key for partitioning
            # (keeps all transactions for a customer in same partition)
            key = key or transaction.get('customer_id')
            
            # Send message asynchronously
            future = self.producer.send(
                self.topic,
                key=key,
                value=transaction
            )
            
            # Add callbacks
            future.add_callback(self._on_send_success)
            future.add_errback(self._on_send_error)
            
            return True
            
        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
            self.error_count += 1
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.error_count += 1
            return False
    
    def send_batch(self, transactions: list) -> int:
        """
        Send a batch of transactions.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Number of successfully queued messages
        """
        success = 0
        for transaction in transactions:
            if self.send_transaction(transaction):
                success += 1
        
        # Flush to ensure all messages are sent
        self.producer.flush()
        
        return success
    
    def flush(self):
        """Flush any pending messages."""
        self.producer.flush()
    
    def close(self):
        """Close the producer and cleanup resources."""
        try:
            self.producer.flush()
            self.producer.close()
            logger.info(
                f"Kafka producer closed. "
                f"Sent: {self.success_count}, Errors: {self.error_count}"
            )
        except Exception as e:
            logger.error(f"Error closing producer: {e}")
    
    def get_stats(self) -> Dict:
        """
        Get producer statistics.
        
        Returns:
            Dictionary with producer stats
        """
        return {
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": (
                self.success_count / (self.success_count + self.error_count)
                if (self.success_count + self.error_count) > 0 else 0
            )
        }


class FraudAlertProducer:
    """
    Separate producer for fraud alerts.
    Sends high-priority fraud alerts to dedicated topic.
    """
    
    def __init__(self):
        """Initialize fraud alert producer."""
        self.producer = KafkaProducer(
            bootstrap_servers=config.kafka.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=5,  # More retries for critical alerts
            compression_type='gzip'
        )
        
        self.topic = config.kafka.topic_fraud_alerts
        logger.info(f"Fraud alert producer initialized: {self.topic}")
    
    def send_alert(self, alert: Dict) -> bool:
        """
        Send a fraud alert.
        
        Args:
            alert: Fraud alert dictionary
            
        Returns:
            True if sent successfully
        """
        try:
            future = self.producer.send(self.topic, value=alert)
            future.get(timeout=10)  # Wait for confirmation
            return True
        except Exception as e:
            logger.error(f"Error sending fraud alert: {e}")
            return False
    
    def close(self):
        """Close the producer."""
        self.producer.close()



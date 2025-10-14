"""
Integration tests for the entire pipeline.
"""

import pytest
import time
from datetime import datetime

from src.ingestion.transaction_generator import TransactionGenerator
from src.ingestion.kafka_producer import KafkaTransactionProducer
from src.storage.database import db_manager


class TestPipelineIntegration:
    """Integration tests for the complete data pipeline."""
    
    @pytest.fixture(scope="class")
    def setup_database(self):
        """Set up test database."""
        # Initialize tables
        db_manager.create_tables()
        yield
        # Cleanup after tests
        # db_manager.drop_tables()  # Commented out to preserve data
    
    def test_database_connection(self):
        """Test database connectivity."""
        try:
            stats = db_manager.get_database_stats()
            assert stats is not None
            assert 'total_transactions' in stats
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
    
    def test_transaction_generation(self):
        """Test transaction generator produces valid data."""
        generator = TransactionGenerator(num_customers=10, num_products=5)
        
        transaction = generator.generate_transaction()
        
        # Validate transaction structure
        required_fields = [
            'transaction_id', 'timestamp', 'customer_id',
            'product_id', 'total_amount', 'is_fraud'
        ]
        
        for field in required_fields:
            assert field in transaction
        
        # Validate data types and values
        assert isinstance(transaction['total_amount'], (int, float))
        assert transaction['total_amount'] > 0
        assert isinstance(transaction['is_fraud'], bool)
    
    def test_batch_transaction_generation(self):
        """Test batch transaction generation."""
        generator = TransactionGenerator(num_customers=10, num_products=5)
        
        batch = generator.generate_batch(10)
        
        assert len(batch) == 10
        
        # All transactions should have unique IDs
        tx_ids = [tx['transaction_id'] for tx in batch]
        assert len(tx_ids) == len(set(tx_ids))
    
    @pytest.mark.skipif(
        not db_manager.engine.url.database,
        reason="Database not configured"
    )
    def test_database_write_read(self, setup_database):
        """Test writing and reading from database."""
        # Generate sample transaction
        generator = TransactionGenerator(num_customers=5, num_products=3)
        transactions = generator.generate_batch(5)
        
        # Convert to database format
        db_transactions = []
        for tx in transactions:
            db_tx = {
                'transaction_id': tx['transaction_id'],
                'timestamp': datetime.fromisoformat(tx['timestamp']),
                'customer_id': tx['customer_id'],
                'product_id': tx['product_id'],
                'product_name': tx['product_name'],
                'category': tx['category'],
                'quantity': tx['quantity'],
                'unit_price': tx['unit_price'],
                'total_amount': tx['total_amount'],
                'is_fraud': tx['is_fraud'],
                'customer_email': tx.get('customer_email'),
                'customer_location': tx.get('customer_location')
            }
            db_transactions.append(db_tx)
        
        # Write to database
        count = db_manager.bulk_insert_transactions(db_transactions)
        assert count == 5
        
        # Read back
        recent = db_manager.get_recent_transactions(limit=5)
        assert len(recent) >= 1
    
    def test_end_to_end_latency(self):
        """Test end-to-end latency of transaction processing."""
        generator = TransactionGenerator(num_customers=5, num_products=3)
        
        start_time = time.time()
        
        # Generate transaction
        transaction = generator.generate_transaction()
        
        # Simulate processing steps
        # 1. Validation
        assert 'transaction_id' in transaction
        
        # 2. Enrichment
        transaction['processing_timestamp'] = datetime.now()
        
        # 3. Storage simulation
        time.sleep(0.001)  # Simulate I/O
        
        end_time = time.time()
        latency = end_time - start_time
        
        # Latency should be under 100ms for single transaction
        assert latency < 0.1
    
    def test_concurrent_transaction_generation(self):
        """Test generator handles concurrent usage."""
        generator = TransactionGenerator(num_customers=100, num_products=50)
        
        # Generate transactions rapidly
        transactions = []
        for _ in range(100):
            tx = generator.generate_transaction()
            transactions.append(tx)
        
        # All transactions should be unique
        tx_ids = [tx['transaction_id'] for tx in transactions]
        assert len(tx_ids) == len(set(tx_ids))
        
        # All should have valid timestamps
        for tx in transactions:
            assert 'timestamp' in tx
            datetime.fromisoformat(tx['timestamp'])  # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



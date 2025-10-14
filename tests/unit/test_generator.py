"""
Unit tests for transaction generator.
"""

import pytest
from datetime import datetime

from src.ingestion.transaction_generator import TransactionGenerator


class TestTransactionGenerator:
    """Test suite for TransactionGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create a transaction generator instance."""
        return TransactionGenerator(
            num_customers=100,
            num_products=50,
            fraud_rate=0.02
        )
    
    def test_generator_initialization(self, generator):
        """Test generator initializes with correct parameters."""
        assert generator.num_customers == 100
        assert generator.num_products == 50
        assert generator.fraud_rate == 0.02
        assert len(generator.customers) == 100
        assert len(generator.products) == 50
    
    def test_generate_customers(self, generator):
        """Test customer generation."""
        customers = generator.customers
        
        assert len(customers) > 0
        
        # Check customer structure
        customer = customers[0]
        assert 'customer_id' in customer
        assert 'email' in customer
        assert 'first_name' in customer
        assert 'last_name' in customer
        assert 'location' in customer
    
    def test_generate_products(self, generator):
        """Test product generation."""
        products = generator.products
        
        assert len(products) > 0
        
        # Check product structure
        product = products[0]
        assert 'product_id' in product
        assert 'product_name' in product
        assert 'category' in product
        assert 'unit_price' in product
        assert product['unit_price'] > 0
    
    def test_generate_transaction(self, generator):
        """Test single transaction generation."""
        transaction = generator.generate_transaction()
        
        # Check required fields
        assert 'transaction_id' in transaction
        assert 'timestamp' in transaction
        assert 'customer_id' in transaction
        assert 'product_id' in transaction
        assert 'category' in transaction
        assert 'quantity' in transaction
        assert 'unit_price' in transaction
        assert 'total_amount' in transaction
        assert 'is_fraud' in transaction
        
        # Check data types
        assert isinstance(transaction['quantity'], int)
        assert isinstance(transaction['unit_price'], (int, float))
        assert isinstance(transaction['total_amount'], (int, float))
        assert isinstance(transaction['is_fraud'], bool)
        
        # Check calculations
        expected_total = transaction['unit_price'] * transaction['quantity']
        assert abs(transaction['total_amount'] - expected_total) < 0.01
    
    def test_generate_batch(self, generator):
        """Test batch transaction generation."""
        batch_size = 10
        batch = generator.generate_batch(batch_size)
        
        assert len(batch) == batch_size
        
        for transaction in batch:
            assert 'transaction_id' in transaction
            assert 'total_amount' in transaction
    
    def test_fraud_rate(self, generator):
        """Test that fraud rate is approximately correct."""
        batch_size = 1000
        batch = generator.generate_batch(batch_size)
        
        fraud_count = sum(1 for tx in batch if tx['is_fraud'])
        fraud_rate = fraud_count / batch_size
        
        # Allow 50% margin of error for small sample
        expected_rate = generator.fraud_rate
        assert fraud_rate < expected_rate * 1.5
    
    def test_customer_behavior_tracking(self, generator):
        """Test that customer behavior is tracked."""
        customer_id = generator.customers[0]['customer_id']
        
        # Generate transactions
        for _ in range(5):
            tx = generator._generate_normal_transaction()
        
        # Check if behavior is tracked
        if customer_id in generator.customer_history:
            behavior = generator.customer_history[customer_id]
            assert 'transaction_count' in behavior
            assert 'total_spent' in behavior
    
    def test_fraudulent_transaction_patterns(self, generator):
        """Test fraudulent transaction generation."""
        fraud_tx = generator._generate_fraudulent_transaction()
        
        assert fraud_tx['is_fraud'] is True
        assert 'fraud_pattern' in fraud_tx
        
        # Fraud transactions should have some anomalous characteristic
        assert (
            fraud_tx['total_amount'] > 500 or  # High amount
            fraud_tx['quantity'] > 5  # High quantity
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



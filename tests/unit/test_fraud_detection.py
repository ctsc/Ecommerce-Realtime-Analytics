"""
Unit tests for fraud detection engine.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.processing.fraud_detection import FraudDetectionEngine


class TestFraudDetectionEngine:
    """Test suite for FraudDetectionEngine."""
    
    @pytest.fixture
    def fraud_engine(self):
        """Create a fraud detection engine instance."""
        return FraudDetectionEngine()
    
    @pytest.fixture
    def sample_transaction(self):
        """Create a sample transaction."""
        return {
            'transaction_id': 'TX123',
            'timestamp': datetime.now().isoformat(),
            'customer_id': 'CUST001',
            'product_id': 'PROD001',
            'quantity': 1,
            'unit_price': 100.0,
            'total_amount': 100.0
        }
    
    @pytest.fixture
    def customer_history(self):
        """Create sample customer history."""
        return {
            'transaction_count': 10,
            'avg_amount': 50.0,
            'total_spent': 500.0,
            'last_transaction_time': datetime.now() - timedelta(days=1)
        }
    
    def test_engine_initialization(self, fraud_engine):
        """Test engine initializes correctly."""
        assert fraud_engine is not None
        assert fraud_engine.feature_names is not None
    
    def test_extract_features(self, fraud_engine, sample_transaction, customer_history):
        """Test feature extraction."""
        features = fraud_engine.extract_features(sample_transaction, customer_history)
        
        assert features is not None
        assert features.shape == (1, 6)  # 6 features
        assert isinstance(features, np.ndarray)
    
    def test_extract_features_without_history(self, fraud_engine, sample_transaction):
        """Test feature extraction without customer history."""
        features = fraud_engine.extract_features(sample_transaction)
        
        assert features is not None
        assert features.shape == (1, 6)
    
    def test_predict_without_training(self, fraud_engine, sample_transaction):
        """Test prediction returns default when not trained."""
        is_fraud, score, reasons = fraud_engine.predict(sample_transaction)
        
        assert isinstance(is_fraud, bool)
        assert isinstance(score, float)
        assert isinstance(reasons, list)
    
    def test_train_model(self, fraud_engine):
        """Test model training."""
        # Create synthetic training data
        transactions = pd.DataFrame({
            'transaction_id': [f'TX{i}' for i in range(100)],
            'timestamp': [datetime.now().isoformat() for _ in range(100)],
            'customer_id': [f'CUST{i%20}' for i in range(100)],
            'total_amount': np.random.uniform(10, 1000, 100),
            'quantity': np.random.randint(1, 5, 100)
        })
        
        fraud_engine.train(transactions)
        
        assert fraud_engine.model is not None
        assert fraud_engine.scaler is not None
    
    def test_determine_fraud_reasons_high_amount(self, fraud_engine):
        """Test fraud reasons for high amount."""
        transaction = {
            'timestamp': datetime.now().isoformat(),
            'total_amount': 2000.0
        }
        
        reasons = fraud_engine._determine_fraud_reasons(transaction, {}, 85.0)
        
        assert len(reasons) > 0
        assert any('High transaction amount' in r for r in reasons)
    
    def test_determine_fraud_reasons_unusual_time(self, fraud_engine):
        """Test fraud reasons for unusual time."""
        late_night = datetime.now().replace(hour=3)
        transaction = {
            'timestamp': late_night.isoformat(),
            'total_amount': 100.0
        }
        
        reasons = fraud_engine._determine_fraud_reasons(transaction, {}, 85.0)
        
        assert len(reasons) > 0
        assert any('Unusual transaction time' in r for r in reasons)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



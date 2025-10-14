"""
Fraud detection module using machine learning.
Implements Isolation Forest for anomaly detection.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pickle
from pathlib import Path

from src.utils.config import config
from src.utils.logging_config import get_logger


logger = get_logger(__name__)


class FraudDetectionEngine:
    """
    Fraud detection engine using Isolation Forest algorithm.
    Detects anomalous transactions based on multiple features.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize fraud detection engine.
        
        Args:
            model_path: Optional path to pre-trained model
        """
        self.model_path = model_path or "models/fraud_detection_model.pkl"
        self.scaler = StandardScaler()
        self.model = None
        self.feature_names = config.fraud_detection.features
        
        # Load existing model if available
        if Path(self.model_path).exists():
            self.load_model()
        else:
            self._initialize_model()
        
        logger.info("Fraud detection engine initialized")
    
    def _initialize_model(self):
        """Initialize a new Isolation Forest model."""
        self.model = IsolationForest(
            contamination=config.fraud_detection.contamination,
            n_estimators=config.fraud_detection.n_estimators,
            random_state=config.fraud_detection.random_state,
            n_jobs=-1,
            verbose=0
        )
        logger.info("Initialized new Isolation Forest model")
    
    def extract_features(
        self, 
        transaction: Dict,
        customer_history: Dict = None
    ) -> np.ndarray:
        """
        Extract features from transaction for fraud detection.
        
        Args:
            transaction: Transaction dictionary
            customer_history: Optional customer transaction history
            
        Returns:
            Feature array
        """
        # Parse timestamp
        try:
            ts = pd.to_datetime(transaction['timestamp'])
        except:
            ts = datetime.now()
        
        # Basic features
        features = {
            'amount': float(transaction['total_amount']),
            'quantity': int(transaction['quantity']),
            'hour_of_day': ts.hour,
            'day_of_week': ts.weekday(),
            'is_weekend': 1 if ts.weekday() >= 5 else 0,
        }
        
        # Customer history features (if available)
        if customer_history:
            features['customer_transaction_count'] = customer_history.get('transaction_count', 0)
            features['customer_avg_amount'] = customer_history.get('avg_amount', 0)
            features['customer_total_spent'] = customer_history.get('total_spent', 0)
            
            # Amount deviation from customer average
            if features['customer_avg_amount'] > 0:
                features['amount_deviation'] = (
                    features['amount'] / features['customer_avg_amount']
                )
            else:
                features['amount_deviation'] = 1.0
            
            # Time since last transaction (hours)
            if 'last_transaction_time' in customer_history:
                last_tx_time = customer_history['last_transaction_time']
                if last_tx_time:
                    time_diff = (ts - last_tx_time).total_seconds() / 3600
                    features['hours_since_last_tx'] = time_diff
                else:
                    features['hours_since_last_tx'] = 24  # Default
            else:
                features['hours_since_last_tx'] = 24
        else:
            # Default values when no history available
            features['customer_transaction_count'] = 0
            features['customer_avg_amount'] = 0
            features['customer_total_spent'] = 0
            features['amount_deviation'] = 1.0
            features['hours_since_last_tx'] = 24
        
        # Convert to array in consistent order
        feature_array = np.array([
            features['amount'],
            features['hour_of_day'],
            features['day_of_week'],
            features['customer_transaction_count'],
            features['customer_avg_amount'],
            features['amount_deviation']
        ]).reshape(1, -1)
        
        return feature_array
    
    def train(self, transactions: pd.DataFrame):
        """
        Train the fraud detection model on historical data.
        
        Args:
            transactions: DataFrame with transaction history
        """
        logger.info(f"Training fraud detection model on {len(transactions)} transactions")
        
        # Extract features from all transactions
        features_list = []
        
        for _, tx in transactions.iterrows():
            tx_dict = tx.to_dict()
            features = self.extract_features(tx_dict)
            features_list.append(features[0])
        
        X = np.array(features_list)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled)
        
        logger.info("Model training completed")
    
    def predict(
        self, 
        transaction: Dict,
        customer_history: Dict = None
    ) -> Tuple[bool, float, List[str]]:
        """
        Predict if a transaction is fraudulent.
        
        Args:
            transaction: Transaction dictionary
            customer_history: Customer transaction history
            
        Returns:
            Tuple of (is_fraud, fraud_score, reasons)
        """
        if self.model is None:
            logger.warning("Model not trained. Returning default prediction.")
            return False, 0.0, []
        
        # Extract features
        features = self.extract_features(transaction, customer_history)
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Predict (returns -1 for anomaly, 1 for normal)
        prediction = self.model.predict(features_scaled)[0]
        
        # Get anomaly score (lower = more anomalous)
        score = self.model.score_samples(features_scaled)[0]
        
        # Normalize score to 0-100 range
        fraud_score = max(0, min(100, (1 - score) * 50))
        
        is_fraud = prediction == -1 or fraud_score > 80
        
        # Determine reasons for fraud flag
        reasons = self._determine_fraud_reasons(transaction, customer_history, fraud_score)
        
        return is_fraud, fraud_score, reasons
    
    def _determine_fraud_reasons(
        self,
        transaction: Dict,
        customer_history: Dict,
        fraud_score: float
    ) -> List[str]:
        """
        Determine reasons why transaction was flagged as fraud.
        
        Args:
            transaction: Transaction dictionary
            customer_history: Customer history
            fraud_score: Calculated fraud score
            
        Returns:
            List of reason strings
        """
        reasons = []
        
        amount = float(transaction['total_amount'])
        
        # High amount
        if amount > 1000:
            reasons.append(f"High transaction amount: ${amount:.2f}")
        
        # Unusual time
        try:
            ts = pd.to_datetime(transaction['timestamp'])
            if ts.hour < 6 or ts.hour > 22:
                reasons.append(f"Unusual transaction time: {ts.hour}:00")
        except:
            pass
        
        # Deviation from customer average
        if customer_history:
            avg_amount = customer_history.get('avg_amount', 0)
            if avg_amount > 0 and amount > avg_amount * 3:
                reasons.append(f"Amount {amount/avg_amount:.1f}x customer average")
        
        # High anomaly score
        if fraud_score > 80:
            reasons.append(f"High anomaly score: {fraud_score:.1f}")
        
        return reasons if reasons else ["Anomalous pattern detected"]
    
    def save_model(self):
        """Save trained model and scaler to disk."""
        model_dir = Path(self.model_path).parent
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load trained model from disk."""
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            
            logger.info(f"Model loaded from {self.model_path}")
        except Exception as e:
            logger.warning(f"Could not load model: {e}. Initializing new model.")
            self._initialize_model()
    
    def batch_predict(
        self, 
        transactions: List[Dict]
    ) -> List[Tuple[bool, float, List[str]]]:
        """
        Predict fraud for a batch of transactions.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of (is_fraud, score, reasons) tuples
        """
        results = []
        
        for transaction in transactions:
            result = self.predict(transaction)
            results.append(result)
        
        return results
    
    def get_fraud_statistics(
        self, 
        predictions: List[Tuple[bool, float, List[str]]]
    ) -> Dict:
        """
        Calculate statistics from fraud predictions.
        
        Args:
            predictions: List of prediction tuples
            
        Returns:
            Dictionary with statistics
        """
        total = len(predictions)
        fraud_count = sum(1 for p in predictions if p[0])
        
        fraud_scores = [p[1] for p in predictions]
        
        stats = {
            "total_transactions": total,
            "fraud_detected": fraud_count,
            "fraud_rate": (fraud_count / total * 100) if total > 0 else 0,
            "avg_fraud_score": np.mean(fraud_scores) if fraud_scores else 0,
            "max_fraud_score": max(fraud_scores) if fraud_scores else 0,
            "min_fraud_score": min(fraud_scores) if fraud_scores else 0
        }
        
        return stats


# Global fraud detection engine instance
fraud_engine = FraudDetectionEngine()



"""
Unit tests for RFM analysis.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from src.analytics.rfm_analysis import RFMAnalyzer


class TestRFMAnalyzer:
    """Test suite for RFMAnalyzer."""
    
    @pytest.fixture
    def rfm_analyzer(self):
        """Create RFM analyzer instance."""
        return RFMAnalyzer()
    
    @pytest.fixture
    def sample_transactions(self):
        """Create sample transaction data."""
        transactions = []
        
        # Customer 1: Recent, frequent, high value (Champion)
        for i in range(10):
            transactions.append({
                'customer_id': 'CUST001',
                'transaction_id': f'TX001_{i}',
                'timestamp': datetime.now() - timedelta(days=i),
                'total_amount': 100.0
            })
        
        # Customer 2: Old, infrequent, low value (Lost)
        for i in range(2):
            transactions.append({
                'customer_id': 'CUST002',
                'transaction_id': f'TX002_{i}',
                'timestamp': datetime.now() - timedelta(days=180 + i),
                'total_amount': 20.0
            })
        
        # Customer 3: Recent, medium frequency, medium value
        for i in range(5):
            transactions.append({
                'customer_id': 'CUST003',
                'transaction_id': f'TX003_{i}',
                'timestamp': datetime.now() - timedelta(days=i*7),
                'total_amount': 50.0
            })
        
        return pd.DataFrame(transactions)
    
    def test_analyzer_initialization(self, rfm_analyzer):
        """Test analyzer initializes correctly."""
        assert rfm_analyzer is not None
        assert rfm_analyzer.analysis_date is not None
        assert isinstance(rfm_analyzer.SEGMENTS, dict)
    
    def test_calculate_rfm(self, rfm_analyzer, sample_transactions):
        """Test RFM calculation."""
        rfm_df = rfm_analyzer.calculate_rfm(sample_transactions)
        
        # Check output structure
        assert not rfm_df.empty
        assert 'customer_id' in rfm_df.columns
        assert 'recency' in rfm_df.columns
        assert 'frequency' in rfm_df.columns
        assert 'monetary' in rfm_df.columns
        assert 'r_score' in rfm_df.columns
        assert 'f_score' in rfm_df.columns
        assert 'm_score' in rfm_df.columns
        assert 'rfm_score' in rfm_df.columns
        assert 'segment' in rfm_df.columns
        
        # Check scores are in 1-5 range
        assert rfm_df['r_score'].min() >= 1
        assert rfm_df['r_score'].max() <= 5
        assert rfm_df['f_score'].min() >= 1
        assert rfm_df['f_score'].max() <= 5
        assert rfm_df['m_score'].min() >= 1
        assert rfm_df['m_score'].max() <= 5
    
    def test_get_segment(self, rfm_analyzer):
        """Test segment assignment."""
        # Test known segment
        segment = rfm_analyzer._get_segment('555')
        assert segment == 'Champions'
        
        segment = rfm_analyzer._get_segment('111')
        assert segment == 'Lost'
        
        # Test unknown segment (should return default)
        segment = rfm_analyzer._get_segment('999')
        assert segment is not None
    
    def test_get_segment_summary(self, rfm_analyzer, sample_transactions):
        """Test segment summary calculation."""
        rfm_df = rfm_analyzer.calculate_rfm(sample_transactions)
        summary = rfm_analyzer.get_segment_summary(rfm_df)
        
        assert not summary.empty
        assert 'segment' in summary.columns
        assert 'customer_count' in summary.columns
        assert 'avg_recency_days' in summary.columns
        assert 'avg_frequency' in summary.columns
        assert 'total_revenue' in summary.columns
        assert 'customer_percentage' in summary.columns
        assert 'revenue_percentage' in summary.columns
        
        # Check percentages sum to ~100%
        assert abs(summary['customer_percentage'].sum() - 100) < 1
        assert abs(summary['revenue_percentage'].sum() - 100) < 1
    
    def test_identify_high_value_customers(self, rfm_analyzer, sample_transactions):
        """Test high-value customer identification."""
        rfm_df = rfm_analyzer.calculate_rfm(sample_transactions)
        top_customers = rfm_analyzer.identify_high_value_customers(rfm_df, top_n=2)
        
        assert len(top_customers) <= 2
        assert 'composite_score' in top_customers.columns
        
        # Check ordering (descending by composite score)
        if len(top_customers) > 1:
            scores = top_customers['composite_score'].values
            assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    
    def test_identify_at_risk_customers(self, rfm_analyzer, sample_transactions):
        """Test at-risk customer identification."""
        rfm_df = rfm_analyzer.calculate_rfm(sample_transactions)
        at_risk = rfm_analyzer.identify_at_risk_customers(rfm_df)
        
        assert isinstance(at_risk, pd.DataFrame)
        
        # All at-risk customers should have low recency or be in at-risk segments
        if not at_risk.empty:
            assert all(
                (row['segment'] in ['At Risk', 'Need Attention', 'Hibernating']) or
                (row['r_score'] <= 2 and row['f_score'] >= 3)
                for _, row in at_risk.iterrows()
            )
    
    def test_get_actionable_insights(self, rfm_analyzer, sample_transactions):
        """Test insights generation."""
        rfm_df = rfm_analyzer.calculate_rfm(sample_transactions)
        insights = rfm_analyzer.get_actionable_insights(rfm_df)
        
        assert 'total_customers' in insights
        assert 'champions' in insights
        assert 'at_risk' in insights
        assert 'lost' in insights
        assert 'total_revenue' in insights
        assert 'recommendations' in insights
        
        assert isinstance(insights['recommendations'], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



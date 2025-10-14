"""
RFM (Recency, Frequency, Monetary) Analysis module.
Segments customers based on purchase behavior.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from src.storage.database import db_manager
from src.utils.logging_config import get_logger


logger = get_logger(__name__)


class RFMAnalyzer:
    """
    RFM Analysis for customer segmentation.
    Analyzes Recency, Frequency, and Monetary value of customers.
    """
    
    # Customer segment definitions
    SEGMENTS = {
        '555': 'Champions',
        '554': 'Champions',
        '544': 'Champions',
        '545': 'Champions',
        '454': 'Loyal Customers',
        '455': 'Loyal Customers',
        '445': 'Loyal Customers',
        '444': 'Loyal Customers',
        '435': 'Loyal Customers',
        '355': 'Potential Loyalists',
        '354': 'Potential Loyalists',
        '345': 'Potential Loyalists',
        '344': 'Potential Loyalists',
        '335': 'Potential Loyalists',
        '534': 'Recent Customers',
        '535': 'Recent Customers',
        '525': 'Recent Customers',
        '524': 'Recent Customers',
        '514': 'Recent Customers',
        '515': 'Recent Customers',
        '425': 'Promising',
        '415': 'Promising',
        '424': 'Promising',
        '414': 'Promising',
        '325': 'New Customers',
        '324': 'New Customers',
        '315': 'New Customers',
        '314': 'New Customers',
        '255': 'Need Attention',
        '254': 'Need Attention',
        '245': 'Need Attention',
        '244': 'Need Attention',
        '235': 'Need Attention',
        '145': 'At Risk',
        '155': 'At Risk',
        '135': 'At Risk',
        '144': 'At Risk',
        '154': 'At Risk',
        '124': 'Hibernating',
        '125': 'Hibernating',
        '115': 'Hibernating',
        '114': 'Hibernating',
        '134': 'Hibernating',
        '111': 'Lost',
        '112': 'Lost',
        '121': 'Lost',
        '122': 'Lost',
        '123': 'Lost',
        '113': 'Lost',
        '131': 'Lost',
        '132': 'Lost',
        '133': 'Lost',
    }
    
    def __init__(self, analysis_date: datetime = None):
        """
        Initialize RFM analyzer.
        
        Args:
            analysis_date: Reference date for recency calculation
        """
        self.analysis_date = analysis_date or datetime.now()
        logger.info("RFM Analyzer initialized")
    
    def calculate_rfm(self, transactions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RFM metrics for all customers.
        
        Args:
            transactions_df: DataFrame with transaction data
            
        Returns:
            DataFrame with RFM scores per customer
        """
        logger.info(f"Calculating RFM for {len(transactions_df)} transactions")
        
        # Ensure timestamp is datetime
        transactions_df['timestamp'] = pd.to_datetime(transactions_df['timestamp'])
        
        # Calculate RFM metrics
        rfm_df = transactions_df.groupby('customer_id').agg({
            'timestamp': lambda x: (self.analysis_date - x.max()).days,  # Recency
            'transaction_id': 'count',  # Frequency
            'total_amount': 'sum'  # Monetary
        }).reset_index()
        
        rfm_df.columns = ['customer_id', 'recency', 'frequency', 'monetary']
        
        # Calculate RFM scores (1-5 scale)
        rfm_df['r_score'] = self._calculate_score(rfm_df['recency'], reverse=True)
        rfm_df['f_score'] = self._calculate_score(rfm_df['frequency'])
        rfm_df['m_score'] = self._calculate_score(rfm_df['monetary'])
        
        # Create RFM string (e.g., "555")
        rfm_df['rfm_score'] = (
            rfm_df['r_score'].astype(str) +
            rfm_df['f_score'].astype(str) +
            rfm_df['m_score'].astype(str)
        )
        
        # Assign segments
        rfm_df['segment'] = rfm_df['rfm_score'].apply(self._get_segment)
        
        # Calculate customer lifetime value (simplified)
        rfm_df['lifetime_value'] = rfm_df['monetary']
        
        logger.info(f"RFM calculated for {len(rfm_df)} customers")
        
        return rfm_df
    
    def _calculate_score(
        self, 
        values: pd.Series, 
        reverse: bool = False
    ) -> pd.Series:
        """
        Calculate 1-5 score using quintiles.
        
        Args:
            values: Series of values to score
            reverse: If True, lower values get higher scores (for recency)
            
        Returns:
            Series of scores (1-5)
        """
        try:
            if reverse:
                scores = pd.qcut(
                    values, 
                    q=5, 
                    labels=[5, 4, 3, 2, 1], 
                    duplicates='drop'
                )
            else:
                scores = pd.qcut(
                    values, 
                    q=5, 
                    labels=[1, 2, 3, 4, 5], 
                    duplicates='drop'
                )
            return scores.astype(int)
        except ValueError:
            # If can't create quintiles (too few unique values), use simple binning
            if reverse:
                return pd.cut(
                    values, 
                    bins=5, 
                    labels=[5, 4, 3, 2, 1], 
                    include_lowest=True
                ).astype(int)
            else:
                return pd.cut(
                    values, 
                    bins=5, 
                    labels=[1, 2, 3, 4, 5], 
                    include_lowest=True
                ).astype(int)
    
    def _get_segment(self, rfm_score: str) -> str:
        """
        Get customer segment from RFM score.
        
        Args:
            rfm_score: RFM score string (e.g., "555")
            
        Returns:
            Segment name
        """
        # Try exact match first
        if rfm_score in self.SEGMENTS:
            return self.SEGMENTS[rfm_score]
        
        # Otherwise, create general segment
        r, f, m = int(rfm_score[0]), int(rfm_score[1]), int(rfm_score[2])
        
        if r >= 4 and f >= 4:
            return 'Champions'
        elif r >= 4:
            return 'Recent Customers'
        elif f >= 4:
            return 'Loyal Customers'
        elif r <= 2 and f <= 2:
            return 'Lost'
        else:
            return 'Regular'
    
    def get_segment_summary(self, rfm_df: pd.DataFrame) -> pd.DataFrame:
        """
        Get summary statistics by customer segment.
        
        Args:
            rfm_df: DataFrame with RFM analysis results
            
        Returns:
            Summary DataFrame
        """
        summary = rfm_df.groupby('segment').agg({
            'customer_id': 'count',
            'recency': 'mean',
            'frequency': 'mean',
            'monetary': ['mean', 'sum']
        }).round(2)
        
        summary.columns = [
            'customer_count',
            'avg_recency_days',
            'avg_frequency',
            'avg_monetary',
            'total_revenue'
        ]
        
        # Calculate percentage of customers
        summary['customer_percentage'] = (
            summary['customer_count'] / summary['customer_count'].sum() * 100
        ).round(2)
        
        # Calculate revenue percentage
        summary['revenue_percentage'] = (
            summary['total_revenue'] / summary['total_revenue'].sum() * 100
        ).round(2)
        
        return summary.reset_index()
    
    def identify_high_value_customers(
        self, 
        rfm_df: pd.DataFrame, 
        top_n: int = 100
    ) -> pd.DataFrame:
        """
        Identify top high-value customers.
        
        Args:
            rfm_df: RFM analysis results
            top_n: Number of top customers to return
            
        Returns:
            DataFrame with top customers
        """
        # Sort by monetary value and recency
        rfm_df['composite_score'] = (
            rfm_df['m_score'] * 0.5 +
            rfm_df['f_score'] * 0.3 +
            rfm_df['r_score'] * 0.2
        )
        
        top_customers = rfm_df.nlargest(top_n, 'composite_score')
        
        return top_customers
    
    def identify_at_risk_customers(self, rfm_df: pd.DataFrame) -> pd.DataFrame:
        """
        Identify customers at risk of churning.
        
        Args:
            rfm_df: RFM analysis results
            
        Returns:
            DataFrame with at-risk customers
        """
        at_risk = rfm_df[
            (rfm_df['segment'].isin(['At Risk', 'Need Attention', 'Hibernating'])) |
            ((rfm_df['r_score'] <= 2) & (rfm_df['f_score'] >= 3))
        ]
        
        return at_risk.sort_values('monetary', ascending=False)
    
    def get_actionable_insights(self, rfm_df: pd.DataFrame) -> Dict:
        """
        Generate actionable insights from RFM analysis.
        
        Args:
            rfm_df: RFM analysis results
            
        Returns:
            Dictionary with insights and recommendations
        """
        total_customers = len(rfm_df)
        
        insights = {
            'total_customers': total_customers,
            'champions': len(rfm_df[rfm_df['segment'] == 'Champions']),
            'at_risk': len(rfm_df[rfm_df['segment'].isin(['At Risk', 'Hibernating'])]),
            'lost': len(rfm_df[rfm_df['segment'] == 'Lost']),
            'avg_lifetime_value': rfm_df['lifetime_value'].mean(),
            'total_revenue': rfm_df['monetary'].sum(),
            'recommendations': []
        }
        
        # Generate recommendations
        if insights['champions'] / total_customers < 0.05:
            insights['recommendations'].append(
                "Low number of Champions. Focus on loyalty programs."
            )
        
        if insights['at_risk'] / total_customers > 0.20:
            insights['recommendations'].append(
                "High number of at-risk customers. Launch re-engagement campaigns."
            )
        
        if insights['lost'] / total_customers > 0.30:
            insights['recommendations'].append(
                "High churn rate. Investigate reasons and improve retention."
            )
        
        return insights


# Global RFM analyzer instance
rfm_analyzer = RFMAnalyzer()



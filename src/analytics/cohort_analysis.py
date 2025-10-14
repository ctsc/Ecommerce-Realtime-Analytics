"""
Cohort analysis module for tracking customer behavior over time.
Analyzes retention and engagement by customer cohorts.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Tuple

from src.utils.logging_config import get_logger


logger = get_logger(__name__)


class CohortAnalyzer:
    """
    Cohort analysis for customer retention and engagement tracking.
    Groups customers by acquisition date and tracks behavior over time.
    """
    
    def __init__(self):
        """Initialize cohort analyzer."""
        logger.info("Cohort Analyzer initialized")
    
    def prepare_cohort_data(
        self, 
        transactions_df: pd.DataFrame,
        customer_registration_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Prepare transaction data for cohort analysis.
        
        Args:
            transactions_df: DataFrame with transaction data
            customer_registration_df: Optional DataFrame with customer registration dates
            
        Returns:
            Prepared DataFrame with cohort information
        """
        # Ensure timestamp is datetime
        transactions_df['timestamp'] = pd.to_datetime(transactions_df['timestamp'])
        
        # Get first purchase date for each customer (as cohort)
        customer_cohorts = (
            transactions_df.groupby('customer_id')['timestamp']
            .min()
            .reset_index()
        )
        customer_cohorts.columns = ['customer_id', 'cohort_date']
        
        # Extract cohort month
        customer_cohorts['cohort_month'] = customer_cohorts['cohort_date'].dt.to_period('M')
        
        # Merge cohort info back to transactions
        cohort_df = transactions_df.merge(customer_cohorts, on='customer_id')
        
        # Calculate period (months since first purchase)
        cohort_df['transaction_month'] = cohort_df['timestamp'].dt.to_period('M')
        cohort_df['period'] = (
            cohort_df['transaction_month'] - cohort_df['cohort_month']
        ).apply(lambda x: x.n)
        
        return cohort_df
    
    def calculate_retention_cohort(
        self, 
        cohort_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calculate retention cohort matrix.
        
        Args:
            cohort_df: Prepared cohort DataFrame
            
        Returns:
            Tuple of (cohort_counts, cohort_percentages)
        """
        # Count unique customers per cohort and period
        cohort_counts = (
            cohort_df.groupby(['cohort_month', 'period'])['customer_id']
            .nunique()
            .reset_index()
        )
        
        # Pivot to create cohort matrix
        cohort_matrix = cohort_counts.pivot(
            index='cohort_month',
            columns='period',
            values='customer_id'
        )
        
        # Calculate retention percentages
        cohort_size = cohort_matrix.iloc[:, 0]
        retention_matrix = cohort_matrix.divide(cohort_size, axis=0) * 100
        
        logger.info(f"Calculated retention for {len(cohort_matrix)} cohorts")
        
        return cohort_matrix, retention_matrix
    
    def calculate_revenue_cohort(
        self, 
        cohort_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate revenue by cohort over time.
        
        Args:
            cohort_df: Prepared cohort DataFrame
            
        Returns:
            Revenue cohort matrix
        """
        # Sum revenue per cohort and period
        revenue_cohorts = (
            cohort_df.groupby(['cohort_month', 'period'])['total_amount']
            .sum()
            .reset_index()
        )
        
        # Pivot to create cohort matrix
        revenue_matrix = revenue_cohorts.pivot(
            index='cohort_month',
            columns='period',
            values='total_amount'
        )
        
        return revenue_matrix
    
    def calculate_average_order_value_cohort(
        self, 
        cohort_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate average order value by cohort over time.
        
        Args:
            cohort_df: Prepared cohort DataFrame
            
        Returns:
            AOV cohort matrix
        """
        # Calculate average order value per cohort and period
        aov_cohorts = (
            cohort_df.groupby(['cohort_month', 'period'])['total_amount']
            .mean()
            .reset_index()
        )
        
        # Pivot to create cohort matrix
        aov_matrix = aov_cohorts.pivot(
            index='cohort_month',
            columns='period',
            values='total_amount'
        )
        
        return aov_matrix
    
    def calculate_frequency_cohort(
        self, 
        cohort_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate purchase frequency by cohort over time.
        
        Args:
            cohort_df: Prepared cohort DataFrame
            
        Returns:
            Frequency cohort matrix
        """
        # Count transactions per customer per cohort and period
        frequency_cohorts = (
            cohort_df.groupby(['cohort_month', 'period', 'customer_id'])
            .size()
            .reset_index(name='transactions')
        )
        
        # Calculate average frequency
        avg_frequency = (
            frequency_cohorts.groupby(['cohort_month', 'period'])['transactions']
            .mean()
            .reset_index()
        )
        
        # Pivot to create cohort matrix
        frequency_matrix = avg_frequency.pivot(
            index='cohort_month',
            columns='period',
            values='transactions'
        )
        
        return frequency_matrix
    
    def get_cohort_summary(
        self, 
        retention_matrix: pd.DataFrame,
        revenue_matrix: pd.DataFrame
    ) -> Dict:
        """
        Generate summary statistics from cohort analysis.
        
        Args:
            retention_matrix: Retention percentage matrix
            revenue_matrix: Revenue matrix
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'total_cohorts': len(retention_matrix),
            'avg_retention_month_1': retention_matrix[1].mean() if 1 in retention_matrix.columns else 0,
            'avg_retention_month_3': retention_matrix[3].mean() if 3 in retention_matrix.columns else 0,
            'avg_retention_month_6': retention_matrix[6].mean() if 6 in retention_matrix.columns else 0,
            'best_cohort': retention_matrix[1].idxmax() if 1 in retention_matrix.columns else None,
            'worst_cohort': retention_matrix[1].idxmin() if 1 in retention_matrix.columns else None,
            'total_revenue': revenue_matrix.sum().sum(),
            'avg_cohort_revenue': revenue_matrix.sum(axis=1).mean()
        }
        
        return summary
    
    def identify_best_cohorts(
        self, 
        retention_matrix: pd.DataFrame,
        top_n: int = 5
    ) -> pd.DataFrame:
        """
        Identify best performing cohorts.
        
        Args:
            retention_matrix: Retention percentage matrix
            top_n: Number of top cohorts to return
            
        Returns:
            DataFrame with best cohorts
        """
        # Calculate average retention across all periods
        avg_retention = retention_matrix.mean(axis=1).sort_values(ascending=False)
        
        best_cohorts = avg_retention.head(top_n).reset_index()
        best_cohorts.columns = ['cohort_month', 'avg_retention_rate']
        
        return best_cohorts
    
    def calculate_ltv_by_cohort(
        self, 
        cohort_df: pd.DataFrame,
        months: int = 12
    ) -> pd.DataFrame:
        """
        Calculate customer lifetime value by cohort.
        
        Args:
            cohort_df: Prepared cohort DataFrame
            months: Number of months to calculate LTV for
            
        Returns:
            DataFrame with LTV by cohort
        """
        # Filter to specified period
        filtered_df = cohort_df[cohort_df['period'] <= months]
        
        # Calculate total revenue per customer per cohort
        customer_ltv = (
            filtered_df.groupby(['cohort_month', 'customer_id'])['total_amount']
            .sum()
            .reset_index()
        )
        
        # Calculate average LTV per cohort
        cohort_ltv = (
            customer_ltv.groupby('cohort_month')['total_amount']
            .agg(['mean', 'median', 'std'])
            .reset_index()
        )
        
        cohort_ltv.columns = ['cohort_month', 'avg_ltv', 'median_ltv', 'std_ltv']
        
        return cohort_ltv
    
    def generate_cohort_insights(
        self, 
        retention_matrix: pd.DataFrame,
        revenue_matrix: pd.DataFrame
    ) -> Dict:
        """
        Generate actionable insights from cohort analysis.
        
        Args:
            retention_matrix: Retention percentage matrix
            revenue_matrix: Revenue matrix
            
        Returns:
            Dictionary with insights
        """
        insights = {
            'observations': [],
            'recommendations': []
        }
        
        # Check month-1 retention
        if 1 in retention_matrix.columns:
            avg_month1_retention = retention_matrix[1].mean()
            
            if avg_month1_retention < 30:
                insights['observations'].append(
                    f"Low month-1 retention: {avg_month1_retention:.1f}%"
                )
                insights['recommendations'].append(
                    "Improve onboarding experience and early engagement"
                )
            elif avg_month1_retention > 50:
                insights['observations'].append(
                    f"Strong month-1 retention: {avg_month1_retention:.1f}%"
                )
        
        # Check retention trend
        if len(retention_matrix.columns) >= 3:
            recent_cohorts = retention_matrix.tail(3)
            if recent_cohorts[1].mean() < retention_matrix[1].mean():
                insights['observations'].append(
                    "Recent cohorts showing lower retention"
                )
                insights['recommendations'].append(
                    "Investigate changes in acquisition channels or product experience"
                )
        
        # Revenue concentration
        total_revenue = revenue_matrix.sum().sum()
        first_month_revenue = revenue_matrix[0].sum() if 0 in revenue_matrix.columns else 0
        
        if first_month_revenue / total_revenue > 0.5:
            insights['observations'].append(
                "Revenue heavily concentrated in first month"
            )
            insights['recommendations'].append(
                "Focus on driving repeat purchases and long-term engagement"
            )
        
        return insights


# Global cohort analyzer instance
cohort_analyzer = CohortAnalyzer()



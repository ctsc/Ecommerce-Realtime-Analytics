"""
Product recommendation engine module.
Implements collaborative filtering and content-based recommendations.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from collections import defaultdict, Counter
from sklearn.metrics.pairwise import cosine_similarity

from src.utils.logging_config import get_logger


logger = get_logger(__name__)


class RecommendationEngine:
    """
    Product recommendation engine using collaborative filtering.
    Generates personalized product recommendations based on purchase history.
    """
    
    def __init__(self):
        """Initialize recommendation engine."""
        self.customer_product_matrix = None
        self.product_similarity_matrix = None
        self.product_index_map = {}
        self.index_product_map = {}
        
        logger.info("Recommendation Engine initialized")
    
    def build_customer_product_matrix(
        self, 
        transactions_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Build customer-product interaction matrix.
        
        Args:
            transactions_df: DataFrame with transaction data
            
        Returns:
            Customer-product matrix
        """
        logger.info("Building customer-product matrix...")
        
        # Create interaction matrix (customer x product)
        # Value is purchase count or total amount spent
        matrix = transactions_df.pivot_table(
            index='customer_id',
            columns='product_id',
            values='total_amount',
            aggfunc='sum',
            fill_value=0
        )
        
        self.customer_product_matrix = matrix
        
        # Create product index mappings
        self.product_index_map = {
            prod: idx for idx, prod in enumerate(matrix.columns)
        }
        self.index_product_map = {
            idx: prod for prod, idx in self.product_index_map.items()
        }
        
        logger.info(
            f"Matrix built: {matrix.shape[0]} customers x {matrix.shape[1]} products"
        )
        
        return matrix
    
    def calculate_product_similarity(self):
        """
        Calculate product-product similarity matrix using cosine similarity.
        """
        if self.customer_product_matrix is None:
            raise ValueError("Customer-product matrix not built yet")
        
        logger.info("Calculating product similarity...")
        
        # Transpose to get product x customer matrix
        product_customer_matrix = self.customer_product_matrix.T
        
        # Calculate cosine similarity between products
        similarity = cosine_similarity(product_customer_matrix)
        
        self.product_similarity_matrix = pd.DataFrame(
            similarity,
            index=product_customer_matrix.index,
            columns=product_customer_matrix.index
        )
        
        logger.info("Product similarity calculated")
    
    def recommend_for_customer(
        self, 
        customer_id: str,
        n_recommendations: int = 5,
        exclude_purchased: bool = True
    ) -> List[Tuple[str, float]]:
        """
        Generate product recommendations for a customer.
        
        Args:
            customer_id: Customer identifier
            n_recommendations: Number of recommendations to generate
            exclude_purchased: Whether to exclude already purchased products
            
        Returns:
            List of (product_id, score) tuples
        """
        if self.customer_product_matrix is None or self.product_similarity_matrix is None:
            logger.warning("Matrices not built. Cannot generate recommendations.")
            return []
        
        # Check if customer exists
        if customer_id not in self.customer_product_matrix.index:
            logger.warning(f"Customer {customer_id} not found in matrix")
            return self._recommend_popular_products(n_recommendations)
        
        # Get customer's purchase history
        customer_purchases = self.customer_product_matrix.loc[customer_id]
        purchased_products = customer_purchases[customer_purchases > 0].index.tolist()
        
        if not purchased_products:
            return self._recommend_popular_products(n_recommendations)
        
        # Calculate recommendation scores
        scores = defaultdict(float)
        
        for product in purchased_products:
            if product in self.product_similarity_matrix.index:
                # Get similar products
                similar_products = self.product_similarity_matrix[product]
                
                # Weight by customer's interaction strength
                weight = customer_purchases[product]
                
                for similar_prod, similarity_score in similar_products.items():
                    if similar_prod != product:
                        scores[similar_prod] += similarity_score * weight
        
        # Exclude already purchased products if requested
        if exclude_purchased:
            for product in purchased_products:
                if product in scores:
                    del scores[product]
        
        # Sort by score and return top N
        recommendations = sorted(
            scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:n_recommendations]
        
        return recommendations
    
    def _recommend_popular_products(
        self, 
        n_recommendations: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Recommend most popular products (fallback for new customers).
        
        Args:
            n_recommendations: Number of recommendations
            
        Returns:
            List of (product_id, score) tuples
        """
        if self.customer_product_matrix is None:
            return []
        
        # Calculate product popularity (total purchases)
        popularity = self.customer_product_matrix.sum(axis=0)
        
        # Get top products
        top_products = popularity.nlargest(n_recommendations)
        
        recommendations = [(prod, score) for prod, score in top_products.items()]
        
        return recommendations
    
    def recommend_similar_products(
        self, 
        product_id: str,
        n_recommendations: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find similar products to a given product.
        
        Args:
            product_id: Product identifier
            n_recommendations: Number of similar products to return
            
        Returns:
            List of (product_id, similarity_score) tuples
        """
        if self.product_similarity_matrix is None:
            logger.warning("Product similarity matrix not calculated")
            return []
        
        if product_id not in self.product_similarity_matrix.index:
            logger.warning(f"Product {product_id} not found in similarity matrix")
            return []
        
        # Get similarity scores for the product
        similar_products = self.product_similarity_matrix[product_id]
        
        # Exclude the product itself
        similar_products = similar_products[similar_products.index != product_id]
        
        # Get top N
        top_similar = similar_products.nlargest(n_recommendations)
        
        recommendations = [(prod, score) for prod, score in top_similar.items()]
        
        return recommendations
    
    def recommend_frequently_bought_together(
        self,
        transactions_df: pd.DataFrame,
        product_id: str,
        n_recommendations: int = 5
    ) -> List[Tuple[str, int]]:
        """
        Find products frequently bought together with a given product.
        
        Args:
            transactions_df: Transaction data
            product_id: Product identifier
            n_recommendations: Number of recommendations
            
        Returns:
            List of (product_id, co-occurrence_count) tuples
        """
        # Get all transactions containing the product
        transactions_with_product = transactions_df[
            transactions_df['product_id'] == product_id
        ]['transaction_id'].unique()
        
        if len(transactions_with_product) == 0:
            return []
        
        # Get all products in those transactions
        co_purchased = transactions_df[
            transactions_df['transaction_id'].isin(transactions_with_product)
        ]
        
        # Count co-occurrences
        product_counts = Counter(co_purchased['product_id'])
        
        # Remove the original product
        if product_id in product_counts:
            del product_counts[product_id]
        
        # Get top N
        top_products = product_counts.most_common(n_recommendations)
        
        return top_products
    
    def recommend_by_category(
        self,
        transactions_df: pd.DataFrame,
        customer_id: str,
        n_recommendations: int = 5
    ) -> List[Tuple[str, str, float]]:
        """
        Recommend products from customer's favorite categories.
        
        Args:
            transactions_df: Transaction data
            customer_id: Customer identifier
            n_recommendations: Number of recommendations
            
        Returns:
            List of (product_id, category, score) tuples
        """
        # Get customer's purchase history
        customer_txs = transactions_df[
            transactions_df['customer_id'] == customer_id
        ]
        
        if len(customer_txs) == 0:
            return []
        
        # Find favorite categories
        category_spend = customer_txs.groupby('category')['total_amount'].sum()
        favorite_categories = category_spend.nlargest(3).index.tolist()
        
        # Get products from favorite categories (that customer hasn't purchased)
        purchased_products = customer_txs['product_id'].unique()
        
        recommendations = []
        for category in favorite_categories:
            category_products = transactions_df[
                (transactions_df['category'] == category) &
                (~transactions_df['product_id'].isin(purchased_products))
            ]
            
            # Get most popular products in category
            popular = category_products.groupby('product_id')['total_amount'].sum()
            
            for product_id, score in popular.nlargest(n_recommendations).items():
                recommendations.append((product_id, category, score))
        
        # Sort by score and get top N
        recommendations.sort(key=lambda x: x[2], reverse=True)
        
        return recommendations[:n_recommendations]
    
    def batch_recommend(
        self,
        customer_ids: List[str],
        n_recommendations: int = 5
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Generate recommendations for multiple customers.
        
        Args:
            customer_ids: List of customer identifiers
            n_recommendations: Number of recommendations per customer
            
        Returns:
            Dictionary mapping customer_id to recommendations
        """
        results = {}
        
        for customer_id in customer_ids:
            results[customer_id] = self.recommend_for_customer(
                customer_id, 
                n_recommendations
            )
        
        logger.info(f"Generated recommendations for {len(customer_ids)} customers")
        
        return results
    
    def evaluate_recommendations(
        self,
        test_transactions_df: pd.DataFrame,
        n_recommendations: int = 5
    ) -> Dict[str, float]:
        """
        Evaluate recommendation quality using test data.
        
        Args:
            test_transactions_df: Test transaction data
            n_recommendations: Number of recommendations to evaluate
            
        Returns:
            Dictionary with evaluation metrics
        """
        if self.customer_product_matrix is None:
            return {"error": "Model not trained"}
        
        hits = 0
        total = 0
        
        # Get unique customers in test set
        test_customers = test_transactions_df['customer_id'].unique()
        
        for customer_id in test_customers:
            if customer_id not in self.customer_product_matrix.index:
                continue
            
            # Get actual purchases in test period
            actual_purchases = test_transactions_df[
                test_transactions_df['customer_id'] == customer_id
            ]['product_id'].unique()
            
            # Get recommendations
            recommendations = self.recommend_for_customer(
                customer_id, 
                n_recommendations
            )
            recommended_products = [r[0] for r in recommendations]
            
            # Check hits
            for product in actual_purchases:
                total += 1
                if product in recommended_products:
                    hits += 1
        
        # Calculate metrics
        hit_rate = hits / total if total > 0 else 0
        
        metrics = {
            "hit_rate": hit_rate,
            "total_evaluations": total,
            "hits": hits
        }
        
        logger.info(f"Evaluation complete: Hit rate = {hit_rate:.2%}")
        
        return metrics


# Global recommendation engine instance
recommendation_engine = RecommendationEngine()



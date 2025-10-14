"""
Transaction data generator for the e-commerce analytics pipeline.
Simulates realistic transaction data with configurable fraud patterns.
"""

import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List
from faker import Faker
import uuid

from src.ingestion.kafka_producer import KafkaTransactionProducer
from src.utils.config import config
from src.utils.logging_config import get_logger


logger = get_logger(__name__)
fake = Faker()


class TransactionGenerator:
    """
    Generates realistic e-commerce transaction data.
    Includes normal and fraudulent transaction patterns.
    """
    
    def __init__(
        self,
        num_customers: int = 10000,
        num_products: int = 500,
        fraud_rate: float = 0.02
    ):
        """
        Initialize transaction generator.
        
        Args:
            num_customers: Number of unique customers to simulate
            num_products: Number of unique products in catalog
            fraud_rate: Percentage of transactions that are fraudulent (0.02 = 2%)
        """
        self.num_customers = num_customers
        self.num_products = num_products
        self.fraud_rate = fraud_rate
        
        # Initialize data
        self.customers = self._generate_customers()
        self.products = self._generate_products()
        
        # Customer behavior tracking (for realistic patterns)
        self.customer_history = {}
        
        logger.info(
            f"Transaction generator initialized: "
            f"{num_customers} customers, {num_products} products"
        )
    
    def _generate_customers(self) -> List[Dict]:
        """Generate customer profiles."""
        customers = []
        locations = [
            "New York, NY", "Los Angeles, CA", "Chicago, IL", 
            "Houston, TX", "Phoenix, AZ", "Philadelphia, PA",
            "San Antonio, TX", "San Diego, CA", "Dallas, TX", 
            "San Jose, CA", "Austin, TX", "Seattle, WA"
        ]
        
        for i in range(self.num_customers):
            customer = {
                "customer_id": f"CUST{str(i).zfill(8)}",
                "email": fake.email(),
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "location": random.choice(locations),
                "registration_date": fake.date_time_between(
                    start_date="-2y", 
                    end_date="-1m"
                )
            }
            customers.append(customer)
        
        return customers
    
    def _generate_products(self) -> List[Dict]:
        """Generate product catalog."""
        products = []
        categories = config.generator.categories
        
        for i in range(self.num_products):
            category = random.choice(categories)
            
            # Price ranges by category
            price_ranges = {
                "Electronics": (50, 2000),
                "Clothing": (20, 300),
                "Home & Garden": (15, 500),
                "Books": (10, 50),
                "Sports": (25, 400),
                "Toys": (10, 150),
                "Food & Beverage": (5, 100),
                "Health & Beauty": (10, 200),
                "Automotive": (20, 1000),
                "Office Supplies": (5, 200)
            }
            
            min_price, max_price = price_ranges.get(category, (10, 100))
            
            product = {
                "product_id": f"PROD{str(i).zfill(6)}",
                "product_name": fake.catch_phrase(),
                "category": category,
                "unit_price": round(random.uniform(min_price, max_price), 2),
                "description": fake.text(max_nb_chars=200)
            }
            products.append(product)
        
        return products
    
    def _get_customer_behavior(self, customer_id: str) -> Dict:
        """Get or create customer behavior profile."""
        if customer_id not in self.customer_history:
            self.customer_history[customer_id] = {
                "transaction_count": 0,
                "total_spent": 0.0,
                "avg_amount": 0.0,
                "favorite_categories": [],
                "last_transaction_time": None
            }
        return self.customer_history[customer_id]
    
    def _update_customer_behavior(
        self, 
        customer_id: str, 
        amount: float, 
        category: str
    ):
        """Update customer behavior after transaction."""
        behavior = self._get_customer_behavior(customer_id)
        behavior["transaction_count"] += 1
        behavior["total_spent"] += amount
        behavior["avg_amount"] = behavior["total_spent"] / behavior["transaction_count"]
        behavior["last_transaction_time"] = datetime.now()
        
        # Track favorite categories
        if category not in behavior["favorite_categories"]:
            behavior["favorite_categories"].append(category)
    
    def _should_be_fraudulent(self) -> bool:
        """Determine if transaction should be fraudulent."""
        return random.random() < self.fraud_rate
    
    def _generate_fraudulent_transaction(self) -> Dict:
        """
        Generate a fraudulent transaction with suspicious patterns.
        
        Fraud patterns:
        1. Unusually high amount
        2. Multiple transactions in short time
        3. Unusual location
        4. Odd hour (late night)
        5. Multiple high-value items
        """
        customer = random.choice(self.customers)
        product = random.choice(self.products)
        
        # Fraudulent patterns
        fraud_patterns = random.choice([
            "high_amount",
            "rapid_transactions",
            "unusual_location",
            "odd_hours"
        ])
        
        # Base transaction
        quantity = random.randint(1, 5)
        
        if fraud_patterns == "high_amount":
            # Abnormally high purchase
            product = random.choice([p for p in self.products if p["unit_price"] > 500])
            quantity = random.randint(5, 20)
        
        total_amount = product["unit_price"] * quantity
        
        # Set timestamp to odd hours for some frauds
        if fraud_patterns == "odd_hours":
            hour = random.choice([1, 2, 3, 4, 5])
        else:
            hour = datetime.now().hour
        
        timestamp = datetime.now().replace(hour=hour)
        
        transaction = {
            "transaction_id": str(uuid.uuid4()),
            "timestamp": timestamp.isoformat(),
            "customer_id": customer["customer_id"],
            "customer_email": customer["email"],
            "customer_location": customer["location"],
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "category": product["category"],
            "quantity": quantity,
            "unit_price": product["unit_price"],
            "total_amount": round(total_amount, 2),
            "is_fraud": True,
            "fraud_pattern": fraud_patterns
        }
        
        return transaction
    
    def _generate_normal_transaction(self) -> Dict:
        """Generate a normal, non-fraudulent transaction."""
        customer = random.choice(self.customers)
        behavior = self._get_customer_behavior(customer["customer_id"])
        
        # Select product (prefer favorite categories if available)
        if behavior["favorite_categories"] and random.random() < 0.7:
            favorite_cat = random.choice(behavior["favorite_categories"])
            products_in_cat = [
                p for p in self.products if p["category"] == favorite_cat
            ]
            product = random.choice(products_in_cat) if products_in_cat else random.choice(self.products)
        else:
            product = random.choice(self.products)
        
        # Realistic quantities (mostly 1-3 items)
        quantity = random.choices([1, 2, 3, 4, 5], weights=[50, 30, 15, 4, 1])[0]
        total_amount = product["unit_price"] * quantity
        
        transaction = {
            "transaction_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "customer_id": customer["customer_id"],
            "customer_email": customer["email"],
            "customer_location": customer["location"],
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "category": product["category"],
            "quantity": quantity,
            "unit_price": product["unit_price"],
            "total_amount": round(total_amount, 2),
            "is_fraud": False
        }
        
        # Update customer behavior
        self._update_customer_behavior(
            customer["customer_id"], 
            total_amount, 
            product["category"]
        )
        
        return transaction
    
    def generate_transaction(self) -> Dict:
        """
        Generate a single transaction (normal or fraudulent).
        
        Returns:
            Transaction dictionary
        """
        if self._should_be_fraudulent():
            return self._generate_fraudulent_transaction()
        else:
            return self._generate_normal_transaction()
    
    def generate_batch(self, size: int) -> List[Dict]:
        """
        Generate a batch of transactions.
        
        Args:
            size: Number of transactions to generate
            
        Returns:
            List of transaction dictionaries
        """
        return [self.generate_transaction() for _ in range(size)]


def main():
    """
    Main function to run continuous transaction generation.
    Sends transactions to Kafka in real-time.
    """
    logger.info("Starting transaction generator...")
    
    # Initialize generator
    generator = TransactionGenerator(
        num_customers=config.generator.num_customers,
        num_products=config.generator.num_products,
        fraud_rate=config.generator.fraud_rate
    )
    
    # Initialize Kafka producer
    producer = KafkaTransactionProducer()
    
    # Target rate
    transactions_per_second = config.generator.transactions_per_second
    batch_size = 10  # Send in small batches
    sleep_time = batch_size / transactions_per_second
    
    logger.info(
        f"Generating {transactions_per_second} transactions/second "
        f"(batch size: {batch_size})"
    )
    
    transaction_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Generate batch
            batch = generator.generate_batch(batch_size)
            
            # Send to Kafka
            for transaction in batch:
                producer.send_transaction(transaction)
                transaction_count += 1
            
            # Log progress every 1000 transactions
            if transaction_count % 1000 == 0:
                elapsed = time.time() - start_time
                rate = transaction_count / elapsed
                logger.info(
                    f"Generated {transaction_count} transactions "
                    f"(rate: {rate:.2f}/sec)"
                )
            
            # Sleep to maintain target rate
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        logger.info("Stopping transaction generator...")
        elapsed = time.time() - start_time
        logger.info(
            f"Total generated: {transaction_count} transactions "
            f"in {elapsed:.2f} seconds"
        )
    finally:
        producer.close()


if __name__ == "__main__":
    main()



# API Documentation

Complete API reference for all modules in the e-commerce analytics pipeline.

## Table of Contents

1. [Configuration](#configuration)
2. [Data Ingestion](#data-ingestion)
3. [Stream Processing](#stream-processing)
4. [Storage](#storage)
5. [Analytics](#analytics)
6. [Visualization](#visualization)
7. [Utilities](#utilities)

---

## Configuration

### `src.utils.config`

Central configuration management for the entire pipeline.

#### `Config` Class

```python
from src.utils.config import config

# Access configuration
print(config.kafka.bootstrap_servers)
print(config.database.connection_string)
print(config.generator.transactions_per_second)
```

**Attributes:**
- `kafka`: KafkaConfig - Kafka connection settings
- `database`: DatabaseConfig - PostgreSQL settings
- `spark`: SparkConfig - Spark configuration
- `generator`: GeneratorConfig - Transaction generator settings
- `fraud_detection`: FraudDetectionConfig - Fraud model settings
- `dashboard`: DashboardConfig - Dashboard settings

---

## Data Ingestion

### `src.ingestion.transaction_generator`

#### `TransactionGenerator` Class

Generates realistic e-commerce transaction data.

```python
from src.ingestion.transaction_generator import TransactionGenerator

generator = TransactionGenerator(
    num_customers=10000,
    num_products=500,
    fraud_rate=0.02
)

# Generate single transaction
transaction = generator.generate_transaction()

# Generate batch
batch = generator.generate_batch(100)
```

**Methods:**

##### `generate_transaction() -> Dict`
Generates a single transaction (normal or fraudulent).

**Returns:** Dictionary with transaction data
```python
{
    'transaction_id': 'uuid',
    'timestamp': 'ISO-8601 string',
    'customer_id': 'CUST00001234',
    'product_id': 'PROD001234',
    'total_amount': 123.45,
    'is_fraud': False,
    # ... more fields
}
```

##### `generate_batch(size: int) -> List[Dict]`
Generates multiple transactions.

**Parameters:**
- `size`: Number of transactions to generate

**Returns:** List of transaction dictionaries

---

### `src.ingestion.kafka_producer`

#### `KafkaTransactionProducer` Class

Sends transactions to Kafka topics.

```python
from src.ingestion.kafka_producer import KafkaTransactionProducer

producer = KafkaTransactionProducer()

# Send single transaction
producer.send_transaction(transaction)

# Send batch
producer.send_batch(transactions)

# Cleanup
producer.close()
```

**Methods:**

##### `send_transaction(transaction: Dict, key: Optional[str] = None) -> bool`
Send a single transaction to Kafka.

**Parameters:**
- `transaction`: Transaction dictionary
- `key`: Optional partition key (defaults to customer_id)

**Returns:** True if successfully queued

##### `get_stats() -> Dict`
Get producer statistics.

**Returns:** Dictionary with success_count, error_count, success_rate

---

## Stream Processing

### `src.processing.spark_consumer`

#### `SparkTransactionConsumer` Class

Consumes and processes transactions from Kafka using Spark Streaming.

```python
from src.processing.spark_consumer import SparkTransactionConsumer

consumer = SparkTransactionConsumer()
consumer.run()  # Starts streaming
```

**Methods:**

##### `read_from_kafka() -> DataFrame`
Creates a streaming DataFrame from Kafka.

##### `process_transactions(df: DataFrame) -> DataFrame`
Applies transformations to transactions.

##### `write_to_postgres(df: DataFrame, checkpoint: str, table: str) -> StreamingQuery`
Writes streaming data to PostgreSQL.

---

### `src.processing.fraud_detection`

#### `FraudDetectionEngine` Class

ML-powered fraud detection using Isolation Forest.

```python
from src.processing.fraud_detection import FraudDetectionEngine

engine = FraudDetectionEngine()

# Train on historical data
engine.train(transactions_df)

# Predict on new transaction
is_fraud, score, reasons = engine.predict(transaction, customer_history)

# Save model
engine.save_model()
```

**Methods:**

##### `train(transactions: pd.DataFrame)`
Train the fraud detection model.

**Parameters:**
- `transactions`: DataFrame with historical transactions

##### `predict(transaction: Dict, customer_history: Dict = None) -> Tuple[bool, float, List[str]]`
Predict if transaction is fraudulent.

**Returns:** Tuple of (is_fraud, fraud_score, reasons)
- `is_fraud`: Boolean flag
- `fraud_score`: 0-100 score (higher = more suspicious)
- `reasons`: List of explanation strings

##### `extract_features(transaction: Dict, customer_history: Dict = None) -> np.ndarray`
Extract features for model input.

---

## Storage

### `src.storage.database`

#### `DatabaseManager` Class

Handles all database operations.

```python
from src.storage.database import db_manager

# Create tables
db_manager.create_tables()

# Get session
with db_manager.get_session() as session:
    # Use session
    transactions = session.query(Transaction).limit(10).all()

# Bulk insert
db_manager.bulk_insert_transactions(transaction_list)

# Get stats
stats = db_manager.get_database_stats()
```

**Methods:**

##### `get_session() -> Session`
Context manager for database sessions.

##### `bulk_insert_transactions(transactions: List[Dict]) -> int`
Efficiently insert multiple transactions.

**Returns:** Number of records inserted

##### `get_recent_transactions(limit: int = 100, fraud_only: bool = False) -> List[Transaction]`
Query recent transactions.

##### `get_customer_stats(customer_id: str) -> Dict`
Get aggregated customer statistics.

##### `get_database_stats() -> Dict`
Get overall database statistics.

---

### `src.storage.models`

SQLAlchemy ORM models.

#### `Transaction` Model

```python
from src.storage.models import Transaction

# Fields
transaction.transaction_id  # Primary key
transaction.timestamp       # DateTime
transaction.customer_id     # String
transaction.total_amount    # Float
transaction.is_fraud        # Boolean
# ... more fields
```

#### `Customer` Model

```python
from src.storage.models import Customer

customer.customer_id       # Primary key
customer.rfm_score         # String
customer.customer_segment  # String
customer.lifetime_value    # Float
# ... more fields
```

---

## Analytics

### `src.analytics.rfm_analysis`

#### `RFMAnalyzer` Class

Customer segmentation using RFM analysis.

```python
from src.analytics.rfm_analysis import RFMAnalyzer

analyzer = RFMAnalyzer()

# Calculate RFM
rfm_df = analyzer.calculate_rfm(transactions_df)

# Get segment summary
summary = analyzer.get_segment_summary(rfm_df)

# Identify high-value customers
top_customers = analyzer.identify_high_value_customers(rfm_df, top_n=100)

# Get actionable insights
insights = analyzer.get_actionable_insights(rfm_df)
```

**Methods:**

##### `calculate_rfm(transactions_df: pd.DataFrame) -> pd.DataFrame`
Calculate RFM scores for all customers.

**Returns:** DataFrame with columns:
- `customer_id`
- `recency`, `frequency`, `monetary`
- `r_score`, `f_score`, `m_score` (1-5)
- `rfm_score` (e.g., "555")
- `segment` (e.g., "Champions")

##### `get_segment_summary(rfm_df: pd.DataFrame) -> pd.DataFrame`
Aggregate statistics by segment.

##### `identify_at_risk_customers(rfm_df: pd.DataFrame) -> pd.DataFrame`
Find customers at risk of churning.

---

### `src.analytics.cohort_analysis`

#### `CohortAnalyzer` Class

Retention and engagement tracking by cohort.

```python
from src.analytics.cohort_analysis import CohortAnalyzer

analyzer = CohortAnalyzer()

# Prepare data
cohort_df = analyzer.prepare_cohort_data(transactions_df)

# Calculate retention
cohort_matrix, retention_matrix = analyzer.calculate_retention_cohort(cohort_df)

# Calculate revenue by cohort
revenue_matrix = analyzer.calculate_revenue_cohort(cohort_df)

# Get insights
insights = analyzer.generate_cohort_insights(retention_matrix, revenue_matrix)
```

**Methods:**

##### `calculate_retention_cohort(cohort_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]`
Calculate retention rates.

**Returns:** Tuple of (cohort_counts, retention_percentages)

##### `calculate_ltv_by_cohort(cohort_df: pd.DataFrame, months: int = 12) -> pd.DataFrame`
Calculate customer lifetime value by cohort.

---

### `src.analytics.recommendations`

#### `RecommendationEngine` Class

Product recommendation system.

```python
from src.analytics.recommendations import RecommendationEngine

engine = RecommendationEngine()

# Build matrices
engine.build_customer_product_matrix(transactions_df)
engine.calculate_product_similarity()

# Get recommendations
recommendations = engine.recommend_for_customer('CUST001', n_recommendations=5)
# Returns: [('PROD123', 0.95), ('PROD456', 0.87), ...]

# Similar products
similar = engine.recommend_similar_products('PROD001', n_recommendations=5)

# Frequently bought together
fbt = engine.recommend_frequently_bought_together(transactions_df, 'PROD001')
```

**Methods:**

##### `recommend_for_customer(customer_id: str, n_recommendations: int = 5) -> List[Tuple[str, float]]`
Generate personalized recommendations.

**Returns:** List of (product_id, score) tuples

##### `recommend_similar_products(product_id: str, n_recommendations: int = 5) -> List[Tuple[str, float]]`
Find similar products.

##### `batch_recommend(customer_ids: List[str], n_recommendations: int = 5) -> Dict`
Generate recommendations for multiple customers.

---

## Visualization

### `src.visualization.dashboard`

#### Dash Application

Real-time analytics dashboard.

```python
from src.visualization.dashboard import run_dashboard

# Start dashboard server
run_dashboard()
# Dashboard available at http://localhost:8050
```

**Components:**
- Real-time metrics cards
- Transaction volume graph
- Revenue by category pie chart
- Fraud detection timeline
- Customer segmentation bar chart
- Recent fraud alerts table

---

## Utilities

### `src.utils.logging_config`

#### `get_logger(name: str) -> logging.Logger`

Get a configured logger.

```python
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message")
```

---

### `src.utils.metrics`

#### `MetricsCollector` Class

Collect and aggregate pipeline metrics.

```python
from src.utils.metrics import metrics_collector

# Record events
metrics_collector.record_transaction(latency=0.5)
metrics_collector.record_fraud()
metrics_collector.record_error()

# Get current metrics
metrics = metrics_collector.get_metrics()

print(f"Processed: {metrics.transactions_processed}")
print(f"Throughput: {metrics.transactions_per_second}/sec")
print(f"Fraud rate: {metrics.fraud_rate}%")
```

**Methods:**

##### `record_transaction(latency: float = None)`
Record a processed transaction.

##### `record_fraud()`
Record a fraud detection.

##### `get_metrics() -> PipelineMetrics`
Get current metrics snapshot.

---

## Type Definitions

### Transaction Dictionary

```python
{
    'transaction_id': str,          # Unique identifier
    'timestamp': str,                # ISO-8601 format
    'customer_id': str,              # Customer identifier
    'customer_email': str,           # Email address
    'customer_location': str,        # City, State
    'product_id': str,               # Product identifier
    'product_name': str,             # Product name
    'category': str,                 # Product category
    'quantity': int,                 # Quantity purchased
    'unit_price': float,             # Price per unit
    'total_amount': float,           # Total transaction amount
    'is_fraud': bool,                # Fraud flag
    'fraud_pattern': str | None      # Pattern if fraudulent
}
```

### Customer History Dictionary

```python
{
    'transaction_count': int,        # Number of transactions
    'total_spent': float,            # Total amount spent
    'avg_amount': float,             # Average transaction amount
    'last_transaction_time': datetime,  # Most recent purchase
    'favorite_categories': List[str]    # Preferred categories
}
```

---

## Error Handling

All methods use proper exception handling. Common exceptions:

- `ConnectionError`: Database or Kafka connection issues
- `ValueError`: Invalid input parameters
- `RuntimeError`: Processing errors
- `KafkaError`: Kafka-specific errors

Example:

```python
try:
    producer.send_transaction(transaction)
except KafkaError as e:
    logger.error(f"Kafka error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

---

## Environment Variables

Override configuration using environment variables:

```bash
export KAFKA_BOOTSTRAP_SERVERS="kafka:9092"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="ecommerce"
export DB_USER="dataengineer"
export DB_PASSWORD="SecurePass123!"
```

---

## Examples

### Complete Pipeline Example

```python
from src.ingestion.transaction_generator import TransactionGenerator
from src.ingestion.kafka_producer import KafkaTransactionProducer
from src.processing.fraud_detection import FraudDetectionEngine

# Setup
generator = TransactionGenerator()
producer = KafkaTransactionProducer()
fraud_engine = FraudDetectionEngine()

# Generate and send transactions
for _ in range(100):
    tx = generator.generate_transaction()
    
    # Check for fraud
    is_fraud, score, reasons = fraud_engine.predict(tx)
    tx['fraud_score'] = score
    tx['fraud_reason'] = reasons[0] if reasons else None
    
    # Send to Kafka
    producer.send_transaction(tx)

producer.close()
```

---

For more examples, see the `tests/` directory.


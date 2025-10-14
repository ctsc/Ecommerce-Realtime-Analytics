# System Architecture

## Overview

This document describes the architecture of the Real-Time E-Commerce Analytics Pipeline, including component interactions, data flow, and design decisions.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Ingestion Layer                         │
├─────────────────────────────────────────────────────────────────┤
│  Transaction Generator  →  Kafka Producer  →  Kafka Topics      │
│  (10K+ tx/min)            (JSON messages)     (partitioned)     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Stream Processing Layer                       │
├─────────────────────────────────────────────────────────────────┤
│              Apache Spark Structured Streaming                   │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │  Kafka     │→ │ Transformations│→│ Fraud Detection │       │
│  │  Consumer  │  │  & Enrichment │  │   (Isolation    │       │
│  └────────────┘  └──────────────┘  │    Forest)      │       │
│                                     └──────────────────┘       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Storage Layer                               │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL Database (Transactional + Analytical Storage)       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Transactions │  │  Customers   │  │ Fraud Alerts │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Analytics Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────────┐    │
│  │ RFM Analysis│  │Cohort Analysis │  │ Recommendation   │    │
│  │  (Customer  │  │  (Retention    │  │   Engine         │    │
│  │Segmentation)│  │   Tracking)    │  │ (Collaborative   │    │
│  └─────────────┘  └────────────────┘  │  Filtering)      │    │
│                                        └──────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Visualization Layer                             │
├─────────────────────────────────────────────────────────────────┤
│              Plotly Dash Interactive Dashboard                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │ Real-time  │  │  Customer  │  │   Fraud    │               │
│  │  Metrics   │  │  Analytics │  │  Alerts    │               │
│  └────────────┘  └────────────┘  └────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Data Ingestion Layer

#### Transaction Generator
- **Purpose**: Simulates realistic e-commerce transaction data
- **Rate**: Configurable (default: 100 tx/sec = 6,000 tx/min)
- **Features**:
  - Customer behavior modeling
  - Realistic product categories and pricing
  - Fraud pattern injection (configurable rate)
  - Time-based patterns (business hours, weekends)

#### Kafka Producer
- **Technology**: kafka-python
- **Configuration**:
  - Acknowledgment: `acks=all` (ensures durability)
  - Compression: `gzip` (reduces network traffic)
  - Batching: 16KB batches, 10ms linger time
- **Partitioning Strategy**: Customer ID based (keeps customer data together)

#### Kafka Topics
- `ecommerce-transactions`: Main transaction stream
- `fraud-alerts`: High-priority fraud notifications
- **Partitions**: 3 (configurable)
- **Replication Factor**: 1 (increase for production)

### 2. Stream Processing Layer

#### Spark Structured Streaming
- **Execution Mode**: Continuous processing with micro-batches
- **Batch Duration**: 5 seconds (configurable)
- **Features**:
  - Exactly-once processing semantics
  - Automatic checkpointing for fault tolerance
  - Watermarking for late data handling

#### Data Transformations
1. **Timestamp Parsing**: Convert ISO strings to timestamp type
2. **Feature Engineering**:
   - Hour of day (0-23)
   - Day of week (0-6)
   - Derived metrics
3. **Data Validation**: Schema enforcement, null checks
4. **Enrichment**: Join with customer history (future enhancement)

#### Fraud Detection
- **Algorithm**: Isolation Forest (anomaly detection)
- **Features Used**:
  - Transaction amount
  - Hour of day
  - Day of week
  - Customer transaction count
  - Customer average amount
  - Amount deviation from customer baseline
- **Scoring**: 0-100 scale (higher = more suspicious)
- **Threshold**: 80 (configurable)

### 3. Storage Layer

#### PostgreSQL Database
- **Schema Design**: Hybrid transactional + analytical
- **Tables**:
  1. `transactions`: Fact table (partitioned by timestamp in production)
  2. `customers`: Dimension table with aggregated metrics
  3. `products`: Dimension table
  4. `fraud_alerts`: Specialized table for fraud investigation
  5. `analytics_summaries`: Pre-aggregated metrics for performance
  6. `recommendations`: Product recommendations cache

#### Indexing Strategy
- **Primary Indexes**: All primary keys (B-tree)
- **Secondary Indexes**:
  - `timestamp` columns (range queries)
  - `customer_id`, `product_id` (joins)
  - `is_fraud` flag (filtering)
  - Composite indexes for common query patterns

#### Data Retention
- **Transactions**: 90 days active, archive to data lake
- **Analytics Summaries**: 1 year
- **Fraud Alerts**: 2 years (compliance)

### 4. Analytics Layer

#### RFM Analysis
- **Algorithm**: Quintile-based scoring (1-5 scale)
- **Segments**: 11 defined segments (Champions, Loyal, At Risk, etc.)
- **Update Frequency**: Daily batch job
- **Output**: Customer segmentation, actionable insights

#### Cohort Analysis
- **Cohort Definition**: First purchase month
- **Metrics Tracked**:
  - Retention rate by period
  - Revenue by cohort
  - Average order value
  - Purchase frequency
- **Update Frequency**: Weekly

#### Recommendation Engine
- **Approach**: Collaborative filtering + content-based
- **Techniques**:
  - Item-item similarity (cosine similarity)
  - Frequently bought together
  - Category-based recommendations
- **Performance**: Sub-second recommendation generation
- **Update Frequency**: Real-time (on new purchases)

### 5. Visualization Layer

#### Plotly Dash Dashboard
- **Framework**: Dash + Bootstrap components
- **Features**:
  - Real-time metrics cards
  - Interactive graphs (time-series, pie charts, bar charts)
  - Fraud alert table
  - Auto-refresh (5 second intervals)
- **Theme**: Dark mode (Cyborg theme)
- **Responsive**: Mobile-friendly design

## Data Flow

### Real-time Transaction Flow

```
1. Transaction Generated
   ↓ [~1ms]
2. Sent to Kafka Topic
   ↓ [~10ms - network + batch]
3. Consumed by Spark
   ↓ [~50ms - micro-batch]
4. Transformations Applied
   ↓ [~100ms - processing]
5. Fraud Detection
   ↓ [~50ms - model inference]
6. Written to PostgreSQL
   ↓ [~100ms - batch insert]
7. Queryable by Dashboard
   
Total Latency: ~300-500ms (p95 < 1s)
```

### Batch Analytics Flow

```
1. Daily Trigger (cron/Airflow)
   ↓
2. Extract Transactions (last 24h)
   ↓
3. Run RFM Analysis
   ↓
4. Run Cohort Analysis
   ↓
5. Update Customer Table
   ↓
6. Generate Recommendations
   ↓
7. Update Analytics Summaries
   
Duration: ~5-10 minutes for 1M transactions
```

## Scalability Considerations

### Current Capacity
- **Throughput**: 10,000 tx/min (167 tx/sec)
- **Data Volume**: ~10GB/day at full capacity
- **Query Performance**: Sub-second for dashboard queries

### Scaling Strategies

#### Horizontal Scaling
1. **Kafka**: Add more partitions + brokers
2. **Spark**: Increase executors and cores
3. **PostgreSQL**: Read replicas for analytics queries

#### Vertical Scaling
1. **Kafka**: Larger instances for higher throughput
2. **Spark**: More memory for larger windows
3. **PostgreSQL**: More RAM for query cache

#### Future Enhancements
1. **Sharding**: Partition PostgreSQL by time range
2. **Data Lake**: Move cold data to S3/Parquet
3. **Caching**: Redis for hot customer data
4. **CDN**: Cache dashboard static assets

## Security Considerations

### Authentication & Authorization
- Database: Username/password (environment variables)
- API: JWT tokens (future)
- Dashboard: Basic auth (production)

### Data Protection
- Encryption at rest: PostgreSQL TDE (production)
- Encryption in transit: SSL/TLS for all connections
- PII Handling: Customer email hashing (GDPR compliance)

### Monitoring & Alerting
- Metrics Collection: Prometheus integration
- Log Aggregation: Centralized logging (future)
- Alerting: PagerDuty/Slack integration

## Disaster Recovery

### Backup Strategy
- **Database**: Daily full backups + WAL archiving
- **Kafka**: Topic replication (production)
- **Code**: Git version control

### Recovery Objectives
- **RTO** (Recovery Time Objective): < 1 hour
- **RPO** (Recovery Point Objective): < 5 minutes

## Performance Optimization

### Applied Optimizations
1. **Batch Processing**: Bulk inserts instead of individual
2. **Connection Pooling**: Reuse database connections
3. **Query Optimization**: Proper indexes and query structure
4. **Compression**: Gzip for Kafka messages
5. **Caching**: Pre-computed analytics summaries

### Monitoring Metrics
- Throughput (tx/sec)
- Latency (p50, p95, p99)
- Error rate
- Data quality score
- System resource utilization

## Technology Choices & Rationale

| Technology | Alternative Considered | Reason for Choice |
|------------|------------------------|-------------------|
| Kafka | RabbitMQ, Pulsar | Industry standard, proven at scale |
| Spark | Flink, Storm | Mature ecosystem, easier development |
| PostgreSQL | MySQL, MongoDB | ACID compliance, JSON support |
| Plotly Dash | Streamlit, Grafana | Python-native, highly customizable |
| Docker Compose | Kubernetes | Simpler for development, easier setup |

## Future Architecture Evolution

### Phase 2: Cloud Migration
- Deploy to AWS (EMR, MSK, RDS, QuickSight)
- Implement AWS Lambda for serverless functions
- Use S3 for data lake
- CloudWatch for monitoring

### Phase 3: Advanced Features
- Apache Airflow for orchestration
- ML model deployment with MLflow
- Real-time personalization engine
- A/B testing framework

### Phase 4: Enterprise Scale
- Multi-region deployment
- Kubernetes for container orchestration
- Service mesh (Istio) for microservices
- Advanced observability (OpenTelemetry)



# Setup Guide

This guide walks you through setting up the Real-Time E-Commerce Analytics Pipeline on your local machine.

## Prerequisites

### Required Software
- **Docker Desktop** (20.10+)
  - [Windows/Mac Download](https://www.docker.com/products/docker-desktop)
  - Linux: Install Docker Engine + Docker Compose
- **Python** (3.9 or higher)
  - [Download Python](https://www.python.org/downloads/)
- **Git** (for cloning the repository)

### System Requirements
- **RAM**: 8GB minimum, 16GB recommended
- **CPU**: 4 cores minimum
- **Disk Space**: 10GB free
- **OS**: Windows 10+, macOS 10.14+, or Linux

## Step-by-Step Installation

### 1. Clone the Repository

```bash
cd Desktop/DataProjects
# Repository is already in ecommerce-realtime-analytics/
cd ecommerce-realtime-analytics
```

### 2. Verify Docker Installation

```bash
# Check Docker is running
docker --version
docker-compose --version

# Start Docker Desktop if not running
```

### 3. Start Infrastructure Services

Start Kafka, Zookeeper, and PostgreSQL using Docker Compose:

```bash
# Start all services in detached mode
docker-compose up -d

# Verify all containers are running
docker-compose ps

# You should see:
# - zookeeper
# - kafka
# - postgres
# - pgadmin (optional)
```

**Expected Output:**
```
NAME        IMAGE                              STATUS
kafka       confluentinc/cp-kafka:7.4.0       Up
postgres    postgres:15-alpine                 Up
zookeeper   confluentinc/cp-zookeeper:7.4.0   Up
pgadmin     dpage/pgadmin4:latest              Up
```

### 4. Install Python Dependencies

Create a virtual environment (recommended):

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Note**: This may take 5-10 minutes to download all packages.

### 5. Initialize the Database

Create database tables and schema:

```bash
# Run database initialization script
python scripts/init_db.py

# To drop existing tables and recreate (careful!):
python scripts/init_db.py --drop
```

**Expected Output:**
```
INFO | Initializing database...
INFO | Creating tables...
INFO | Database initialized successfully!
INFO | Database statistics: {'total_transactions': 0, ...}
```

### 6. Verify Kafka is Ready

```bash
# Check Kafka topics (should auto-create on first use)
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092
```

## Running the Pipeline

### Terminal 1: Start Transaction Generator

This generates simulated transaction data and sends it to Kafka:

```bash
# Make sure virtual environment is activated
python src/ingestion/transaction_generator.py
```

**Expected Output:**
```
INFO | Starting transaction generator...
INFO | Generating 100 transactions/second (batch size: 10)
INFO | Generated 1000 transactions (rate: 102.45/sec)
```

### Terminal 2: Start Spark Consumer

This processes transactions in real-time:

```bash
# Open a new terminal, activate venv, then run:
python src/processing/spark_consumer.py
```

**Expected Output:**
```
INFO | Starting Spark streaming consumer...
INFO | Reading from Kafka topic: ecommerce-transactions
INFO | Streaming queries started successfully
```

**Note**: First run will download Spark dependencies (~200MB). This is normal.

### Terminal 3: Start Dashboard

Launch the interactive dashboard:

```bash
# Open a new terminal, activate venv, then run:
python src/visualization/dashboard.py
```

**Expected Output:**
```
INFO | Starting dashboard on 0.0.0.0:8050
Dash is running on http://0.0.0.0:8050/
```

### 7. Access the Dashboard

Open your browser and navigate to:
```
http://localhost:8050
```

You should see the real-time analytics dashboard with live metrics!

## Verification Checklist

- [ ] Docker containers are running (`docker-compose ps`)
- [ ] Database tables created (check logs)
- [ ] Transaction generator is producing data
- [ ] Spark consumer is processing without errors
- [ ] Dashboard is accessible at localhost:8050
- [ ] Dashboard shows increasing transaction counts

## Optional: Access pgAdmin

If you want to explore the database visually:

1. Open browser to `http://localhost:5050`
2. Login:
   - Email: `admin@ecommerce.com`
   - Password: `admin123`
3. Add server:
   - Name: `ecommerce-db`
   - Host: `postgres` (or `localhost` if connecting from host)
   - Port: `5432`
   - Username: `dataengineer`
   - Password: `SecurePass123!`

## Troubleshooting

### Issue: Docker containers won't start

**Solution:**
```bash
# Stop all containers
docker-compose down

# Remove volumes (careful: deletes data)
docker-compose down -v

# Restart
docker-compose up -d
```

### Issue: "Port already in use"

**Solution:**
```bash
# Find process using the port (Windows)
netstat -ano | findstr :5432
netstat -ano | findstr :9092

# Find process (Mac/Linux)
lsof -i :5432
lsof -i :9092

# Stop the conflicting process or change port in docker-compose.yml
```

### Issue: Python dependencies fail to install

**Solution:**
```bash
# Upgrade pip first
pip install --upgrade pip

# Install packages one by one to identify issue
pip install pyspark
pip install kafka-python
# etc...

# On Windows, if psycopg2-binary fails:
pip install psycopg2-binary --no-cache-dir
```

### Issue: Kafka "Connection refused"

**Solution:**
```bash
# Wait for Kafka to fully start (can take 30-60 seconds)
docker logs kafka

# Restart Kafka if needed
docker-compose restart kafka

# Verify Kafka is listening
docker exec -it kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

### Issue: Spark downloads are slow

**Solution:**
- First run downloads ~200MB of Spark dependencies
- Be patient, this is normal
- Subsequent runs will be much faster

### Issue: Dashboard shows "No data available"

**Solution:**
- Ensure transaction generator is running
- Ensure Spark consumer is running
- Wait 10-20 seconds for initial data to flow through
- Check database has transactions: `docker exec -it postgres psql -U dataengineer -d ecommerce -c "SELECT COUNT(*) FROM transactions;"`

### Issue: High memory usage

**Solution:**
```bash
# Reduce transaction rate in src/utils/config.py:
# transactions_per_second: int = 50  # Reduce from 100

# Reduce Spark shuffle partitions in config:
# shuffle_partitions: int = 2  # Reduce from 4

# Restart services after changes
```

## Performance Tuning

### For Higher Throughput

Edit `src/utils/config.py`:

```python
# Increase transaction rate
transactions_per_second: int = 200  # Up to 500 on good hardware

# Increase Spark parallelism
shuffle_partitions: int = 8

# Increase Kafka batch size
batch_size = 32768  # 32KB
```

### For Lower Resource Usage

```python
# Decrease transaction rate
transactions_per_second: int = 50

# Reduce Spark parallelism
shuffle_partitions: int = 2

# Reduce dashboard refresh rate
refresh_interval: int = 10000  # 10 seconds
```

## Stopping the Pipeline

### Graceful Shutdown

1. Stop transaction generator (Ctrl+C in Terminal 1)
2. Stop Spark consumer (Ctrl+C in Terminal 2)
3. Stop dashboard (Ctrl+C in Terminal 3)
4. Stop Docker containers:
   ```bash
   docker-compose down
   ```

### Keep Data for Next Run

```bash
# Stop containers but keep data
docker-compose down
```

### Clean Slate (Delete All Data)

```bash
# Stop and remove volumes
docker-compose down -v

# Reinitialize when restarting
python scripts/init_db.py --drop
```

## Next Steps

Once the pipeline is running:

1. **Explore the Dashboard**: Watch real-time metrics update
2. **Check Fraud Alerts**: See detected anomalies
3. **Query the Database**: Use pgAdmin or SQL client
4. **Run Tests**: `pytest tests/ -v`
5. **Modify Configuration**: Experiment with settings
6. **Add Features**: Build on top of the foundation

## Additional Resources

- [Architecture Documentation](ARCHITECTURE.md) - System design details
- [API Documentation](API.md) - Code reference
- [Performance Guide](PERFORMANCE.md) - Optimization tips
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Kafka Quickstart](https://kafka.apache.org/quickstart)
- [Spark Structured Streaming](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)

## Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review logs: `docker-compose logs [service-name]`
3. Check Python logs in `logs/` directory
4. Verify all prerequisites are met
5. Ensure ports are not in use by other applications

## Development Tips

### Hot Reload for Dashboard

The dashboard auto-reloads when you change code (if `debug=True` in config).

### Testing Changes

```bash
# Run specific tests
pytest tests/unit/test_generator.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html  # Mac
start htmlcov/index.html  # Windows
```

### Viewing Logs

```bash
# Application logs
cat logs/app_*.log

# Docker logs
docker-compose logs -f kafka
docker-compose logs -f postgres

# Spark logs (in terminal output)
```

## Production Considerations

This setup is for **development/demo purposes**. For production:

- [ ] Use managed Kafka (AWS MSK, Confluent Cloud)
- [ ] Deploy to cloud infrastructure
- [ ] Implement proper authentication/authorization
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure log aggregation (ELK stack)
- [ ] Enable encryption at rest and in transit
- [ ] Set up automated backups
- [ ] Implement disaster recovery procedures
- [ ] Use Kubernetes for orchestration
- [ ] Set up CI/CD pipelines

---

**You're all set!** 🚀 The pipeline should now be running and processing transactions in real-time.


# Quick Start Guide

Get the Real-Time E-Commerce Analytics Pipeline running in 10 minutes!

## Prerequisites ✅

- Docker Desktop installed and running
- Python 3.9+ installed
- 8GB RAM available
- 10GB disk space

## Step 1: Start Infrastructure (2 min)

```bash
cd ecommerce-realtime-analytics

# Start Docker services
docker-compose up -d

# Wait ~30 seconds for services to start
# Verify services are running:
docker-compose ps
```

You should see: ✓ zookeeper, ✓ kafka, ✓ postgres, ✓ pgadmin

## Step 2: Setup Python Environment (3 min)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Initialize Database (1 min)

```bash
python scripts/init_db.py
```

Expected output: `Database initialized successfully!`

## Step 4: Start the Pipeline (3 min)

Open **3 separate terminals**, activate venv in each, then:

**Terminal 1 - Data Generator:**
```bash
python src/ingestion/transaction_generator.py
```

**Terminal 2 - Stream Processor:**
```bash
python src/processing/spark_consumer.py
```

**Terminal 3 - Dashboard:**
```bash
python src/visualization/dashboard.py
```

## Step 5: View Dashboard (1 min)

Open browser to: **http://localhost:8050**

You should see:
- 📊 Real-time metrics updating
- 📈 Transaction volume graph
- 🛡️ Fraud detection alerts
- 👥 Customer analytics

## Troubleshooting

### Docker containers won't start
```bash
docker-compose down -v
docker-compose up -d
```

### "Port already in use"
Change ports in `docker-compose.yml` or stop conflicting services

### Python package install fails
```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### Dashboard shows no data
- Wait 20-30 seconds for data to flow through
- Check all 3 terminals are running
- Verify database has data: 
  ```bash
  docker exec -it postgres psql -U dataengineer -d ecommerce -c "SELECT COUNT(*) FROM transactions;"
  ```

## Next Steps

- 📖 Read [SETUP.md](docs/SETUP.md) for detailed setup
- 🏗️ Explore [ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design
- 🚀 Check [PERFORMANCE.md](docs/PERFORMANCE.md) for optimization
- 🧪 Run tests: `pytest tests/ -v`

## Stopping the Pipeline

1. Press Ctrl+C in all 3 terminals
2. Stop Docker: `docker-compose down`
3. To delete data: `docker-compose down -v`

---

**Congratulations!** 🎉 You have a production-grade real-time analytics pipeline running!


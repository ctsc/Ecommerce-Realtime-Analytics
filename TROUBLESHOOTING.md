# Troubleshooting Guide: E-commerce Real-time Analytics

This document chronicles all the issues encountered while building and deploying this project on Windows, along with their solutions. This serves as a reference for others who may face similar challenges.

---

## Table of Contents

1. [Initial Setup Issues](#initial-setup-issues)
2. [Python Environment Problems](#python-environment-problems)
3. [PostgreSQL Connection Issues](#postgresql-connection-issues)
4. [Kafka Configuration Problems](#kafka-configuration-problems)
5. [Apache Spark on Windows Challenges](#apache-spark-on-windows-challenges)
6. [Docker Implementation](#docker-implementation)
7. [Schema Mismatches](#schema-mismatches)
8. [Final Solution: Full Docker Deployment](#final-solution-full-docker-deployment)

---

## 1. Initial Setup Issues

### Issue: Docker Not Installed
**Error:**
```
docker : The term 'docker' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

**Root Cause:** Docker Desktop was not installed on the Windows machine.

**Solution:**
- Installed Docker Desktop for Windows
- Verified installation with `docker --version`
- Ensured Docker daemon was running

---

## 2. Python Environment Problems

### Issue: Missing Python Dependencies
**Error:**
```
ModuleNotFoundError: No module named 'sqlalchemy'
```

**Root Cause:** Python packages were not installed in the active Python environment.

**Solution:**
1. Created a virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activated the virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
3. Installed dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Issue: Module Import Errors
**Error:**
```
ModuleNotFoundError: No module named 'src'
```

**Root Cause:** The `PYTHONPATH` environment variable was not set to include the project root.

**Solution:**
Set `PYTHONPATH` before running Python scripts:
```powershell
$env:PYTHONPATH = $PWD
python src/ingestion/transaction_generator.py
```

---

## 3. PostgreSQL Connection Issues

### Issue: Password Authentication Failed
**Error:**
```
psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed: 
FATAL: password authentication failed for user "dataengineer"
```

**Root Cause:** Two PostgreSQL instances were running:
1. Docker container PostgreSQL (port 5432)
2. Local Windows PostgreSQL installation (port 5432)

The local installation was capturing connections instead of the Docker container.

**Solution:**
Stopped the local PostgreSQL Windows service:
```powershell
# As Administrator
Stop-Service -Name postgresql-x64-18
# Or disable it permanently
Set-Service -Name postgresql-x64-18 -StartupType Disabled
```

**Alternative Solution:**
Use different ports for each PostgreSQL instance in `docker-compose.yml`:
```yaml
postgres:
  ports:
    - "5433:5432"  # Map to different host port
```

---

## 4. Kafka Configuration Problems

### Issue: Kafka Container Repeatedly Stopping
**Error:**
```
ClassNotFoundException: io.confluent.metrics.reporter.ConfluentMetricsReporter
```

**Root Cause:** The `docker-compose.yml` included Confluent Metrics Reporter configuration, but the Confluent Platform image didn't have the required classes.

**Solution:**
Removed the following lines from `docker-compose.yml`:
```yaml
# REMOVED:
KAFKA_METRIC_REPORTERS: io.confluent.metrics.reporter.ConfluentMetricsReporter
KAFKA_CONFLUENT_METRICS_REPORTER_BOOTSTRAP_SERVERS: kafka:29092
KAFKA_CONFLUENT_METRICS_REPORTER_TOPIC_REPLICAS: 1
KAFKA_CONFLUENT_METRICS_ENABLE: 'true'
KAFKA_CONFLUENT_SUPPORT_CUSTOMER_ID: 'anonymous'
```

### Issue: kafka-python Dependency Error
**Error:**
```
ModuleNotFoundError: No module named 'kafka.vendor.six.moves'
```

**Root Cause:** Outdated or corrupted `kafka-python` installation.

**Solution:**
Reinstalled `kafka-python`:
```bash
pip uninstall kafka-python
pip install kafka-python
```

---

## 5. Apache Spark on Windows Challenges

This was the **most significant challenge** in the project. Apache Spark has poor native Windows support.

### Issue 1: HADOOP_HOME Not Set
**Error:**
```
java.io.FileNotFoundException: HADOOP_HOME and hadoop.home.dir are unset. 
-see https://wiki.apache.org/hadoop/WindowsProblems
```

**Root Cause:** Spark requires Hadoop utilities (specifically `winutils.exe`) to run on Windows, even in local mode.

**Attempted Solution 1:**
Set `HADOOP_HOME` environment variable in the Spark consumer code:
```python
import os
import platform

if platform.system() == 'Windows':
    os.environ.setdefault('HADOOP_HOME', 'C:\\hadoop')
```

**Result:** Partial success, but led to the next issue.

---

### Issue 2: Missing winutils.exe
**Error:**
```
java.io.FileNotFoundException: java.io.FileNotFoundException: HADOOP_HOME and hadoop.home.dir are unset.
```

**Root Cause:** The `C:\hadoop\bin\winutils.exe` file didn't exist.

**Attempted Solution 2:**
1. Created `C:\hadoop\bin` directory
2. Downloaded `winutils.exe` from GitHub:
   ```
   https://github.com/steveloughran/winutils/blob/master/hadoop-3.0.0/bin/winutils.exe
   ```
3. Also downloaded `hadoop.dll` for the same version

**Result:** Partial success, but encountered native library errors.

---

### Issue 3: UnsatisfiedLinkError for Native Libraries
**Error:**
```
java.lang.UnsatisfiedLinkError: 'boolean org.apache.hadoop.io.nativeio.NativeIO$Windows.access0(java.lang.String, int)'
```

**Root Cause:** Spark's Hadoop libraries couldn't load the native Windows DLL files properly, or version mismatches between Spark/Hadoop/Java.

**Multiple Attempted Solutions:**
1. ✗ Downloaded different versions of `winutils.exe`
2. ✗ Set additional Java options in Spark config
3. ✗ Created dummy `winutils.exe` (incompatible with Windows version)
4. ✗ Tried different Hadoop versions (2.7.1, 3.0.0, 3.2.0)

**Conclusion:** **Running Spark natively on Windows is extremely problematic and not recommended for production or even development.**

---

## 6. Docker Implementation

### Decision Point
After extensive troubleshooting of Spark on Windows, we decided to containerize the entire application using Docker.

### Benefits of Docker Approach:
1. ✅ **No Windows-specific Hadoop issues** - Spark runs in Linux container
2. ✅ **Consistent environment** - Same setup works on any OS
3. ✅ **Easy deployment** - Single `docker-compose up` command
4. ✅ **Isolation** - No conflicts with local installations
5. ✅ **Reproducibility** - Guaranteed to work the same way everywhere

---

## 7. Schema Mismatches

### Issue 1: fraud_pattern vs fraud_reason
**Error:**
```
Column fraud_pattern not found in schema Some(StructType(...fraud_reason...))
```

**Root Cause:** Inconsistency between:
- Kafka message schema (used `fraud_pattern`)
- Database table schema (used `fraud_reason`)

**Solution:**
Updated `src/processing/spark_consumer.py` to use `fraud_reason`:
```python
StructField("fraud_reason", StringType(), True)  # Changed from fraud_pattern
```

---

### Issue 2: Extra Columns in Spark DataFrame
**Error:**
```
Column hour_of_day not found in schema
Column day_of_week not found in schema
```

**Root Cause:** Spark consumer was adding derived columns (`hour_of_day`, `day_of_week`) that didn't exist in the database schema.

**Solution:**
Removed the derived column logic from `src/processing/spark_consumer.py`:
```python
# REMOVED:
.withColumn("hour_of_day", col("timestamp").cast("timestamp").cast("long") % 86400 / 3600)
.withColumn("day_of_week", col("timestamp").cast("timestamp").cast("long") % 604800 / 86400)
```

---

## 8. Final Solution: Full Docker Deployment

### Architecture
All components now run in Docker containers:

1. **Zookeeper** - Kafka coordination
2. **Kafka** - Message broker
3. **PostgreSQL** - Data storage
4. **pgAdmin** - Database management UI
5. **Transaction Generator** - Python app in container
6. **Spark Consumer** - PySpark app in container with Java 21
7. **Dashboard** - Dash/Flask app in container

### Files Created

#### Dockerfile.generator
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY scripts/ ./scripts/
ENV PYTHONPATH=/app
CMD ["python", "src/ingestion/transaction_generator.py"]
```

#### Dockerfile.spark
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc openjdk-21-jre-headless && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY scripts/ ./scripts/
ENV PYTHONPATH=/app
CMD ["python", "src/processing/spark_consumer.py"]
```

#### Dockerfile.dashboard
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY scripts/ ./scripts/
ENV PYTHONPATH=/app
EXPOSE 8050
CMD ["python", "src/visualization/dashboard.py"]
```

#### .dockerignore
Created to optimize Docker builds by excluding unnecessary files:
```
__pycache__/
*.py[cod]
venv/
.git/
*.md
docs/
logs/
checkpoints/
tests/
```

### Updated docker-compose.yml
Added three new services:
- `generator` - Transaction generation
- `spark-consumer` - Real-time processing
- `dashboard` - Visualization

**Key configurations:**
- Internal Docker network (`ecommerce-network`)
- Service dependencies (wait for PostgreSQL to be healthy)
- Environment variables for service discovery
- Proper restart policies

---

## Lessons Learned

### 1. **Avoid Running Spark Natively on Windows**
- Windows lacks proper Hadoop native library support
- `winutils.exe` is a hack, not a real solution
- Version mismatches are extremely common
- Docker or WSL2 are the only viable options

### 2. **Docker First Approach**
- For distributed systems projects, start with Docker
- Don't try to run complex JVM-based tools (Spark, Kafka) natively on Windows
- Docker provides consistency and eliminates OS-specific issues

### 3. **Schema Consistency is Critical**
- Keep database schemas, Spark schemas, and message schemas in sync
- Use a schema registry (like Confluent Schema Registry) for production
- Document expected schemas clearly

### 4. **Environment Variables Matter**
- Use environment variables for all configuration
- Docker makes this much easier with `docker-compose.yml`
- Never hardcode hosts, ports, or credentials

### 5. **Port Conflicts**
- Check for existing services on common ports (5432, 9092, etc.)
- Use `netstat` or `Get-NetTCPConnection` to identify conflicts
- Stop conflicting services or use different ports

---

## Quick Reference: Common Commands

### Docker
```bash
# Start all services
docker-compose up -d

# View logs
docker logs transaction-generator
docker logs spark-consumer
docker logs dashboard

# Check status
docker-compose ps

# Stop all services
docker-compose down

# Rebuild specific service
docker-compose up --build -d spark-consumer

# Access PostgreSQL
docker exec -it postgres psql -U dataengineer -d ecommerce
```

### Database Queries
```sql
-- Check transaction count
SELECT COUNT(*) FROM transactions;

-- Check fraud detections
SELECT COUNT(*) FROM transactions WHERE is_fraud = true;

-- View recent transactions
SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 10;

-- Check database schema
\d transactions
```

### Troubleshooting
```bash
# Check if ports are in use (PowerShell)
Get-NetTCPConnection -LocalPort 5432,9092,8050

# Stop Windows PostgreSQL service
Stop-Service -Name postgresql-x64-18

# Verify Docker is running
docker info

# Check Docker network
docker network ls
docker network inspect ecommerce-realtime-analytics_ecommerce-network
```

---

## System Requirements (Docker Approach)

### Minimum Requirements:
- **OS:** Windows 10/11 Pro, Enterprise, or Education (for Docker Desktop)
- **RAM:** 8 GB (16 GB recommended)
- **Disk:** 10 GB free space
- **Docker Desktop:** Latest version with WSL2 backend

### No Longer Required:
- ✗ Local Java installation
- ✗ Local Spark installation
- ✗ Hadoop/winutils.exe
- ✗ Local Kafka installation
- ✗ Local PostgreSQL installation

---

## Performance Notes

### Observed Performance:
- **Transaction Generation:** ~85-95 transactions/second
- **Spark Processing:** Real-time with 5-second micro-batches
- **Data Storage:** 20,000+ transactions processed successfully
- **Fraud Detection:** ~2% fraud rate as configured
- **Dashboard Refresh:** 5-second interval

### Resource Usage:
- Docker containers: ~4-6 GB RAM total
- CPU: Moderate usage (20-40% on modern CPUs)
- Disk I/O: Minimal after initial data load

---

## Future Improvements

1. **Use Confluent Schema Registry** for schema management
2. **Implement Kubernetes** for production deployment
3. **Add monitoring** with Prometheus and Grafana
4. **Implement CI/CD** pipeline
5. **Add data validation** layers
6. **Implement backup** and recovery procedures
7. **Add authentication** to services
8. **Implement SSL/TLS** for secure communication

---

## Conclusion

The journey from attempting to run Spark natively on Windows to a fully Dockerized solution taught us that:

**Sometimes the "hard way" teaches you why the "easy way" exists.**

Docker isn't just convenient—it's essential for modern distributed systems development, especially on Windows. The time invested in troubleshooting Windows-specific issues could have been saved by starting with Docker from day one.

For anyone building similar projects: **Start with Docker. Your future self will thank you.**

---

*Document created: October 14, 2025*  
*Last updated: October 14, 2025*  
*Status: Production-ready with Docker*


"""
PySpark streaming consumer for processing transactions in real-time.
Reads from Kafka, processes data, detects fraud, and stores results.
"""

import json
import os
import platform
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, window, count, sum as spark_sum, 
    avg, max as spark_max, current_timestamp, lit
)
from pyspark.sql.types import (
    StructType, StructField, StringType, 
    DoubleType, IntegerType, BooleanType, TimestampType
)

from src.utils.config import config
from src.utils.logging_config import get_logger


logger = get_logger(__name__)


class SparkTransactionConsumer:
    """
    Spark Structured Streaming consumer for transaction processing.
    Reads from Kafka, applies transformations, and writes to PostgreSQL.
    """
    
    def __init__(self):
        """Initialize Spark session and consumer."""
        self.spark = self._create_spark_session()
        self.schema = self._get_transaction_schema()
        
        logger.info("Spark consumer initialized")
    
    def _create_spark_session(self) -> SparkSession:
        """
        Create and configure Spark session.
        
        Returns:
            Configured SparkSession
        """
        # Windows-specific: Set HADOOP_HOME to avoid winutils error
        if platform.system() == 'Windows':
            os.environ.setdefault('HADOOP_HOME', 'C:\\hadoop')
            
        spark = (
            SparkSession.builder
            .appName(config.spark.app_name)
            .master(config.spark.master)
            .config("spark.sql.shuffle.partitions", config.spark.shuffle_partitions)
            .config("spark.streaming.stopGracefullyOnShutdown", "true")
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.driver.extraJavaOptions", "-Djava.security.manager=allow")
            .config("spark.executor.extraJavaOptions", "-Djava.security.manager=allow")
            .config("spark.hadoop.hadoop.home.dir", os.environ.get('HADOOP_HOME', '/tmp'))
            .config("spark.jars.packages", 
                    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
                    "org.postgresql:postgresql:42.6.0")
            .getOrCreate()
        )
        
        spark.sparkContext.setLogLevel(config.spark.log_level)
        
        return spark
    
    def _get_transaction_schema(self) -> StructType:
        """
        Define schema for incoming transaction data.
        
        Returns:
            StructType schema definition
        """
        return StructType([
            StructField("transaction_id", StringType(), False),
            StructField("timestamp", StringType(), False),
            StructField("customer_id", StringType(), False),
            StructField("customer_email", StringType(), True),
            StructField("customer_location", StringType(), True),
            StructField("product_id", StringType(), False),
            StructField("product_name", StringType(), False),
            StructField("category", StringType(), False),
            StructField("quantity", IntegerType(), False),
            StructField("unit_price", DoubleType(), False),
            StructField("total_amount", DoubleType(), False),
            StructField("is_fraud", BooleanType(), True),
            StructField("fraud_reason", StringType(), True)
        ])
    
    def read_from_kafka(self):
        """
        Read streaming data from Kafka.
        
        Returns:
            Streaming DataFrame
        """
        logger.info(f"Reading from Kafka topic: {config.kafka.topic_transactions}")
        
        df = (
            self.spark
            .readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", config.kafka.bootstrap_servers)
            .option("subscribe", config.kafka.topic_transactions)
            .option("startingOffsets", "latest")
            .option("failOnDataLoss", "false")
            .load()
        )
        
        # Parse JSON data
        transactions_df = (
            df
            .selectExpr("CAST(value AS STRING) as json")
            .select(from_json(col("json"), self.schema).alias("data"))
            .select("data.*")
        )
        
        return transactions_df
    
    def process_transactions(self, transactions_df):
        """
        Apply transformations to transaction data.
        
        Args:
            transactions_df: Input streaming DataFrame
            
        Returns:
            Processed DataFrame
        """
        # Convert timestamp string to timestamp type
        processed_df = (
            transactions_df
            .withColumn("timestamp", col("timestamp").cast(TimestampType()))
            .withColumn("processing_timestamp", current_timestamp())
        )
        
        return processed_df
    
    def write_to_postgres(self, df, checkpoint_location: str, table_name: str):
        """
        Write streaming data to PostgreSQL.
        
        Args:
            df: Streaming DataFrame to write
            checkpoint_location: Location for streaming checkpoints
            table_name: Target table name
        """
        jdbc_url = (
            f"jdbc:postgresql://{config.database.host}:{config.database.port}/"
            f"{config.database.database}"
        )
        
        connection_properties = {
            "user": config.database.user,
            "password": config.database.password,
            "driver": "org.postgresql.Driver"
        }
        
        query = (
            df.writeStream
            .outputMode("append")
            .foreachBatch(
                lambda batch_df, batch_id: self._write_batch_to_postgres(
                    batch_df, batch_id, jdbc_url, table_name, connection_properties
                )
            )
            .option("checkpointLocation", checkpoint_location)
            .start()
        )
        
        return query
    
    def _write_batch_to_postgres(
        self, 
        batch_df, 
        batch_id: int,
        jdbc_url: str,
        table_name: str,
        properties: dict
    ):
        """
        Write a microbatch to PostgreSQL.
        
        Args:
            batch_df: Batch DataFrame
            batch_id: Batch identifier
            jdbc_url: JDBC connection URL
            table_name: Target table
            properties: Connection properties
        """
        if batch_df.count() > 0:
            try:
                batch_df.write.jdbc(
                    url=jdbc_url,
                    table=table_name,
                    mode="append",
                    properties=properties
                )
                logger.info(f"Batch {batch_id}: Wrote {batch_df.count()} records to {table_name}")
            except Exception as e:
                logger.error(f"Error writing batch {batch_id} to PostgreSQL: {e}")
    
    def write_to_console(self, df, checkpoint_location: str):
        """
        Write streaming data to console (for debugging).
        
        Args:
            df: Streaming DataFrame
            checkpoint_location: Checkpoint location
        """
        query = (
            df.writeStream
            .outputMode("append")
            .format("console")
            .option("truncate", "false")
            .option("checkpointLocation", checkpoint_location)
            .start()
        )
        
        return query
    
    def calculate_aggregations(self, transactions_df):
        """
        Calculate real-time aggregations over time windows.
        
        Args:
            transactions_df: Input DataFrame
            
        Returns:
            Aggregated DataFrame
        """
        # 5-minute window aggregations
        agg_df = (
            transactions_df
            .groupBy(
                window(col("timestamp"), "5 minutes", "1 minute"),
                col("category")
            )
            .agg(
                count("transaction_id").alias("transaction_count"),
                spark_sum("total_amount").alias("total_revenue"),
                avg("total_amount").alias("avg_transaction_amount"),
                spark_max("total_amount").alias("max_transaction_amount")
            )
        )
        
        return agg_df
    
    def filter_fraud_transactions(self, transactions_df):
        """
        Filter only fraudulent transactions.
        
        Args:
            transactions_df: Input DataFrame
            
        Returns:
            DataFrame with only fraud transactions
        """
        fraud_df = transactions_df.filter(col("is_fraud") == True)
        return fraud_df
    
    def run(self):
        """
        Main execution method to start the streaming pipeline.
        """
        logger.info("Starting Spark streaming consumer...")
        
        # Read from Kafka
        transactions_df = self.read_from_kafka()
        
        # Process transactions
        processed_df = self.process_transactions(transactions_df)
        
        # Write to PostgreSQL
        checkpoint_base = config.spark.checkpoint_location
        
        # Main transaction stream
        query_main = self.write_to_postgres(
            processed_df,
            f"{checkpoint_base}/transactions",
            "transactions"
        )
        
        # Fraud alerts stream
        fraud_df = self.filter_fraud_transactions(processed_df)
        query_fraud = self.write_to_console(
            fraud_df,
            f"{checkpoint_base}/fraud"
        )
        
        logger.info("Streaming queries started successfully")
        
        # Wait for termination
        try:
            query_main.awaitTermination()
        except KeyboardInterrupt:
            logger.info("Stopping streaming consumer...")
            self.spark.stop()


def main():
    """Main entry point for Spark consumer."""
    consumer = SparkTransactionConsumer()
    consumer.run()


if __name__ == "__main__":
    main()



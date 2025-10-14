"""
Performance benchmarking script for the analytics pipeline.
Tests throughput, latency, and resource utilization.
"""

import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import statistics

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.transaction_generator import TransactionGenerator
from src.ingestion.kafka_producer import KafkaTransactionProducer
from src.utils.logging_config import get_logger


logger = get_logger(__name__)


class PerformanceBenchmark:
    """
    Benchmark the performance of the transaction pipeline.
    Measures throughput, latency, and success rate.
    """
    
    def __init__(self):
        """Initialize benchmark."""
        self.generator = TransactionGenerator()
        self.producer = KafkaTransactionProducer()
        self.results = {
            'latencies': [],
            'timestamps': [],
            'errors': 0,
            'success': 0
        }
    
    def benchmark_throughput(
        self, 
        duration_seconds: int = 60,
        target_rate: int = 100
    ) -> Dict:
        """
        Benchmark transaction throughput.
        
        Args:
            duration_seconds: How long to run the test
            target_rate: Target transactions per second
            
        Returns:
            Dictionary with benchmark results
        """
        logger.info(f"Starting throughput benchmark: {target_rate} tx/sec for {duration_seconds}s")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        batch_size = 10
        sleep_time = batch_size / target_rate
        
        total_transactions = 0
        
        try:
            while time.time() < end_time:
                batch_start = time.time()
                
                # Generate and send batch
                batch = self.generator.generate_batch(batch_size)
                
                for tx in batch:
                    tx_start = time.time()
                    success = self.producer.send_transaction(tx)
                    tx_latency = time.time() - tx_start
                    
                    self.results['latencies'].append(tx_latency)
                    self.results['timestamps'].append(time.time())
                    
                    if success:
                        self.results['success'] += 1
                    else:
                        self.results['errors'] += 1
                    
                    total_transactions += 1
                
                # Flush to ensure delivery
                self.producer.flush()
                
                # Sleep to maintain target rate
                elapsed = time.time() - batch_start
                if elapsed < sleep_time:
                    time.sleep(sleep_time - elapsed)
        
        except KeyboardInterrupt:
            logger.info("Benchmark interrupted by user")
        
        actual_duration = time.time() - start_time
        
        return self._calculate_results(total_transactions, actual_duration)
    
    def benchmark_latency(self, num_transactions: int = 1000) -> Dict:
        """
        Benchmark transaction latency.
        
        Args:
            num_transactions: Number of transactions to test
            
        Returns:
            Dictionary with latency statistics
        """
        logger.info(f"Starting latency benchmark: {num_transactions} transactions")
        
        latencies = []
        
        for i in range(num_transactions):
            tx = self.generator.generate_transaction()
            
            start = time.time()
            self.producer.send_transaction(tx)
            self.producer.flush()
            latency = time.time() - start
            
            latencies.append(latency)
            
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1} transactions")
        
        return {
            'total_transactions': num_transactions,
            'min_latency_ms': min(latencies) * 1000,
            'max_latency_ms': max(latencies) * 1000,
            'mean_latency_ms': statistics.mean(latencies) * 1000,
            'median_latency_ms': statistics.median(latencies) * 1000,
            'p95_latency_ms': self._percentile(latencies, 95) * 1000,
            'p99_latency_ms': self._percentile(latencies, 99) * 1000
        }
    
    def benchmark_sustained_load(
        self,
        duration_minutes: int = 5,
        rate: int = 100
    ) -> Dict:
        """
        Run sustained load test to check stability.
        
        Args:
            duration_minutes: Test duration in minutes
            rate: Transactions per second
            
        Returns:
            Benchmark results with stability metrics
        """
        logger.info(f"Starting sustained load test: {rate} tx/sec for {duration_minutes} min")
        
        results = self.benchmark_throughput(
            duration_seconds=duration_minutes * 60,
            target_rate=rate
        )
        
        # Calculate stability metrics
        if len(self.results['latencies']) > 100:
            # Split into time windows
            window_size = len(self.results['latencies']) // 10
            window_means = []
            
            for i in range(0, len(self.results['latencies']) - window_size, window_size):
                window = self.results['latencies'][i:i+window_size]
                window_means.append(statistics.mean(window))
            
            # Coefficient of variation (lower is more stable)
            if statistics.mean(window_means) > 0:
                stability = statistics.stdev(window_means) / statistics.mean(window_means)
            else:
                stability = 0
            
            results['stability_coefficient'] = round(stability, 4)
            results['stable'] = stability < 0.2  # < 20% variation
        
        return results
    
    def _calculate_results(self, total_transactions: int, duration: float) -> Dict:
        """Calculate benchmark results."""
        if not self.results['latencies']:
            return {'error': 'No data collected'}
        
        actual_rate = total_transactions / duration if duration > 0 else 0
        
        results = {
            'duration_seconds': round(duration, 2),
            'total_transactions': total_transactions,
            'successful_transactions': self.results['success'],
            'failed_transactions': self.results['errors'],
            'success_rate': round(self.results['success'] / total_transactions * 100, 2) if total_transactions > 0 else 0,
            'throughput_tx_per_sec': round(actual_rate, 2),
            'throughput_tx_per_min': round(actual_rate * 60, 2),
            'latency_stats': {
                'min_ms': round(min(self.results['latencies']) * 1000, 2),
                'max_ms': round(max(self.results['latencies']) * 1000, 2),
                'mean_ms': round(statistics.mean(self.results['latencies']) * 1000, 2),
                'median_ms': round(statistics.median(self.results['latencies']) * 1000, 2),
                'p95_ms': round(self._percentile(self.results['latencies'], 95) * 1000, 2),
                'p99_ms': round(self._percentile(self.results['latencies'], 99) * 1000, 2)
            }
        }
        
        return results
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def print_results(self, results: Dict):
        """Pretty print results."""
        print("\n" + "="*60)
        print("BENCHMARK RESULTS")
        print("="*60)
        
        if 'error' in results:
            print(f"Error: {results['error']}")
            return
        
        print(f"\nDuration: {results['duration_seconds']}s")
        print(f"Total Transactions: {results['total_transactions']:,}")
        print(f"Successful: {results['successful_transactions']:,}")
        print(f"Failed: {results['failed_transactions']:,}")
        print(f"Success Rate: {results['success_rate']}%")
        
        print(f"\n📊 THROUGHPUT")
        print(f"  {results['throughput_tx_per_sec']:.2f} tx/sec")
        print(f"  {results['throughput_tx_per_min']:.2f} tx/min")
        
        if 'latency_stats' in results:
            stats = results['latency_stats']
            print(f"\n⏱️  LATENCY")
            print(f"  Min:    {stats['min_ms']:.2f}ms")
            print(f"  Mean:   {stats['mean_ms']:.2f}ms")
            print(f"  Median: {stats['median_ms']:.2f}ms")
            print(f"  p95:    {stats['p95_ms']:.2f}ms")
            print(f"  p99:    {stats['p99_ms']:.2f}ms")
            print(f"  Max:    {stats['max_ms']:.2f}ms")
        
        if 'stability_coefficient' in results:
            print(f"\n📈 STABILITY")
            print(f"  Coefficient: {results['stability_coefficient']}")
            print(f"  Status: {'✓ Stable' if results['stable'] else '✗ Unstable'}")
        
        print("\n" + "="*60 + "\n")
    
    def cleanup(self):
        """Cleanup resources."""
        self.producer.close()
        logger.info("Benchmark cleanup complete")


def main():
    """Main benchmark execution."""
    parser = argparse.ArgumentParser(description='Benchmark the analytics pipeline')
    parser.add_argument(
        '--mode',
        choices=['throughput', 'latency', 'sustained'],
        default='throughput',
        help='Benchmark mode'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Duration in seconds (for throughput/sustained)'
    )
    parser.add_argument(
        '--rate',
        type=int,
        default=100,
        help='Target rate in transactions per second'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=1000,
        help='Number of transactions (for latency mode)'
    )
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark()
    
    try:
        if args.mode == 'throughput':
            results = benchmark.benchmark_throughput(
                duration_seconds=args.duration,
                target_rate=args.rate
            )
        elif args.mode == 'latency':
            results = benchmark.benchmark_latency(num_transactions=args.count)
        elif args.mode == 'sustained':
            results = benchmark.benchmark_sustained_load(
                duration_minutes=args.duration // 60,
                rate=args.rate
            )
        
        benchmark.print_results(results)
        
        # Save results to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"benchmark_results_{args.mode}_{timestamp}.txt"
        
        with open(results_file, 'w') as f:
            f.write(f"Benchmark Results - {args.mode.upper()}\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(f"\nResults:\n{results}\n")
        
        logger.info(f"Results saved to {results_file}")
        
    except KeyboardInterrupt:
        logger.info("Benchmark interrupted")
    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    main()


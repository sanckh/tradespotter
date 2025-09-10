"""Main application entry point for PTR ingestion worker."""

import asyncio
import signal
import sys
from typing import Optional
from pathlib import Path
import argparse
import structlog

from .config.settings import Settings
from .scheduler.task_scheduler import PTRIngestionScheduler
from .pipeline.ingestion_pipeline import IngestionPipeline
from .utils.logging_config import setup_logging, get_logger, metrics

logger = get_logger("main")


class PTRIngestionWorker:
    """Main PTR ingestion worker application."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.scheduler: Optional[PTRIngestionScheduler] = None
        self.pipeline: Optional[IngestionPipeline] = None
        self.shutdown_event = asyncio.Event()
        
    async def run_scheduled_mode(self):
        """Run in scheduled mode with continuous operation."""
        logger.info("Starting PTR ingestion worker in scheduled mode")
        
        try:
            # Setup scheduler
            self.scheduler = PTRIngestionScheduler(self.settings)
            await self.scheduler.start()
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            logger.info("PTR ingestion worker is running. Press Ctrl+C to stop.")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error("Scheduled mode failed", error=str(e))
            raise
        finally:
            await self._cleanup()
    
    async def run_once_mode(self, limit: Optional[int] = None):
        """Run pipeline once and exit."""
        logger.info("Starting PTR ingestion worker in once mode", limit=limit)
        
        try:
            self.pipeline = IngestionPipeline(self.settings)
            
            # Run full pipeline
            results = await self.pipeline.run_full_pipeline(limit=limit)
            
            logger.info("Once mode completed successfully", **results)
            
            # Print summary
            self._print_summary(results)
            
            return results
            
        except Exception as e:
            logger.error("Once mode failed", error=str(e))
            raise
    
    async def run_health_check_mode(self):
        """Run health check and exit."""
        logger.info("Starting PTR ingestion worker in health check mode")
        
        try:
            self.pipeline = IngestionPipeline(self.settings)
            
            # Run health check
            health_status = await self.pipeline.health_check()
            
            logger.info("Health check completed", status=health_status['overall_status'])
            
            # Print health status
            self._print_health_status(health_status)
            
            # Exit with appropriate code
            if health_status['overall_status'] == 'healthy':
                return 0
            else:
                return 1
                
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return 2
    
    async def run_discovery_mode(self, limit: Optional[int] = None):
        """Run discovery only and exit."""
        logger.info("Starting PTR ingestion worker in discovery mode", limit=limit)
        
        try:
            self.pipeline = IngestionPipeline(self.settings)
            
            # Run discovery only
            filings = await self.pipeline.run_discovery_only(limit=limit)
            
            logger.info("Discovery mode completed", filings_found=len(filings))
            
            # Print discovery results
            self._print_discovery_results(filings)
            
            return filings
            
        except Exception as e:
            logger.error("Discovery mode failed", error=str(e))
            raise
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal", signal=signum)
            asyncio.create_task(self._initiate_shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _initiate_shutdown(self):
        """Initiate graceful shutdown."""
        logger.info("Initiating graceful shutdown")
        self.shutdown_event.set()
    
    async def _cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up resources")
        
        if self.scheduler:
            try:
                await self.scheduler.stop()
            except Exception as e:
                logger.warning("Error stopping scheduler", error=str(e))
        
        logger.info("Cleanup completed")
    
    def _print_summary(self, results: dict):
        """Print pipeline execution summary."""
        print("\n" + "="*60)
        print("PTR INGESTION PIPELINE SUMMARY")
        print("="*60)
        print(f"Status: {results.get('pipeline_status', 'unknown')}")
        print(f"Duration: {results.get('duration_seconds', 0):.2f} seconds")
        print(f"Filings Discovered: {results.get('filings_discovered', 0)}")
        print(f"PDFs Downloaded: {results.get('pdfs_downloaded', 0)}")
        print(f"Trades Parsed: {results.get('trades_parsed', 0)}")
        print(f"Trades Normalized: {results.get('trades_normalized', 0)}")
        print(f"Trades Upserted: {results.get('trades_upserted', 0)}")
        print(f"Total Errors: {results.get('total_errors', 0)}")
        print("="*60)
    
    def _print_health_status(self, health_status: dict):
        """Print health check status."""
        print("\n" + "="*60)
        print("PTR INGESTION WORKER HEALTH STATUS")
        print("="*60)
        print(f"Overall Status: {health_status.get('overall_status', 'unknown').upper()}")
        print(f"Timestamp: {health_status.get('timestamp', 'unknown')}")
        print("\nComponent Status:")
        
        for component, status in health_status.get('components', {}).items():
            status_indicator = "✓" if status.get('status') == 'healthy' else "✗"
            print(f"  {status_indicator} {component}: {status.get('status', 'unknown')}")
            
            if status.get('error'):
                print(f"    Error: {status['error']}")
            elif status.get('test_result'):
                print(f"    Result: {status['test_result']}")
        
        print("="*60)
    
    def _print_discovery_results(self, filings: list):
        """Print discovery results."""
        print("\n" + "="*60)
        print("PTR FILING DISCOVERY RESULTS")
        print("="*60)
        print(f"Total Filings Found: {len(filings)}")
        
        if filings:
            print("\nRecent Filings:")
            for i, filing in enumerate(filings[:10]):  # Show first 10
                print(f"  {i+1}. {filing.get('member_name', 'Unknown')} - {filing.get('filing_date', 'Unknown date')}")
                print(f"     Filing ID: {filing.get('filing_id', 'Unknown')}")
                print(f"     URL: {filing.get('doc_url', 'Unknown')}")
                print()
            
            if len(filings) > 10:
                print(f"  ... and {len(filings) - 10} more filings")
        
        print("="*60)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="PTR Ingestion Worker")
    parser.add_argument(
        "--mode",
        choices=["scheduled", "once", "health", "discovery"],
        default="scheduled",
        help="Execution mode"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of filings to process (for once/discovery modes)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    parser.add_argument(
        "--json-logs",
        action="store_true",
        default=True,
        help="Use JSON logging format"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level=args.log_level, json_logs=args.json_logs)
    
    try:
        # Load settings
        settings = Settings()
        
        # Create worker
        worker = PTRIngestionWorker(settings)
        
        # Run in specified mode
        if args.mode == "scheduled":
            await worker.run_scheduled_mode()
        elif args.mode == "once":
            await worker.run_once_mode(limit=args.limit)
        elif args.mode == "health":
            exit_code = await worker.run_health_check_mode()
            sys.exit(exit_code)
        elif args.mode == "discovery":
            await worker.run_discovery_mode(limit=args.limit)
        
        logger.info("PTR ingestion worker completed successfully")
        
    except KeyboardInterrupt:
        logger.info("PTR ingestion worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("PTR ingestion worker failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

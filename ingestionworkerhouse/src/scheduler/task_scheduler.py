"""Task scheduler with cron-like functionality and error handling."""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from enum import Enum
import structlog

from ..config.settings import Settings
from ..pipeline.ingestion_pipeline import IngestionPipeline
from ..utils.logging_config import performance_timer, metrics, get_logger
from ..utils.retry_utils import retry_with_backoff

logger = get_logger("task_scheduler")


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledTask:
    """Represents a scheduled task with execution metadata."""
    
    def __init__(
        self,
        name: str,
        func: Callable,
        interval_minutes: int,
        max_retries: int = 3,
        retry_backoff: float = 2.0
    ):
        self.name = name
        self.func = func
        self.interval_minutes = interval_minutes
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        
        self.status = TaskStatus.PENDING
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.current_retry = 0
        
        self._calculate_next_run()
    
    def _calculate_next_run(self):
        """Calculate the next run time."""
        if self.last_run:
            self.next_run = self.last_run + timedelta(minutes=self.interval_minutes)
        else:
            self.next_run = datetime.utcnow() + timedelta(minutes=self.interval_minutes)
    
    def should_run(self) -> bool:
        """Check if the task should run now."""
        if self.status == TaskStatus.RUNNING:
            return False
        
        return datetime.utcnow() >= self.next_run
    
    def mark_started(self):
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.last_run = datetime.utcnow()
        self.run_count += 1
    
    def mark_completed(self):
        """Mark task as completed successfully."""
        self.status = TaskStatus.COMPLETED
        self.success_count += 1
        self.current_retry = 0
        self.last_error = None
        self._calculate_next_run()
    
    def mark_failed(self, error: str):
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.error_count += 1
        self.last_error = error
        self.current_retry += 1
        
        # Calculate next retry time with exponential backoff
        if self.current_retry <= self.max_retries:
            backoff_minutes = self.retry_backoff ** self.current_retry
            self.next_run = datetime.utcnow() + timedelta(minutes=backoff_minutes)
            self.status = TaskStatus.PENDING  # Allow retry
        else:
            # Max retries exceeded, wait for next regular interval
            self.current_retry = 0
            self._calculate_next_run()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get task statistics."""
        return {
            'name': self.name,
            'status': self.status.value,
            'interval_minutes': self.interval_minutes,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'run_count': self.run_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': self.success_count / self.run_count if self.run_count > 0 else 0,
            'last_error': self.last_error,
            'current_retry': self.current_retry
        }


class TaskScheduler:
    """Cron-like task scheduler with error handling and monitoring."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
    def add_task(
        self,
        name: str,
        func: Callable,
        interval_minutes: int,
        max_retries: int = 3,
        retry_backoff: float = 2.0
    ):
        """Add a scheduled task."""
        task = ScheduledTask(name, func, interval_minutes, max_retries, retry_backoff)
        self.tasks[name] = task
        
        logger.info(
            "Task added to scheduler",
            task_name=name,
            interval_minutes=interval_minutes,
            max_retries=max_retries
        )
    
    def remove_task(self, name: str) -> bool:
        """Remove a scheduled task."""
        if name in self.tasks:
            del self.tasks[name]
            logger.info("Task removed from scheduler", task_name=name)
            return True
        return False
    
    async def start(self):
        """Start the task scheduler."""
        if self.running:
            logger.warning("Task scheduler is already running")
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        logger.info("Task scheduler started", tasks_count=len(self.tasks))
    
    async def stop(self):
        """Stop the task scheduler."""
        if not self.running:
            return
        
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Task scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        try:
            while self.running:
                try:
                    await self._check_and_run_tasks()
                    await asyncio.sleep(60)  # Check every minute
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Scheduler loop error", error=str(e))
                    metrics.increment("scheduler.loop_errors")
                    await asyncio.sleep(60)  # Continue after error
        
        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        
        logger.info("Scheduler loop ended")
    
    async def _check_and_run_tasks(self):
        """Check and run tasks that are due."""
        for task_name, task in self.tasks.items():
            if task.should_run():
                # Run task in background
                asyncio.create_task(self._run_task(task))
    
    async def _run_task(self, task: ScheduledTask):
        """Run a single task with error handling."""
        logger.info("Starting scheduled task", task_name=task.name)
        
        task.mark_started()
        
        with performance_timer("scheduler.task_execution", {"task": task.name}):
            try:
                # Execute the task function
                if asyncio.iscoroutinefunction(task.func):
                    await task.func()
                else:
                    task.func()
                
                task.mark_completed()
                
                logger.info(
                    "Scheduled task completed successfully",
                    task_name=task.name,
                    run_count=task.run_count,
                    success_count=task.success_count
                )
                
                metrics.increment("scheduler.task_success", tags={"task": task.name})
                
            except Exception as e:
                error_msg = str(e)
                task.mark_failed(error_msg)
                
                logger.error(
                    "Scheduled task failed",
                    task_name=task.name,
                    error=error_msg,
                    retry_count=task.current_retry,
                    max_retries=task.max_retries
                )
                
                metrics.increment("scheduler.task_errors", tags={"task": task.name})
    
    def get_task_status(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        task = self.tasks.get(task_name)
        return task.get_stats() if task else None
    
    def get_all_task_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tasks."""
        return {name: task.get_stats() for name, task in self.tasks.items()}
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get overall scheduler statistics."""
        total_runs = sum(task.run_count for task in self.tasks.values())
        total_successes = sum(task.success_count for task in self.tasks.values())
        total_errors = sum(task.error_count for task in self.tasks.values())
        
        return {
            'running': self.running,
            'tasks_count': len(self.tasks),
            'total_runs': total_runs,
            'total_successes': total_successes,
            'total_errors': total_errors,
            'overall_success_rate': total_successes / total_runs if total_runs > 0 else 0,
            'tasks': self.get_all_task_status()
        }
    
    async def run_task_now(self, task_name: str) -> bool:
        """Run a specific task immediately."""
        task = self.tasks.get(task_name)
        if not task:
            logger.warning("Task not found for immediate execution", task_name=task_name)
            return False
        
        if task.status == TaskStatus.RUNNING:
            logger.warning("Task is already running", task_name=task_name)
            return False
        
        logger.info("Running task immediately", task_name=task_name)
        await self._run_task(task)
        return True


class PTRIngestionScheduler:
    """Specialized scheduler for PTR ingestion tasks."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.scheduler = TaskScheduler(settings)
        self.pipeline = IngestionPipeline(settings)
        
    async def setup_ingestion_tasks(self):
        """Setup standard PTR ingestion tasks."""
        
        # Main ingestion task
        self.scheduler.add_task(
            name="ptr_full_ingestion",
            func=self._run_full_ingestion,
            interval_minutes=self.settings.scan_interval_min,
            max_retries=3,
            retry_backoff=2.0
        )
        
        # Discovery-only task (more frequent)
        self.scheduler.add_task(
            name="ptr_discovery",
            func=self._run_discovery_only,
            interval_minutes=max(30, self.settings.scan_interval_min // 2),
            max_retries=2,
            retry_backoff=1.5
        )
        
        # Health check task
        self.scheduler.add_task(
            name="health_check",
            func=self._run_health_check,
            interval_minutes=15,  # Every 15 minutes
            max_retries=1,
            retry_backoff=1.0
        )
        
        # Data integrity check (daily)
        self.scheduler.add_task(
            name="data_integrity_check",
            func=self._run_data_integrity_check,
            interval_minutes=1440,  # 24 hours
            max_retries=2,
            retry_backoff=2.0
        )
        
        logger.info("PTR ingestion tasks configured")
    
    async def _run_full_ingestion(self):
        """Run full PTR ingestion pipeline."""
        logger.info("Starting scheduled full ingestion")
        
        try:
            results = await self.pipeline.run_full_pipeline()
            
            logger.info(
                "Scheduled full ingestion completed",
                **{k: v for k, v in results.items() if k not in ['start_time', 'end_time']}
            )
            
            # Log metrics
            metrics.gauge("ingestion.filings_processed", results.get('filings_discovered', 0))
            metrics.gauge("ingestion.trades_upserted", results.get('trades_upserted', 0))
            
            if results.get('total_errors', 0) > 0:
                logger.warning("Full ingestion completed with errors", errors=results['total_errors'])
            
        except Exception as e:
            logger.error("Scheduled full ingestion failed", error=str(e))
            raise
    
    async def _run_discovery_only(self):
        """Run discovery-only task."""
        logger.info("Starting scheduled discovery")
        
        try:
            filings = await self.pipeline.run_discovery_only()
            
            logger.info("Scheduled discovery completed", filings_found=len(filings))
            metrics.gauge("discovery.scheduled_filings_found", len(filings))
            
        except Exception as e:
            logger.error("Scheduled discovery failed", error=str(e))
            raise
    
    async def _run_health_check(self):
        """Run health check task."""
        logger.debug("Starting scheduled health check")
        
        try:
            health_status = await self.pipeline.health_check()
            
            logger.debug("Scheduled health check completed", status=health_status['overall_status'])
            
            # Update health metrics
            is_healthy = health_status['overall_status'] == 'healthy'
            metrics.gauge("health.overall_status", 1 if is_healthy else 0)
            
            for component, status in health_status.get('components', {}).items():
                is_component_healthy = status.get('status') == 'healthy'
                metrics.gauge(f"health.component.{component}", 1 if is_component_healthy else 0)
            
            if not is_healthy:
                logger.warning("Health check detected issues", status=health_status)
            
        except Exception as e:
            logger.error("Scheduled health check failed", error=str(e))
            metrics.gauge("health.overall_status", 0)
            raise
    
    async def _run_data_integrity_check(self):
        """Run data integrity check task."""
        logger.info("Starting scheduled data integrity check")
        
        try:
            from ..upserter.data_upserter import DataUpserter
            
            async with DataUpserter(self.settings) as upserter:
                integrity_results = await upserter.validate_data_integrity()
                
                logger.info("Scheduled data integrity check completed", **integrity_results)
                
                # Log integrity metrics
                metrics.gauge("integrity.total_members", integrity_results.get('total_members', 0))
                metrics.gauge("integrity.total_trades", integrity_results.get('total_trades', 0))
                metrics.gauge("integrity.orphaned_trades", integrity_results.get('orphaned_trades', 0))
                metrics.gauge("integrity.duplicate_hashes", integrity_results.get('duplicate_hashes', 0))
                
                # Alert on integrity issues
                issues = integrity_results.get('orphaned_trades', 0) + integrity_results.get('duplicate_hashes', 0)
                if issues > 0:
                    logger.warning("Data integrity issues detected", issues=issues, details=integrity_results)
            
        except Exception as e:
            logger.error("Scheduled data integrity check failed", error=str(e))
            raise
    
    async def start(self):
        """Start the PTR ingestion scheduler."""
        await self.setup_ingestion_tasks()
        await self.scheduler.start()
        
        logger.info("PTR ingestion scheduler started")
    
    async def stop(self):
        """Stop the PTR ingestion scheduler."""
        await self.scheduler.stop()
        logger.info("PTR ingestion scheduler stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return self.scheduler.get_scheduler_stats()
    
    async def run_ingestion_now(self) -> bool:
        """Run full ingestion immediately."""
        return await self.scheduler.run_task_now("ptr_full_ingestion")
    
    async def run_discovery_now(self) -> bool:
        """Run discovery immediately."""
        return await self.scheduler.run_task_now("ptr_discovery")
    
    async def run_health_check_now(self) -> bool:
        """Run health check immediately."""
        return await self.scheduler.run_task_now("health_check")

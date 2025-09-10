"""Logging configuration and utilities for structured logging."""

import sys
import time
import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager
import structlog
from structlog.stdlib import LoggerFactory


class MetricsCollector:
    """Simple metrics collector for tracking performance and errors."""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            'counters': {},
            'timers': {},
            'gauges': {}
        }
    
    def increment(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        key = self._make_key(metric_name, tags)
        self.metrics['counters'][key] = self.metrics['counters'].get(key, 0) + value
    
    def gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        key = self._make_key(metric_name, tags)
        self.metrics['gauges'][key] = value
    
    def timer(self, metric_name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a timer metric."""
        key = self._make_key(metric_name, tags)
        if key not in self.metrics['timers']:
            self.metrics['timers'][key] = []
        self.metrics['timers'][key].append(duration)
    
    def _make_key(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Create a metric key with tags."""
        if not tags:
            return metric_name
        
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric_name}[{tag_str}]"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        return self.metrics.copy()
    
    def reset(self):
        """Reset all metrics."""
        self.metrics = {
            'counters': {},
            'timers': {},
            'gauges': {}
        }


# Global metrics collector instance
metrics = MetricsCollector()


def setup_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """
    Configure structured logging with JSON output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: Whether to use JSON formatting
    """
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


@contextmanager
def log_context(**kwargs):
    """Context manager for adding structured logging context."""
    logger = structlog.get_logger()
    bound_logger = logger.bind(**kwargs)
    
    # Store original logger
    original_logger = structlog.get_logger()
    
    try:
        # Temporarily replace the logger
        structlog._config.logger_factory = lambda: bound_logger
        yield bound_logger
    finally:
        # Restore original logger
        structlog._config.logger_factory = LoggerFactory()


@contextmanager
def performance_timer(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """Context manager for timing operations and recording metrics."""
    start_time = time.time()
    logger = structlog.get_logger()
    
    logger.debug("Operation started", metric=metric_name, tags=tags)
    
    try:
        yield
        duration = time.time() - start_time
        metrics.timer(metric_name, duration, tags)
        logger.debug(
            "Operation completed", 
            metric=metric_name, 
            duration=duration,
            tags=tags
        )
    except Exception as e:
        duration = time.time() - start_time
        metrics.increment(f"{metric_name}.error", tags=tags)
        logger.error(
            "Operation failed",
            metric=metric_name,
            duration=duration,
            error=str(e),
            tags=tags
        )
        raise


def log_function_call(func_name: str, **kwargs):
    """Log a function call with parameters."""
    logger = structlog.get_logger()
    logger.debug("Function called", function=func_name, **kwargs)


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Log an error with context."""
    logger = structlog.get_logger()
    
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    
    if context:
        log_data.update(context)
    
    logger.error("Error occurred", **log_data)
    metrics.increment("errors.total")
    metrics.increment(f"errors.{type(error).__name__}")


def log_performance_metrics():
    """Log current performance metrics."""
    logger = structlog.get_logger()
    current_metrics = metrics.get_metrics()
    
    logger.info("Performance metrics", metrics=current_metrics)


class StructuredLogger:
    """Wrapper for structured logging with common patterns."""
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
        self.name = name
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self.logger.info(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(message, **kwargs)
        metrics.increment("warnings.total")
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message with context."""
        if error:
            kwargs.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })
        
        self.logger.error(message, **kwargs)
        metrics.increment("errors.total")
    
    def bind(self, **kwargs):
        """Create a bound logger with additional context."""
        return StructuredLogger(self.name).logger.bind(**kwargs)
    
    @contextmanager
    def operation(self, operation_name: str, **context):
        """Context manager for logging operations with timing."""
        start_time = time.time()
        
        self.info(f"{operation_name} started", **context)
        
        try:
            yield
            duration = time.time() - start_time
            self.info(
                f"{operation_name} completed",
                duration=duration,
                **context
            )
            metrics.timer(f"{self.name}.{operation_name}", duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.error(
                f"{operation_name} failed",
                error=e,
                duration=duration,
                **context
            )
            metrics.increment(f"{self.name}.{operation_name}.error")
            raise


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)

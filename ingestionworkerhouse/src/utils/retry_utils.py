"""Retry utilities and error handling."""

import asyncio
from typing import Any, Callable, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger()


class RetryableError(Exception):
    """Exception that indicates an operation should be retried."""
    pass


class NonRetryableError(Exception):
    """Exception that indicates an operation should not be retried."""
    pass


def create_retry_decorator(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    multiplier: float = 2.0
):
    """Create a retry decorator with specified parameters."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        reraise=True
    )


async def retry_with_backoff(
    func: Callable,
    *args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    **kwargs
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: The function to retry
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        backoff_factor: Multiplier for delay after each failure
        
    Returns:
        Result of the function call
        
    Raises:
        The last exception if all retries fail
    """
    last_exception = None
    delay = base_delay
    
    for attempt in range(max_attempts):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
                
        except NonRetryableError:
            # Don't retry for non-retryable errors
            raise
            
        except Exception as e:
            last_exception = e
            
            if attempt == max_attempts - 1:
                # Last attempt failed
                logger.error(
                    "All retry attempts failed",
                    function=func.__name__,
                    attempts=max_attempts,
                    error=str(e)
                )
                break
            
            logger.warning(
                "Retry attempt failed, retrying",
                function=func.__name__,
                attempt=attempt + 1,
                max_attempts=max_attempts,
                delay=delay,
                error=str(e)
            )
            
            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)
    
    # All attempts failed
    raise last_exception

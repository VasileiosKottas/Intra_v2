"""
Custom decorators for common functionality
"""

import time
import functools
from typing import Any, Callable

def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f" {func.__name__} executed in {end_time - start_time:.4f} seconds")
        return result
    return wrapper

def cache_result(expiration_seconds: int = 300):
    """Decorator to cache function results for a specified time"""
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Create cache key from function arguments
            cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            current_time = time.time()
            
            # Check if result is cached and not expired
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if current_time - timestamp < expiration_seconds:
                    return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[cache_key] = (result, current_time)
            
            # Clean expired entries
            expired_keys = [
                key for key, (_, timestamp) in cache.items()
                if current_time - timestamp >= expiration_seconds
            ]
            for key in expired_keys:
                del cache[key]
            
            return result
        return wrapper
    return decorator

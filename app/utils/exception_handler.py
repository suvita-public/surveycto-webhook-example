import asyncio
import time
import traceback
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from functools import wraps
from app.config.config_loader import logger

def handle_exceptions(func):
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        except HTTPException as http_exc:
            logger.exception(f"HTTPException: {http_exc.detail}")
            raise http_exc
        except Exception as e:
            logger.error("Unexpected async error:\n" + traceback.format_exc())
            return JSONResponse(status_code=500, content={"response": "Error", "message": str(e)})
        finally:
            duration = (time.time() - start_time) * 1000  # in milliseconds
            logger.info(f"[TIMING] {func.__name__} executed in {duration:.2f} ms")

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        except HTTPException as http_exc:
            logger.exception(f"HTTPException: {http_exc.detail}")
            raise http_exc
        except Exception as e:
            logger.error("Unexpected sync error:\n" + traceback.format_exc())
            return JSONResponse(status_code=500, content={"response": "Error", "message": str(e)})
        finally:
            duration = (time.time() - start_time) * 1000  # in milliseconds
            logger.info(f"[TIMING] {func.__name__} executed in {duration:.2f} ms")

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

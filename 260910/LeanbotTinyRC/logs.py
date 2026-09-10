import asyncio
import time
from datetime import datetime

# ==========================================================
# Internal state
# ==========================================================

_queue = None
_logger_task = None

_last_log_time = None
_log_file_handle = None

_SENTINEL = object()


# ==========================================================
# Public API
# ==========================================================

async def logs_init():
    """
    Initialize background logger.

    Call once from main().
    """
    global _queue, _logger_task

    if _logger_task is not None:
        return

    _queue = asyncio.Queue()
    _logger_task = asyncio.create_task(_logger_loop())


async def logs_shutdown():
    """
    Gracefully stop logger.

    Wait until all queued messages have been processed.
    """
    global _logger_task

    if _logger_task is None:
        return

    _queue.put_nowait(_SENTINEL)

    await _logger_task

    _logger_task = None

    close_log_file()


def log(direction, msg):
    """
    Queue one log message.

    Example:
        log("TX", "AT")
        log("RX", "OK")
    """
    if _queue is None:
        raise RuntimeError("logs_init() has not been called")

    _queue.put_nowait((
        time.perf_counter(),
        datetime.now(),
        direction,
        str(msg),
    ))


def set_log_file(filepath):
    """
    Enable logging to file.

    Optional.
    """
    global _log_file_handle

    close_log_file()

    if filepath:
        _log_file_handle = open(filepath, "w", encoding="utf-8")


def close_log_file():
    """
    Disable file logging.
    """
    global _log_file_handle

    if _log_file_handle is not None:
        _log_file_handle.close()
        _log_file_handle = None


# ==========================================================
# Background logger
# ==========================================================

async def _logger_loop():
    global _last_log_time

    while True:

        item = await _queue.get()

        if item is _SENTINEL:
            _queue.task_done()
            break

        perf_time, wall_time, direction, msg = item

        if _last_log_time is None:
            delta = "---"
        else:
            delta = f"+{int((perf_time - _last_log_time) * 1000)}"

        _last_log_time = perf_time

        timestamp = wall_time.strftime("%H:%M:%S.%f")[:-3]

        line = f"{timestamp} ({delta:>5}) [{direction}] {msg}"

        print(line, flush=True)

        if _log_file_handle is not None:
            _log_file_handle.write(line + "\n")
            _log_file_handle.flush()

        _queue.task_done()
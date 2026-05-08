import time
import threading
import concurrent.futures
from typing import Callable, List, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from core.logger import AppLogger

class ToolWorker(QThread):
    """
    Background worker thread for running tools.

    Signals:
        progress(int, int, int)  — (current, total, duplicates) progress update
        log_message(str, str)    — (message, level) log entry
        finished_signal(dict)    — results dict on completion
        error_signal(str)        — error message on failure
        token_result(str)  — per-token result: (token, result_data)
    """
    
    progress = pyqtSignal(int, int, int)
    log_message = pyqtSignal(str, str)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    token_result = pyqtSignal(str, dict)

    def __init__(self, task_func: Callable, items: List[Any], thread_count: int = 5, **kwargs):
        super().__init__()
        self._task_func = task_func
        self._items = items
        self._thread_count = max(1, min(500, thread_count))
        self._kwargs = kwargs
        
        self._cancelled = False
        self._cancel_event = threading.Event()
        self._logger = AppLogger.instance()

    def cancel(self):
        """Request cancellation of the worker."""
        self._cancelled = True
        self._cancel_event.set()
        self.log_message.emit("Stopping...", "WARNING")

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(self):
        """
        Execute the task across all items — nonstop 1 thread per token.
        thread_count slots run in parallel.
        """
        total = len(self._items)
        success_count = 0
        failed_count = 0
        completed = 0
        duplicates = self._kwargs.get('initial_duplicates', 0)
        max_retries = self._kwargs.get('non_blocking_retries', 3)
        
        lock = threading.Lock()
        retry_queue = []
        results = []

        def run_token(item, attempt=0):
            nonlocal success_count, failed_count, completed
            
            if self._cancelled:
                return
            
            try:
                # Prepare callback for the task if it needs to log
                log_cb = lambda msg, level="INFO": self.log_message.emit(msg, level)
                
                # Execute task
                task_kwargs = self._kwargs.copy()
                task_kwargs['log_callback'] = log_cb
                task_kwargs['worker_cancel_event'] = self._cancel_event
                
                result = self._task_func(item, **task_kwargs)
                
                if result.get('retry_later') and attempt < max_retries:
                    with lock:
                        retry_queue.append((item, attempt + 1))
                    return

                # Update stats
                with lock:
                    completed += 1
                    if result.get('success', False):
                        success_count += 1
                    else:
                        failed_count += 1
                
                # Emit per-token result
                token_str = str(item.token) if hasattr(item, 'token') else str(item)
                self.token_result.emit(token_str, result)
                self.progress.emit(completed, total, duplicates)
                
            except Exception as e:
                with lock:
                    completed += 1
                    failed_count += 1
                self.log_message.emit(f"Error: {str(e)}", "ERROR")
                self.progress.emit(completed, total, duplicates)

        # Main execution loop
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._thread_count) as executor:
                # Initial batch
                futures = [executor.submit(run_token, item) for item in self._items]
                
                # Wait for initial batch and process retries if any
                while futures:
                    done, futures = concurrent.futures.wait(futures, timeout=0.1)
                    if self._cancelled:
                        break
                    
                    # Check for new items in retry queue
                    with lock:
                        while retry_queue:
                            item, att = retry_queue.pop(0)
                            futures.add(executor.submit(run_token, item, att))
            
            # Final report
            details = {
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'duplicates': duplicates,
                'cancelled': self._cancelled
            }
            
            if self._cancelled:
                self.log_message.emit("Task cancelled by user", "WARNING")
                
            self.finished_signal.emit(details)
            
        except Exception as e:
            self.error_signal.emit(f"Worker error: {str(e)}")



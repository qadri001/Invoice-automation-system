"""File system watcher for automatic invoice processing."""
import os
import time
import logging
from pathlib import Path
from typing import Callable, Optional, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

logger = logging.getLogger(__name__)


class InvoiceFileHandler(FileSystemEventHandler):
    """Handler for invoice file events."""

    SUPPORTED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}

    def __init__(self, processor_callback: Callable, processed_dir: str):
        self.processor_callback = processor_callback
        self.processed_dir = processed_dir
        self.pending_files: set = set()
        os.makedirs(processed_dir, exist_ok=True)

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = event.src_path
        if self._is_valid_invoice_file(file_path):
            logger.info(f"New invoice detected: {file_path}")
            self._process_file(file_path)

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = event.src_path
        if self._is_valid_invoice_file(file_path):
            # Avoid processing the same file multiple times rapidly
            if file_path not in self.pending_files:
                logger.info(f"Modified invoice detected: {file_path}")
                self._process_file(file_path)

    def _is_valid_invoice_file(self, file_path: str) -> bool:
        """Check if file is a valid invoice file."""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def _process_file(self, file_path: str):
        """Process the invoice file."""
        try:
            self.pending_files.add(file_path)

            # Wait for file to be fully written (handle large files)
            self._wait_for_file_ready(file_path)

            # Call the processor
            result = self.processor_callback(file_path)

            if result:
                # Move to processed directory
                self._move_to_processed(file_path, result)

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
        finally:
            self.pending_files.discard(file_path)

    def _wait_for_file_ready(self, file_path: str, timeout: int = 30):
        """Wait until file is fully written."""
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < timeout:
            try:
                current_size = os.path.getsize(file_path)
                if current_size == last_size and current_size > 0:
                    # File size stable, assume it's ready
                    time.sleep(0.5)  # Small buffer
                    return
                last_size = current_size
                time.sleep(0.5)
            except OSError:
                time.sleep(0.1)

        logger.warning(f"Timeout waiting for file {file_path}")

    def _move_to_processed(self, file_path: str, result: dict):
        """Move processed file to processed directory."""
        try:
            file_name = Path(file_path).name
            base_name = Path(file_name).stem
            ext = Path(file_name).suffix

            # Add timestamp to avoid overwrites
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            new_name = f"{base_name}_{timestamp}{ext}"
            dest_path = os.path.join(self.processed_dir, new_name)

            # If file is in the same filesystem, rename; otherwise copy
            if Path(file_path).parent.resolve() == Path(self.processed_dir).parent.resolve():
                os.rename(file_path, dest_path)
            else:
                import shutil
                shutil.move(file_path, dest_path)

            logger.info(f"Moved processed file to: {dest_path}")

        except Exception as e:
            logger.error(f"Error moving file: {e}")


class InvoiceWatcher:
    """Watcher service for automatic invoice processing."""

    def __init__(self, input_dir: str, processed_dir: str, 
                 processor_callback: Callable):
        self.input_dir = input_dir
        self.processed_dir = processed_dir
        self.processor_callback = processor_callback
        self.observer: Optional[Observer] = None
        self.is_running = False

    def start(self):
        """Start watching for files."""
        if self.is_running:
            logger.warning("Watcher already running")
            return

        os.makedirs(self.input_dir, exist_ok=True)

        event_handler = InvoiceFileHandler(
            self.processor_callback, 
            self.processed_dir
        )

        self.observer = Observer()
        self.observer.schedule(event_handler, self.input_dir, recursive=False)
        self.observer.start()
        self.is_running = True

        logger.info(f"Started watching directory: {self.input_dir}")

        # Process any existing files
        self._process_existing_files()

    def stop(self):
        """Stop watching."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            logger.info("Watcher stopped")

    def _process_existing_files(self):
        """Process any files already in the directory."""
        logger.info("Checking for existing files...")

        for file_path in Path(self.input_dir).iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in InvoiceFileHandler.SUPPORTED_EXTENSIONS:
                    logger.info(f"Processing existing file: {file_path}")
                    try:
                        result = self.processor_callback(str(file_path))
                        if result:
                            # Move to processed
                            timestamp = time.strftime("%Y%m%d_%H%M%S")
                            new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
                            dest = os.path.join(self.processed_dir, new_name)
                            os.rename(str(file_path), dest)
                    except Exception as e:
                        logger.error(f"Error processing existing file {file_path}: {e}")

    def run_forever(self):
        """Run watcher indefinitely."""
        try:
            self.start()
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()

import logging
import contextvars
import json
import datetime
import os
from src.core.OtelTrace import OtelTrace

# Create a ContextVar for the unique_id
unique_id_var = contextvars.ContextVar("unique_id", default="N/A")

class JSONFormatter(logging.Formatter):
    def format(self, record):
        # Get OpenTelemetry trace and span IDs if available
        trace_id = OtelTrace.get_current_trace_id()
        span_id = OtelTrace.get_current_span_id()
        trace_flags = OtelTrace.get_current_trace_flags()
        
        # Get environment info
        otel_resource_attributes = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")
        attributes = dict(
            attr.split("=")
            for attr in otel_resource_attributes.split(",")
            if "=" in attr
        )
        environment = attributes.get("service.namespace", "development")
        service_name = os.getenv("OTEL_SERVICE_NAME", "pdf-api")

        log_entry = {
            "@timestamp": datetime.datetime.fromtimestamp(record.created).isoformat()
            + "Z",
            "ecs.version": "1.2.0",
            "log.level": record.levelname,
            "severity": record.levelname,  # Explicitly set severity
            "process.thread.name": f"thread-{record.thread}",
            "log.logger": record.name,
            "service": service_name,
            "environment": environment,
            "unique_id": getattr(record, "unique_id", "N/A"),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "pathname": record.pathname,
            "process_id": record.process,
            "message": record.getMessage(),
        }

        # Only add trace/span fields if they exist
        if trace_id and trace_id != "N/A":
            log_entry["trace_id"] = trace_id
        if span_id and span_id != "N/A":
            log_entry["span_id"] = span_id
        if trace_flags and trace_flags != "N/A":
            log_entry["trace_flags"] = trace_flags

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            # Also add stack trace for better debugging
            log_entry["stack_trace"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class LocalLogFormatter(logging.Formatter):
    def format(self, record):
        # Set up color codes
        RESET = "\033[0m"
        COLORS = {
            "DEBUG": "\033[36m",  # Cyan
            "INFO": "\033[32m",  # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",  # Red
            "CRITICAL": "\033[41m",  # Red background
            "LEVEL_NAME": "\033[32m",  # Green
            "NAME": "\033[34m",  # Blue
            "TIME": "\033[90m",  # Grey
        }
        color = COLORS.get(record.levelname, RESET)
        # Ensure asctime and message are present
        record.asctime = self.formatTime(record, self.datefmt)
        record.message = record.getMessage()

        # Format the base message
        formatted_message = f"{color}{record.levelname}{RESET}: {COLORS['TIME']}{record.pathname}:{record.lineno}{RESET} - {COLORS['TIME']}{record.asctime}{RESET}\n{record.message}"

        # Add exception info if present
        if record.exc_info:
            formatted_message += "\n" + self.formatException(record.exc_info)

        return formatted_message


class UniqueIDFilter(logging.Filter):
    def __init__(self, name=""):
        super().__init__(name)

    def filter(self, record):
        if not hasattr(record, "unique_id"):
            record.unique_id = unique_id_var.get()
        return True


def configure_logger():
    # Configure the logging format and level
    # Use JSONFormatter for production environments (when OTEL is configured)
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        formatter = JSONFormatter()
    else:
        # Use LocalLogFormatter for local development
        formatter = LocalLogFormatter()

    # Set log level based on environment
    log_level_str = os.getenv("LOG_LEVEL", "INFO")
    if log_level_str == "DEBUG":
        log_level = logging.DEBUG
    elif log_level_str == "INFO":
        log_level = logging.INFO
    elif log_level_str == "WARNING":
        log_level = logging.WARNING
    elif log_level_str == "ERROR":
        log_level = logging.ERROR
    else:
        log_level = logging.INFO

    # Create a handler
    handler = logging.StreamHandler()

    # Setting level
    handler.setLevel(log_level)

    # Setting formatter
    handler.setFormatter(formatter)

    # Adding filter to handler
    unique_id_filter = UniqueIDFilter()
    handler.addFilter(unique_id_filter)

    # Create the root logger and attach the handler
    logger = logging.getLogger()
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    logger.addHandler(handler)
    logger.setLevel(log_level)

    # Disable logging for uvicorn loggers to avoid noise
    for uvicorn_logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        uv_logger = logging.getLogger(uvicorn_logger_name)
        uv_logger.handlers.clear()
        uv_logger.setLevel(logging.CRITICAL + 1)
        uv_logger.propagate = False

    logger.info("Logger configured with OpenTelemetry support")
    return logger

from src.core.logger_config import configure_logger
from src.core.OtelTrace import OtelTrace

# Configure the logger
configure_logger()

__all__ = [
    "configure_logger",
    "OtelTrace",
]

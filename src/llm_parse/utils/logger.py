import inspect
import logging
import os
import sys
from typing import Optional


class ContextAwareFilter(logging.Filter):
    """
    Adds page_number and file_path to the log record if they're found
    in the current frame's local variables.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        current_frame = inspect.currentframe()
        outer_frames = inspect.getouterframes(current_frame)

        for frame_info in outer_frames:
            frame = frame_info.frame
            local_vars = frame.f_locals

            # Check and attach page_number
            if "page_number" in local_vars:
                record.page_number = local_vars["page_number"]
            else:
                record.page_number = None

            # Check and attach file_path
            if "file_path" in local_vars:
                record.file_path = local_vars["file_path"]
            else:
                record.file_path = None

            # Stop at the first useful match
            if getattr(record, "page_number", None) or getattr(
                record, "file_path", None
            ):
                break

        return True


class ContextAwareFormatter(logging.Formatter):
    LOG_COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        log_parts = [
            "[%(asctime)s]",
            f"{self.LOG_COLORS.get(record.levelname, '')}[%(levelname)s]{self.RESET}",
            "[%(name)s]",
        ]

        rel_path = os.path.relpath(record.pathname, start=os.getcwd())
        log_parts.append(f"[{rel_path}:{record.lineno}]")

        # Optional extras
        if file_path := getattr(record, "file_path", None):
            log_parts.append(f"[file_path: {file_path}]")
        if (page_number := getattr(record, "page_number", None)) is not None:
            log_parts.append(f"[page: {page_number}]")

        log_parts.append("→ %(message)s")
        self._style._fmt = " ".join(log_parts)
        return super().format(record)


def get_logger(name: str, provider: Optional[str] = None) -> logging.Logger:
    """
    Create and configure a logger with optional cloud logging support.

    This logger includes:
    - A context-aware formatter and filter to enrich logs with custom fields
      like `page_number` and `file_path`.
    - A console handler by default.
    - Optional integration with cloud logging providers (GCP, AWS, Azure, Sentry).
    - Safe repeated use (idempotent handler setup).

    Parameters
    ----------
    name : str
        The name of the logger, typically `__name__` from the calling module.
    provider : str or None, optional
        The cloud logging provider to use. Supported values:
        - "gcp": Google Cloud Logging via `google-cloud-logging`
        - "aws": AWS CloudWatch via `watchtower`
        - "azure": Azure Monitor via `opencensus-ext-azure`
        - "sentry": Sentry logging via `sentry-sdk`

    Returns
    -------
    logging.Logger
        A configured logger instance with a console handler and optional cloud handler.

    Notes
    -----
    - For GCP, this function uses `CloudLoggingHandler` instead of `setup_logging()`
      to allow setting custom formatters and filters.
    - Cloud handlers are only attached if the required packages are installed.
    - If the logger already has handlers, no new handlers are added again.
    """

    logger = logging.getLogger(name)

    if logger.handlers:
        # Prevent duplicate handlers on multiple calls
        return logger

    logger.setLevel(logging.INFO)
    formatter = ContextAwareFormatter(datefmt="%Y-%m-%d %H:%M:%S")
    context_filter = ContextAwareFilter()

    # Console handler (always present)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)
    logger.addHandler(console_handler)

    # Add cloud logging provider, if configured
    if provider == "gcp":
        try:
            from google.cloud.logging import Client as GCPClient
            from google.cloud.logging.handlers import CloudLoggingHandler

            gcp_client = GCPClient()
            gcp_handler = CloudLoggingHandler(gcp_client)
            gcp_handler.setFormatter(formatter)
            gcp_handler.addFilter(context_filter)
            logger.addHandler(gcp_handler)

            logger.info("✅ GCP Cloud Logging enabled.")
        except ImportError:
            logger.warning("⚠️ GCP cloud logging not installed.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to enable GCP logging: {e}")

    elif provider == "aws":
        try:
            import watchtower

            cw_handler = watchtower.CloudWatchLogHandler()
            cw_handler.setFormatter(formatter)
            cw_handler.addFilter(context_filter)
            logger.addHandler(cw_handler)

            logger.info("✅ AWS CloudWatch Logging enabled.")
        except ImportError:
            logger.warning(
                "⚠️ watchtower not installed (AWS CloudWatch logging disabled)."
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to enable AWS CloudWatch logging: {e}")

    elif provider == "azure":
        try:
            from opencensus.ext.azure.log_exporter import AzureLogHandler

            azure_handler = AzureLogHandler()
            azure_handler.setFormatter(formatter)
            azure_handler.addFilter(context_filter)
            logger.addHandler(azure_handler)

            logger.info("✅ Azure Monitor Logging enabled.")
        except ImportError:
            logger.warning("⚠️ opencensus-ext-azure not installed.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to enable Azure Monitor logging: {e}")

    elif provider == "sentry":
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration

            sentry_logging = LoggingIntegration(
                level=logging.INFO, event_level=logging.ERROR
            )
            sentry_sdk.init(integrations=[sentry_logging])
            logger.info("✅ Sentry logging enabled.")
        except ImportError:
            logger.warning("⚠️ sentry-sdk not installed.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to enable Sentry logging: {e}")

    logger.propagate = False
    return logger

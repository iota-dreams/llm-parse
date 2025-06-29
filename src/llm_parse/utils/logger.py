import inspect
import logging
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
    def format(self, record: logging.LogRecord) -> str:
        base = (
            "[%(asctime)s] [%(levelname)s] [%(name)s] "
            "[%(filename)s:%(funcName)s:%(lineno)d]"
        )

        # Conditionally add custom fields
        file_path = getattr(record, "file_path", None)
        if file_path:
            base += f" [file_path: {file_path}]"
        page_number = getattr(record, "page_number", None)
        if page_number is not None:
            base += f" [page: {page_number}]"

        base += " → %(message)s"

        self._style._fmt = base
        return super().format(record)


def get_logger(name: str, provider: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        formatter = ContextAwareFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        context_filter = ContextAwareFilter()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(context_filter)
        logger.addHandler(console_handler)

        # Optional cloud logging integrations (same as before)
        if provider == "gcp":
            try:
                import google.cloud.logging as cloud_logging

                client = cloud_logging.Client()
                client.setup_logging()
                logger.info("✅ GCP Cloud Logging enabled.")
            except ImportError:
                logger.warning("⚠️ GCP cloud logging not installed.")

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

        logger.propagate = False

    return logger

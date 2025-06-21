import logging
import sys
from typing import Optional


def get_logger(name: str, provider: Optional[str] = None) -> logging.Logger:
    """
    Returns a configured logger instance. Defaults to local console logging.
    Optionally adds cloud logging handlers for supported providers:
    'gcp', 'aws', 'azure', 'sentry'.

    Args:
        name (str): Logger name, typically __name__.
        provider (Optional[str]): Cloud provider name. Defaults to None.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Always add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Optional cloud logging
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

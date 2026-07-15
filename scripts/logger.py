import os
import re
import logging
from logging.handlers import RotatingFileHandler

class TokenScrubFilter(logging.Filter):
    """
    Log filter that intercepts and redacts GitHub Personal Access Tokens
    and standard environment secrets from being printed to terminal/files.
    """
    # Pattern to match classic (ghp_...) or fine-grained (github_pat_...) tokens
    TOKEN_PATTERN = re.compile(r'(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})')

    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self.TOKEN_PATTERN.sub('[REDACTED_TOKEN]', record.msg)
        return True

def setup_logger(name="skyline", log_level=logging.INFO):
    """
    Configure and return a standard logger printing to stdout/stderr and
    writing to logs/pipeline.log with automatic rotation.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Ensure log directory exists
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'pipeline.log')

    # Token Scrub Filter
    scrub_filter = TokenScrubFilter()

    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s'
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(scrub_filter)
    logger.addHandler(console_handler)

    # Rotating File Handler (Max 1MB, keeping 5 backups)
    file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(scrub_filter)
    logger.addHandler(file_handler)

    return logger

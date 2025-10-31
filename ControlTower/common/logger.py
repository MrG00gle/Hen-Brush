import logging
from colorama import init, Fore, Style

init(autoreset=True)

COMM_LEVEL_NUM = 25
logging.addLevelName(COMM_LEVEL_NUM, "COMM")

def comm(self, message, *args, **kwargs):
    if self.isEnabledFor(COMM_LEVEL_NUM):
        self._log(COMM_LEVEL_NUM, message, args, **kwargs)

logging.Logger.comm = comm   # monkey-patch Logger


class ColoredFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG:    Fore.GREEN,
        logging.INFO:     Fore.BLUE,
        logging.WARNING:  Fore.YELLOW,
        COMM_LEVEL_NUM:   Fore.MAGENTA,   # purple
        logging.ERROR:    Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, Fore.WHITE)
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)


_LOGGERS = {}   # keep a reference so we never add duplicate handlers

def get_logger(name: str = "app") -> logging.Logger:
    """
    Return a logger with coloured console output.
    Call it from any module: `log = get_logger(__name__)`
    """
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)          # capture everything

    # ---- console handler (only once) ----
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        fmt = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        )
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    _LOGGERS[name] = logger
    return logger
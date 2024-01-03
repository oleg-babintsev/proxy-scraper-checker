from __future__ import annotations

import asyncio
import logging
import sys
import atexit
from configparser import ConfigParser
from datetime import datetime, timezone

# import rich.traceback
from rich.console import Console
from rich.logging import RichHandler

from .proxy_scraper_checker import ProxyScraperChecker
from . import proxy


CONFIG_PATH = "../proxy-scraper-checker-configs"


def set_event_loop_policy() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    elif sys.implementation.name == "cpython" and sys.platform in {
        "darwin",
        "linux",
    }:
        try:
            import uvloop
        except ImportError:
            pass
        else:
            uvloop.install()


def configure_logging(console: Console, *, debug: bool) -> None:
    # rich.traceback.install(console=console)
    timestamp = datetime.now().astimezone(timezone.utc).strftime('%Y%m%d-%H%M%S')
    file_handler = logging.FileHandler(f'{CONFIG_PATH}/scan_logs/{timestamp}.log')
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=(
            file_handler,
            RichHandler(
                console=console,
                omit_repeated_times=False,
                show_path=False,
                rich_tracebacks=True,
            ),
        ),
    )


def get_config(file: str) -> ConfigParser:
    print("Config:", file)
    cfg = ConfigParser(interpolation=None)
    cfg.read(file, encoding="utf-8")
    return cfg


async def main() -> None:
    config_file = "config.ini"
    if len(sys.argv) > 1:
        config_file = f"config_{sys.argv[1]}.ini"
    cfg = get_config(f"{CONFIG_PATH}/{config_file}")

    console = Console()
    configure_logging(console, debug=cfg["General"].getboolean("Debug", False))
    logging.getLogger(__name__).info(f"Config: {config_file}")

    general = cfg["General"]
    proxy.STOP_LOCATIONS = tuple([v.strip() for v in (general.get("StopLocations") or "").splitlines() if v])
    proxy.BINGO_LOCATIONS = tuple([v.strip() for v in (general.get("BingoLocations") or "").splitlines() if v])

    await ProxyScraperChecker.from_configparser(cfg, console=console).run()


def goodbye():
    logging.getLogger(__name__).info(f"Exit time: {datetime.now()}")


if __name__ == "__main__":
    # register a function to be executed at termination
    atexit.register(goodbye)
    # start main
    set_event_loop_policy()
    asyncio.run(main())

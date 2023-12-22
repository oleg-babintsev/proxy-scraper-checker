from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from time import perf_counter
from types import MappingProxyType
from typing import Union, Tuple, Optional

from aiohttp import ClientSession, ClientTimeout
from aiohttp.abc import AbstractCookieJar
from aiohttp_socks import ChainProxyConnector, ProxyType, ProxyInfo

from .null_context import AsyncNullContext

logger = logging.getLogger(__name__)

# noinspection HttpUrlsUsage
DEFAULT_CHECK_WEBSITE = "http://ip-api.com/json/?fields=8217"
HEADERS = MappingProxyType(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; rv:109.0)"
            " Gecko/20100101 Firefox/117.0"
        )
    }
)

STOP_LOCATIONS = tuple()
BINGO_LOCATIONS = tuple()


@dataclass(repr=False, unsafe_hash=True)
class Proxy:
    __slots__ = ("geolocation", "host", "is_anonymous", "port", "timeout", "tunnel", "check_mode")

    host: str
    port: int
    tunnel: Optional[Tuple[ProxyInfo, asyncio.Semaphore]]
    check_mode: bool

    # noinspection PyAttributeOutsideInit
    async def check(
        self,
        *,
        website: str,
        sem: Union[asyncio.Semaphore, AsyncNullContext],
        cookie_jar: AbstractCookieJar,
        proto: ProxyType,
        timeout: ClientTimeout,
    ) -> None:
        if website == "default":
            website = DEFAULT_CHECK_WEBSITE

        async with sem:
            start = perf_counter()

            chain = []
            sem_within_tunnel = AsyncNullContext()
            if self.tunnel:
                chain.append(self.tunnel[0])
                sem_within_tunnel = self.tunnel[1]
            # print(self.tunnel[0])
            # print(self.port)
            chain.append(ProxyInfo(proxy_type=proto, host=self.host, port=self.port))
            connector = ChainProxyConnector(chain)

            async with sem_within_tunnel:
                # print(chain)
                # print(self.port)
                logger.debug(
                    f'CHAIN: {proto.name.lower()}://{self.tunnel[0].host}:{self.tunnel[0].port} '
                    f'-> {self.host}:{self.port}'
                )
                async with ClientSession(
                    connector=connector,
                    cookie_jar=cookie_jar,
                    timeout=timeout,
                    headers=HEADERS,
                ) as session, session.get(
                    website, raise_for_status=True
                ) as response:
                    if website == DEFAULT_CHECK_WEBSITE:
                        await response.read()
        self.timeout = perf_counter() - start
        if website == DEFAULT_CHECK_WEBSITE:
            data = await response.json(content_type=None)
            self.is_anonymous = self.host != data["query"]
            self.geolocation = "|{}|{}|{}|{}".format(
                data["country"], data["regionName"], data["city"], data["query"]
            )
            if self.check_mode:
                logger.info(f'{proto.name.lower()}://{self.tunnel[0].host}:{self.tunnel[0].port}')
                return
            name_str = self.as_str(include_geolocation=True)
            # bingo locations
            if any(v in name_str for v in BINGO_LOCATIONS):
                logger.info('---------- BINGO!!! ----------')
                logger.info(f'PROXY({proto.name}): {name_str}')
                logger.info('------------------------------')
            else:
                logger.info(f'PROXY({proto.name}): {name_str}')
            # stop locations
            if any(v in name_str for v in STOP_LOCATIONS):
                logger.info('FOUND!!!')
                raise ValueError('Done!!!')

    def as_str(self, *, include_geolocation: bool) -> str:
        if include_geolocation:
            return f"{self.host}:{self.port}{self.geolocation}"
        return f"{self.host}:{self.port}"

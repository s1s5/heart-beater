import asyncio
import logging
import os
from urllib.parse import urlparse

import aiohttp
import yaml

logger = logging.getLogger(__name__)


async def ping(url, url_kwargs, ping_url):
    timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_connect=10, sock_read=30)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=timeout, **url_kwargs) as res:
            if 200 <= res.status < 400:
                logger.debug("[test] %s status=%d", url, res.status)
                async with session.get(ping_url, timeout=timeout) as ping_res:
                    logger.debug("[ping] %s status=%d", ping_url, ping_res.status)


async def ping_forever(url, timeout, ping_url, **url_kwargs):
    url_kwargs = dict(**url_kwargs)
    try:
        p = urlparse(url)
        if "@" in p.netloc:
            ipass, domain = p.netloc.split("@")
            url = p._replace(netloc=domain).geturl()
            login, password = ipass.split(":")
            url_kwargs["auth"] = aiohttp.BasicAuth(login=login, password=password)
    except Exception as e:
        logger.exception(f"Error parsing url: {e}")
        return

    while True:
        try:
            await ping(url, url_kwargs, ping_url)
        except Exception as e:
            logger.exception("url=%s, exception=%s", url, e)
        await asyncio.sleep(timeout)


async def main(config):
    config = yaml.safe_load(config)
    await asyncio.gather(*[ping_forever(**value) for value in config], return_exceptions=True)


def __entry_point():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", type=argparse.FileType("r"), default=os.environ.get("HB_CONFIG_PATH", "config.yml")
    )
    parser.add_argument("-l", "--log-level", default="error", choices=["debug", "info", "error"])

    kwargs = dict(parser.parse_args()._get_kwargs())
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(
        {"debug": logging.DEBUG, "info": logging.INFO, "error": logging.ERROR}[kwargs.pop("log_level")]
    )
    asyncio.run(main(**kwargs))


if __name__ == "__main__":
    __entry_point()

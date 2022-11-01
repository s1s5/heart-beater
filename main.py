import asyncio
import logging
import os
from typing import Optional
from urllib.parse import urlparse

import aiohttp
import yaml
from crontab import CronTab

logger = logging.getLogger(__name__)
default_timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_connect=10, sock_read=30)


async def ping(session: aiohttp.ClientSession, method: str, url: str, request_kwargs):
    async with session.request(method, url, **request_kwargs) as res:
        logger.debug("[test] %s status=%d", url, res.status)
        res.raise_for_status()


def split_auth_from_url(url: Optional[str]):
    if not url:
        return url, None

    p = urlparse(url)
    if "@" in p.netloc:
        ipass, domain = p.netloc.split("@")
        url = p._replace(netloc=domain).geturl()
        login, password = ipass.split(":")
        auth = aiohttp.BasicAuth(login=login, password=password)
    else:
        auth = None
    return url, auth


def key_value_list_to_dict(kvl):
    if not kvl:
        return None
    d = {}
    for v in kvl:
        d[v["name"]] = v["value"]
    return d


async def ping_forever(
    *,
    name=None,
    url: str,
    ping_url: str,
    fail_ping_url: Optional[str] = None,
    period: Optional[int] = None,
    cron: Optional[str] = None,
    method: str = "GET",
    params=None,
    headers=None,
    proxy=None,
    timeout=None
):
    # data=None, json=None, cookies=None,
    # skip_auto_headers=None, auth=None, allow_redirects=True,
    # max_redirects=10, compress=None, chunked=None, expect100=False,
    # raise_for_status=None, read_until_eof=True, read_bufsize=None,
    # proxy_auth=None, timeout=None, ssl=None, verify_ssl=None,
    # fingerprint=None, ssl_context=None, proxy_headers=None):
    name = name if name else ping_url
    if ((not period) and (not cron)) or (period and cron):
        logger.error("%s period or cron must be specified.", name)
        return

    if cron:
        cron_entry = CronTab(cron)

    def get_sleep_time() -> float:
        if period:
            return period
        return cron_entry.next(default_utc=True)  # type: ignore

    try:
        request_kwargs = {}
        url, request_kwargs["auth"] = split_auth_from_url(url)  # type: ignore
        request_kwargs["proxy"], request_kwargs["proxy_auth"] = split_auth_from_url(proxy)
        request_kwargs["params"] = key_value_list_to_dict(params)
        request_kwargs["headers"] = key_value_list_to_dict(headers)
        if timeout:
            if isinstance(timeout, (int, float)):
                request_kwargs["timeout"] = timeout
            else:
                # total=None, connect=None, sock_connect=None, sock_read=None
                request_kwargs["timeout"] = aiohttp.ClientTimeout(**timeout)
        else:
            request_kwargs["timeout"] = default_timeout

        [request_kwargs.pop(x) for x in [key for key, value in request_kwargs.items() if value is None]]
        logger.debug(
            "name=%s, url=%s, ping_url=%s, period=%s, request_kwargs=%s",
            name,
            url,
            ping_url,
            period,
            request_kwargs,
        )

        if cron:
            await asyncio.sleep(cron_entry.next(default_utc=True))  # type: ignore

        while True:
            async with aiohttp.ClientSession() as session:
                try:
                    await ping(session, method, url, request_kwargs)
                    async with session.get(ping_url, timeout=default_timeout) as ping_res:
                        logger.debug("[ping] %s -> %s status=%d", name, ping_url, ping_res.status)
                except Exception as e:
                    if fail_ping_url:
                        async with session.get(fail_ping_url, timeout=default_timeout) as ping_res:
                            logger.debug("[failping] %s status=%d", fail_ping_url, ping_res.status)
                    logger.exception("%s: url=%s, exception=%s", name, url, e)
            await asyncio.sleep(get_sleep_time())
    except Exception as e:
        logger.exception("%s load settings failed, url=%s, exception=%s", name, url, e)


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

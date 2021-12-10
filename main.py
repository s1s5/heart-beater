import asyncio
import os
import logging
from urllib.parse import urlparse

import aiohttp
import yaml

logger = logging.getLogger(__name__)
# logging.basicConfig(format='%(asctime)-15s %(message)s')
default_timeout = aiohttp.ClientTimeout(
    total=60, connect=10, sock_connect=10, sock_read=30)


async def ping(method, url, request_kwargs, ping_url):
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, **request_kwargs) as res:
            if 200 <= res.status < 400:
                logger.debug('[test] %s status=%d', url, res.status)
        async with session.get(ping_url, timeout=default_timeout) as ping_res:
            logger.debug('[ping] %s status=%d', ping_url, ping_res.status)


def split_auth_from_url(url):
    if not url:
        return None, None

    p = urlparse(url)
    if '@' in p.netloc:
        ipass, domain = p.netloc.split('@')
        url = p._replace(netloc=domain).geturl()
        login, password = ipass.split(':')
        auth = aiohttp.BasicAuth(login=login, password=password)
    else:
        auth = None
    return url, auth


def key_value_list_to_dict(kvl):
    if not kvl:
        return None
    d = {}
    for v in kvl:
        d[v['name']] = v['value']
    return d


async def ping_forever(url, ping_url, period, method='GET',
                       params=None, headers=None, proxy=None, timeout=None):
    # data=None, json=None, cookies=None,
    # skip_auto_headers=None, auth=None, allow_redirects=True,
    # max_redirects=10, compress=None, chunked=None, expect100=False,
    # raise_for_status=None, read_until_eof=True, read_bufsize=None,
    # proxy_auth=None, timeout=None, ssl=None, verify_ssl=None,
    # fingerprint=None, ssl_context=None, proxy_headers=None):

    request_kwargs = {}
    url, request_kwargs['auth'] = split_auth_from_url(url)
    request_kwargs['proxy'], request_kwargs['proxy_auth'] = split_auth_from_url(proxy)
    request_kwargs['params'] = key_value_list_to_dict(params)
    request_kwargs['headers'] = key_value_list_to_dict(headers)
    if timeout:
        if isinstance(timeout, (int, float)):
            request_kwargs['timeout'] = timeout
        else:
            # total=None, connect=None, sock_connect=None, sock_read=None
            request_kwargs['timeout'] = aiohttp.ClientTimeout(**timeout)
    else:
        request_kwargs['timeout'] = default_timeout

    [request_kwargs.pop(x) for x in [key for key, value in request_kwargs.items() if value is None]]
    logger.debug('url=%s, ping_url=%s, period=%s, request_kwargs=%s',
                 url, ping_url, period, request_kwargs)
    while True:
        try:
            await ping(method, url, request_kwargs, ping_url)
        except Exception as e:
            logger.exception('url=%s, exception=%s', url, e)
        await asyncio.sleep(period)


async def main(config):
    config = yaml.safe_load(config)
    await asyncio.gather(*[
        ping_forever(**value) for value in config
    ], return_exceptions=True)


def __entry_point():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=argparse.FileType("r"),
                        default=os.environ.get('HB_CONFIG_PATH', 'config.yml'))
    parser.add_argument("-l", "--log-level", default='error', choices=['debug', 'info', 'error'])

    kwargs = dict(parser.parse_args()._get_kwargs())
    logger.addHandler(logging.StreamHandler())
    logger.setLevel({'debug': logging.DEBUG, 'info': logging.INFO, 'error': logging.ERROR}[kwargs.pop('log_level')])
    asyncio.run(main(**kwargs))


if __name__ == '__main__':
    __entry_point()

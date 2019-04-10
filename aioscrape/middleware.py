import asyncio
import re

from funcy import decorator
from aiohttp.client_exceptions import ClientError
import aioscrape


@decorator
async def log_fetch(call, print_func=print):
    print_func('FETCH ' + call.url)
    return await call()


@decorator
async def last_fetch(call, filename):
    result = await call()
    with open(filename, 'w') as f:
        f.write(result.body)
    return result


def filecache(basedir):
    # Import from here since these are optional dependencies
    from aiocache import cached
    from aiocache.serializers import PickleSerializer
    from aiofilecache import FileCache

    return cached(cache=FileCache, serializer=PickleSerializer(),
                  basedir=basedir, timeout=None, key_builder=_key_builder)

def _key_builder(func, url, *args, **kwargs):
    url = re.sub(r'#.*$', '', url)
    return (func.__module__ or '') + func.__name__ + url


class ValidateError(Exception):
    pass

@decorator
async def validate(call, validator=None):
    result = await call()
    validator = aioscrape.settings.get('validator')
    if validator and not validator(result):
        raise ValidateError
    return result


RETRY_CODES = {503}
RETRY_ERRORS = (ClientError, asyncio.TimeoutError, ValidateError)

class RetryCode(Exception):
    pass

@decorator
@aioscrape.configurable_middleware
async def retry(call, *, tries=10, codes=RETRY_CODES, errors=RETRY_ERRORS,
                         timeout=60, on_error=None):
    """Makes decorated function retry up to tries times.
       Retries only on specified errors.
       Sleeps timeout or timeout(attempt) seconds between tries."""
    errors = _ensure_exceptable(errors)
    if codes:
        errors += (RetryCode,)
    for attempt in range(tries):
        try:
            res = await call()
            if res.status in codes:
                raise RetryCode(res.reason)
            return res
        except errors as e:
            if on_error:
                message = f'{e.__class__.__name__}: {e}' if str(e) else e.__class__.__name__
                on_error(f'Failed with {message}, retrying {attempt + 1}/{tries}...')
            # Reraise error on last attempt
            if attempt + 1 == tries:
                raise
            else:
                timeout_value = timeout(attempt) if callable(timeout) else timeout
                if timeout_value > 0:
                    await asyncio.sleep(timeout_value)


def _ensure_exceptable(errors):
    """Ensures that errors are passable to except clause.
       I.e. should be BaseException subclass or a tuple."""
    is_exception = isinstance(errors, type) and issubclass(errors, BaseException)
    return (errors,) if is_exception else tuple(errors)


from collections import defaultdict
from urllib.parse import urlparse

@decorator
@aioscrape.configurable_middleware
async def limit(call, *, concurrency=None, per_domain=None):
    domain = urlparse(call.url).netloc

    if not hasattr(call._func, 'running'):
        call._func.running = defaultdict(set)
    running = call._func.running['']
    running_in_domain = call._func.running[domain]

    while concurrency and len(running) >= concurrency \
            or per_domain and len(running_in_domain) >= per_domain:
        await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
        _clean_tasks(running)
        _clean_tasks(running_in_domain)

    this = asyncio.ensure_future(call())
    running.add(this)
    running_in_domain.add(this)
    return await this


def _clean_tasks(running):
    for task in list(running):
        if task.done():
            running.remove(task)

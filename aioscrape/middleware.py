from funcy import decorator
from aiohttp.client_exceptions import ClientError


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
                  basedir=basedir, timeout=None)


RERTRY_ERRORS = (ClientError, asyncio.TimeoutError)

@decorator
async def retry(call, tries=10, errors=RERTRY_ERRORS, timeout=60, on_error=None):
    """Makes decorated function retry up to tries times.
       Retries only on specified errors.
       Sleeps timeout or timeout(attempt) seconds between tries."""
    errors = _ensure_exceptable(errors)
    for attempt in range(tries):
        try:
            return await call()
        except errors as e:
            if on_error:
                message = f'{e.__class__.__name__}: {e}' if str(e) else e.__class__.__name__
                on_error(f'Failed with {message}, retrying {attempt + 1}/{tries}...', error=e)
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
    return errors if is_exception else tuple(errors)

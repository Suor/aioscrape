from inspect import signature
from contextlib import contextmanager
from contextvars import ContextVar
import aiohttp
import asyncio

try:
    import aiocontextvars
except ImportError:
    pass
from funcy import compose, decorator, project, merge
from parsechain import Response


# Used to store dynamically scoped settings, part of them are session keyword params
SETTINGS = ContextVar('settings', default={})
SESSION = ContextVar('session')
SESSION_PARAMS = [p.name for p in signature(aiohttp.ClientSession).parameters.values()
                         if p.kind == p.KEYWORD_ONLY]


def run(coro):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(with_session(coro))


@contextmanager
def settings(**values):
    old_values = SETTINGS.get()
    try:
        token = SETTINGS.set(merge(old_values, values))
        yield
    finally:
        SETTINGS.reset(token)


async def with_session(coro):
    """
    Automatically creates aiohttp session around coro.

    A noop if there is a session already, created session is based on settings in scope.
    """
    try:
        session = SESSION.get()
        return await coro
    except LookupError:
        params = project(SETTINGS.get(), SESSION_PARAMS)
        async with aiohttp.ClientSession(**params) as session:
            try:
                token = SESSION.set(session)
                return await coro
            finally:
                SESSION.reset(token)


@decorator
def compose_wrap(call, param):
    middleware = SETTINGS.get().get(param, [])
    key = tuple(middleware) + (call._func,)
    try:
        composed = compose_wrap.cache[key]
    except KeyError:
        composed = compose_wrap.cache[key] = compose(*middleware)(call._func)
    return composed(*call._args, **call._kwargs)

compose_wrap.cache = {}


@compose_wrap('middleware')
async def fetch(url, *, headers=None):
    print('REAL FETCH', url)
    session = SESSION.get()
    async with session.get(url, headers=headers) as response:
        body = await response.text()
        return Response(
            method=response.method, url=url, body=body,
            status=response.status, reason=response.reason,
            headers=dict(response.headers)
        )

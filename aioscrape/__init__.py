from .version import __version__, VERSION
import sys
if sys.version_info < (3, 7):
    import aiocontextvars

from inspect import signature
from contextlib import contextmanager
from contextvars import ContextVar
import aiohttp
import asyncio

from funcy import compose, decorator, project, merge, cut_prefix
from parsechain import Response


__all__ = ['settings', 'run', 'fetch', 'fetchall', 'save']


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


settings.get = lambda param, default=None: SETTINGS.get().get(param, default)


def settings_middleware(what, *, after=None, before=None):
    assert not (after and before), "Should use either after or before param"

    if callable(what):
        what = [what]

    middleware = settings.get('middleware', [])
    i = _get_index(middleware, after or before)
    if after:
        i += 1
    return settings(middleware=middleware[:i] + what + middleware[i:])
settings.middleware = settings_middleware


def _get_index(middleware, name):
    for i, func in enumerate(middleware):
        if _get_name(func) == name:
            return i

from funcy import fallback

def _get_name(func):
    return fallback(
        lambda: func.__closure__[1].cell_contents.__name__,
        lambda: func.__name__,
        lambda: func.__class__.__name__,
    )


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
def configurable_middleware(call):
    prefix = call._func.__name__ + '__'
    overwrites = {cut_prefix(name, prefix): value
                  for name, value in SETTINGS.get().items() if name.startswith(prefix)}
    return call(**overwrites)


@decorator
def compose_wrap(call, param):
    middleware = settings.get(param, [])
    key = tuple(middleware) + (call._func,)
    try:
        composed = compose_wrap.cache[key]
    except KeyError:
        composed = compose_wrap.cache[key] = compose(*middleware)(call._func)
    return composed(*call._args, **call._kwargs)

compose_wrap.cache = {}


@compose_wrap('middleware')
async def fetch(url, *, headers=None, proxy=None, timeout=None):
    session = SESSION.get()
    async with session.get(url, headers=headers, proxy=proxy, timeout=None) as response:
        body = await response.text()
        return Response(
            method=response.method, url=str(response.url), body=body,
            status=response.status, reason=response.reason,
            headers=dict(response.headers)
        )


# TODO: make an async generator?
def fetchall(urls):
    return asyncio.gather(*map(fetch, urls))


# This is a glorified hook with a predefined name,
# serves the purpose of separating scraping code from record processing one.
# TODO: make this async only
def save(record):
    return settings.get('save')(record)

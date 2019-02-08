from pathlib import Path

from funcy import decorator
from aiocache import cached
from aiocache.serializers import PickleSerializer
from aiofilecache import FileCache


@decorator
async def last_fetch(call):
    result = await call()
    Path('last_fetch.html').write_text(result.body)
    return result


def make_filecache(basedir):
    return cached(cache=FileCache, serializer=PickleSerializer(),
                  basedir=basedir)

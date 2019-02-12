from funcy import decorator


@decorator
async def last_fetch(call):
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
                  basedir=basedir)

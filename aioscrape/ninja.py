import heapq

from funcy import decorator
from fake_useragent import UserAgent

from aioscrape import SESSION


@decorator
async def random_proxy(call, *, scheme=None, proxies=[], proxies_file=None, _pqueue=[]):
    assert proxies or proxies_file

    if not proxies:
        with open(proxies_file) as fd:
            lines = fd.read().splitlines()
        if scheme:
            lines = [p for p in lines if p.startswith(scheme + ':')]
        proxies.extend(lines)

    # Use priority queue to use proxies with least errors
    if not _pqueue:
        _pqueue.extend((0, p) for p in proxies)
        heapq.heapify(_pqueue)

    try:
        errs, proxy = heapq.heappop(_pqueue)
        res = await call(proxy=proxy)
    except:
        heapq.heappush(_pqueue, (errs + 1, proxy))
        raise
    else:
        heapq.heappush(_pqueue, (errs, proxy))
        return res


@decorator
def random_useragent(call):
    session = SESSION.get()
    session._cookie_jar.clear()
    ua = UserAgent()
    return call(headers={'User-Agent': ua.random})


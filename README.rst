AioScrape
=========

A scraping library on top of `aiohttp <https://aiohttp.readthedocs.io>`_ and `parsechain <https://github.com/Suor/parsechain>`_. Note that this is **alpha** software.


Installation
-------------

::

    pip install aioscrape


Usage
-----

.. code:: python

    import asyncio
    import aiohttp
    from aioscrape import run, fetch, settings

    from parsechain import C
    from funcy import lcat, lconcat


    def main():
        from aioscrape.utils import SOME_HEADERS
        from aioscrape.middleware import log_fetch, retry, limit, validate
        from aioscrape.middleware import last_fetch, filecache

        middleware = [
            limit(per_domain=5),
            retry(timeout=10, on_error=logger.warning),
            log_fetch(logger.info),
            validate()
        ]
        if DEBUG:
            middleware = [
                filecache('.fcache'),
                last_fetch('last_fetch.html'),
            ] + middleware

        # Settings are scoped and can be redefined later with another "with"
        with settings(
                timeout=aiohttp.ClientTimeout(total=30),
                headers=SOME_HEADERS,  # To not look like a bot
                middleware=middleware,
                ):
            print(run(scrape_all()))


    async def scrape_all():
        # All the settings in scope like headers and middleware are applied to fetch()
        start_page = await fetch(START_URL)

        # AioScrape integrates with parsechain to make extracting a breeze
        list_urls = start_page.css('.pagingLinks a') \
                              .attrs('href').map(start_page.abs)

        # Using asyncio.gather() and friends to run requests in parallel
        list_pages = [start_page] + await amap(fetch, list_urls)

        # Scrape articles, this won't start a horde of parallel requests
        # because of limit() middleware
        result = lcat(await amap(scrape_articles, list_pages))
        write_to_csv('export.csv', result)


    async def scrape_articles(list_page):
        urls = list_page.css('#headlines .titleLink').attrs('href')
        abs_urls = urls.map(list_page.abs)
        return await amap(scrape_article, abs_urls)


    async def scrape_article(url):
        resp = await fetch(url)
        return resp.root.multi({
            'url': C.const(resp.url),
            'title': C.microdata('headline').first,
            'date': C.microdata('datePublished').first,
            'text': C.microdata('articleBody').first,
            'contacts': C.css('.sidebars .contact p')
                         .map(C.inner_html.html_to_text) + lconcat + ''.join,
        })


    def amap(func, seq):
        return asyncio.gather(*map(func, seq))

    if __name__ == '__main__':
        main()


TODO
----

- non-GET requests
- work with forms
- add aio utils?
    - amap()
    - as_completed()

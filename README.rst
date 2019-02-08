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

    from aioscrape import run, fetch, settings
    from aioscrape.middleware import last_fetch, make_filecache
    from aioscrape.utils import SOME_HEADERS # To not look like a bot

    from urllib.parse import urljoin
    from parsechain import C
    from funcy import lcat, lconcat


    def main():
        # Settings are scoped and can be redefined later with another "with"
        cache = make_filecache('.fcache')
        with settings(headers=SOME_HEADERS, middleware=[cache, last_fetch]):
            print(run(scrape_all()))


    async def scrape_all():
        # All the settings in scope like headers and middleware are applied to fetch()
        start_page = await fetch(START_URL)

        # AioScrape integrates with parsechain to make extracting a breeze
        urls = start_page.css('.pagingLinks a').attrs('href')
        list_urls = [urljoin(start_page.url, page_url) for page_url in urls]

        # Using asyncio.wait() and friends to run requests in parallel
        list_pages = [start_page] + await wait_all(map(fetch, list_urls))

        # Scrape articles
        result = lcat(await wait_all(map(scrape_articles, list_pages)))
        write_to_csv('export.csv', result)


    async def scrape_articles(list_page):
        urls = list_page.css('#headlines .titleLink').attrs('href')
        abs_urls = [urljoin(list_page.url, url) for url in urls]
        return await wait_all(map(scrape_article, abs_urls))


    async def scrape_article(url):
        resp = await fetch(url)
        return resp.root.multi({
            'url': C.const(resp.url),
            'title': C.microdata('headline').first,
            'date': C.microdata('datePublished').first,
            'text': C.microdata('articleBody').first,
            'contacts': C.css('.sidebars .contact p')
                         .map(C.inner_html + html_to_text) + lconcat + ''.join,
        })


    if __name__ == '__main__':
        main()


TODO
----

- Response.follow()
- Response.abs()
- non-GET requests
- work with forms

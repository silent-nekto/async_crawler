import aiohttp
import asyncio
import aiofiles.os
import aiofiles.ospath
import os
import json
from bs4 import BeautifulSoup
from hashlib import md5
import argparse


ROOT_URL = 'https://news.ycombinator.com/'

class News:
    def __init__(self, out):
        self.items = {}
        self.out = out

    async def parse(self):
        async with aiohttp.ClientSession() as session:
            tasks = []
            async with session.get(ROOT_URL) as response:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                # news = soup.find_all('span', {'class': 'titleline'})
                tr_news = soup.find_all('tr', {'class': 'athing submission'})
                print(f'{tr_news=}')
                for item in tr_news:
                    main_link = item.find('span', {'class': 'titleline'}, recursive=True).find('a', recursive=False)
                    if main_link:
                        links = item.find_next_sibling('tr').find_all('a', recursive=True)
                        comments = None
                        for lnk in links:
                            if 'comments' in lnk.text:
                                print(lnk.text)
                                comments = lnk.get('href')

                        tasks.append(self.add(main_link.text, main_link.get('href'), comments))

                await asyncio.gather(*tasks)

    async def add(self, title, link, comments):
        h = md5(title.encode('utf-8'))
        if h in self.items:
            return
        print(f'News found: {title} ({comments=})')
        hex_name = str(h.hexdigest())
        self.items[hex_name] = {
            'title': title,
            'link': link,
            'comments': comments
        }
        await self._download(hex_name)
        return f'Complete {title}'

    async def _download(self, name):
        item = self.items[name]
        async with aiohttp.ClientSession() as session:
            dir_name = os.path.join(self.out, name)
            if not await aiofiles.ospath.isdir(dir_name):
                await aiofiles.os.makedirs(dir_name, exist_ok=True)
            url = item['link']
            url = url if url.startswith('http') else ROOT_URL + url
            try:
                async with session.get(url) as response:
                    async with aiofiles.open(os.path.join(dir_name, 'readme'), mode='w') as f:
                        await f.write(json.dumps(item, indent='  '))
                    async with aiofiles.open(os.path.join(dir_name, 'main.html'), mode='wb') as f:
                        async for chunk in response.content.iter_chunked(8192):  # 8192 bytes per chunk
                            await f.write(chunk)
            except Exception as e:
                print(f'Failed to process {url}. {e}')

    async def _parse_comments(self, session, url):
        async with session.get(url) as response:
            async with aiofiles.open(os.path.join(dir_name, 'main.html'), mode='w', encoding='utf-8') as f:
                await f.write(await response.text())

    def __str__(self):
        result = []
        for key in self.items:
            result.append(f'{key}: {self.items[key]}')
        return '\n'.join(result)


async def crawl(options):
    if not await aiofiles.ospath.isdir(options.out):
        await aiofiles.os.makedirs(options.out, exist_ok=True)
    news_collector = News(options.out)
    await news_collector.parse()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--period', required=True)
    options = parser.parse_args()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(crawl(options))


if __name__ == '__main__':
    main()

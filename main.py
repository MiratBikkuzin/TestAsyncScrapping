import asyncio
import aiohttp
import requests
from fake_headers import Headers
from aiohttp_retry import RetryClient, ExponentialRetry
from bs4 import BeautifulSoup as BS
from time import perf_counter


class Parser(object):

    def __new__(cls, *args) -> object:
        return super().__new__(cls, *args)

    def __init__(self, domain: str) -> None:
        self.domain: str = domain
        self.categories: list = []
        self.links: list = []
        self.total_pages: int = 0
        self.products_on_one_page: int = 0
        self.headers: Headers = Headers(True)
        self.result: int = 0

    @staticmethod
    def get_soup(url: str) -> BS:
        html_code: str = requests.get(url).text
        return BS(html_code, 'lxml')

    def get_all_categories(self, soup: BS) -> None:
        self.categories.extend([ctgy['id'] for ctgy in soup.find(
            'div', class_='nav_menu').find_all('div')])

    def get_total_pages(self, soup: BS) -> None:
        self.total_pages: int = int(
            soup.find('div', class_='pagen').find_all('a')[-1].text)

    def get_products_on_one_page(self, soup: BS) -> None:
        self.products_on_one_page: int = len(
            soup.find_all('div', class_='item'))

    def get_all_links(self, categories: list[str], total_pages: int, products_on_one_page: int) -> None:
        for cn in range(1, len(categories) + 1):
            for product_num in range(1, total_pages * products_on_one_page + 1):
                self.links.append(
                    self.domain + f'{categories[cn - 1]}/{cn}/{cn}_{product_num}.html')

    async def get_result(self, session: RetryClient, product_link: str):
        async with session.get(url=product_link, raise_for_status=False, headers=self.headers.generate()) as response:
            soup: BS = BS(await response.text(), 'lxml')
            old_price: int = int(
                soup.find('span', id='old_price').text.split()[0])
            current_price: int = int(
                soup.find('span', id='price').text.split()[0])
            stock: int = int(
                soup.find('span', id='in_stock').text.split(':')[-1].strip())
            self.result: int = self.result + \
                ((old_price - current_price) * stock)

    async def main(self):
        async with aiohttp.ClientSession(trust_env=True) as session:
            retry_options: ExponentialRetry = ExponentialRetry(
                attempts=10, start_timeout=0.5, factor=3)
            retry_client: RetryClient = RetryClient(
                session, retry_options=retry_options)
            await asyncio.gather(*(self.get_result(retry_client, link) for link in self.links))

    def __call__(self, url: str):
        soup: BS = self.get_soup(url)
        self.get_all_categories(soup)
        self.get_total_pages(soup)
        self.get_products_on_one_page(soup)
        self.get_all_links(self.categories, self.total_pages,
                           self.products_on_one_page)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(self.main())


if __name__ == '__main__':
    first_time = perf_counter()
    parser: Parser = Parser(domain='https://parsinger.ru/html/')
    parser('https://parsinger.ru/html/index1_page_1.html')
    print(parser.result)
    print(perf_counter() - first_time)

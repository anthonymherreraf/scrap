import requests
from lxml.html import fromstring
from multiprocessing.pool import ThreadPool
from datetime import datetime
import pymongo
import threading

class Mercadolibre:
    def __init__(self):
        self.client = pymongo.MongoClient()
        self.db = self.client.vehicles
        self.collction = self.db.mercadolibre
        self.db_insert_lock = threading.Lock()

        url = 'https://vehiculos.mercadolibre.com.ec/'
        pag_url = 'https://vehiculos.mercadolibre.com.ec/_Desde_{}'.format
        res = requests.get(url)
        response = fromstring(res.text)
        try:
            results_num = int(response.xpath('//p[@class="page"]/strong/text()')[0])
        except:
            results_num = int(response.xpath('//div[@class="quantity-results"]/text()')[0].strip().split(' ')[0].replace('.', ''))
        self.paganation_links = [pag_url(i) for i in range(1,results_num,48)]

    def get_links(self, url):
        res = requests.get(url)
        response = fromstring(res.text)
        links = response.xpath('//li[@class="results-item article grid "]/div/a/@href')
        if not links:
            links = response.xpath('//h2[@class="list-view-item-title"]/a/@href')
        return links

    def get_fields(self, url):
        try:
            res = requests.get(url)
            response = fromstring(res.text)
            row = {}
            row['source'] = 'mercadolibre'
            row['date'] = datetime.today()
            row['url'] = res.url
            row['title'] = response.xpath('//h1/text()')[0]
            row['price'] = int(response.xpath('//article[contains(@class, "price")]/strong/text()')[0].split()[-1].replace('.', ''))
            all_other_divs = response.xpath('//div[@class="card-section"]/dl')
            for div in all_other_divs:
                key = div.xpath('./dt/text()')[0].strip().strip(':').replace('.', '')
                value = div.xpath('./dd/text()')[0].strip()       
                row[key] = value
                
            with self.db_insert_lock:
                self.collction.insert_one(row)
        except:
            print(url)
    def scrap(self):  
        pool = ThreadPool(32)
        total_links = set()
        print('Collecting Mercadolibre Links')
        for links in pool.imap(self.get_links, self.paganation_links):
            total_links |= set(links)

        total_links = list(total_links)
        len_total_links = len(total_links)
        print('Scraping Mercadolibre Links')
        for r, row in enumerate(pool.imap(self.get_fields, total_links)):
            if r%200==0:
                print('{} out of {}'.format(r, len_total_links))

if __name__ == '__main__':
    scraper = Mercadolibre()
    scraper.scrap()

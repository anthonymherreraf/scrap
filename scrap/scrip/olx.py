import requests
from lxml.html import fromstring
from multiprocessing.pool import ThreadPool
from datetime import datetime
import pymongo
import threading

class Olx:

    def __init__(self):
        self.client = pymongo.MongoClient()
        self.db = self.client.vehicles
        self.collction = self.db.olx
        self.db_insert_lock = threading.Lock()

        url = 'https://www.olx.com.ec/coches-cat-378'
        pag_url = 'https://www.olx.com.ec/coches-cat-378-p-{}'.format
        res = requests.get(url)
        response = fromstring(res.text)
        pages_num = int(response.xpath('//div[@class="breadcrumb-pagination"]/p/text()')[0].split()[-1].strip().replace('.',''))
        self.paganation_links = [pag_url(i) for i in range(1,pages_num+1)]
        
    def get_links(self, url):
        res = requests.get(url)
        response = fromstring(res.content)
        links = response.xpath('//ul[@class="items-list "]/li/a/@href')
        links = ['https:'+l for l in links]
        return links

    def get_fields(self, url):
        row = {}
        try:
            res = requests.get(url, timeout=10)
            response = fromstring(res.content)        
            row['source'] = 'olx'
            row['date'] = datetime.today()
            row['url'] = res.url
            row['title'] = response.xpath('//h1/text()')[0].strip()
            row['price'] = int(response.xpath('//strong[@class="price"]/text()')[0].strip().strip('$').replace('.', ''))
            all_other_divs = response.xpath('//ul[@class="item_partials_optionals_view compact"]/li')
            for div in all_other_divs:
                key = div.xpath('./strong/text()')[0].strip().strip(':')
                value = div.xpath('./span/text()')[0].strip()       
                row[key] = value

            if not row.get('Marca'):
                row['Marca'] = row.get('Marca / Modelo').strip().split(' ')[0]
                row['Modelo'] = ' '.join(row.get('Marca / Modelo').strip().split(' ')[1:])                

            if not row.get('Año'):
                try:
                    row['Año'] = row.get('Año / Condición').strip().split(' ')[0]
                except:
                    pass
                
            with self.db_insert_lock:
                self.collction.insert_one(row)
        except:
            pass

    def scrap(self):
        pool = ThreadPool(32)
        
        print('Collecting Olx Links')        
        total_links = set()
        for links in pool.imap(self.get_links, self.paganation_links):
            total_links |= set(links)
            
        total_links = list(total_links)
        len_total_links = len(total_links)
        print('Scraping Olx Links')
        for r, row in enumerate(pool.imap(self.get_fields, total_links)):
            if r%200==0:
                print('{} out of {}'.format(r, len_total_links))

if __name__ == '__main__':
    scraper = Olx()
    scraper.scrap()
    
    

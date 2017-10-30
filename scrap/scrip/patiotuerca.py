import requests
from lxml.html import fromstring
from multiprocessing.pool import ThreadPool
from datetime import datetime
import pymongo
import threading



def get_field(text):
    if text:
        return text[0].strip()
    return ''

class Patiotuerca:
    threads = 16
    def __init__(self):
        self.client = pymongo.MongoClient()
        self.db = self.client.vehicles
        self.collction = self.db.patiotuerca
        self.db_insert_lock = threading.Lock()

        url = 'https://ecuador.patiotuerca.com/usados/-/autos?fts=vehicle'
        self.paganation_url = 'https://ecuador.patiotuerca.com/usados/-/autos?fts=vehicle&page={}'.format
        self.base_url = 'https://ecuador.patiotuerca.com'
        self.page_numbers = range(0, 10000)
        self.stop_counter = 0
        
    def get_links(self, page_number):
        if self.stop_counter>self.threads:
            return []
        res = requests.get(self.paganation_url(page_number))
        response = fromstring(res.text)
        links = set(response.xpath('//a[@class="vehicle-href"]/@href'))
        links = [self.base_url+l for l in links]
        if not links:        
            self.stop_counter += 1
        return links

    def get_fields(self, url):
        res = requests.get(url)
        response = fromstring(res.text)
        row = {}
        row['source'] = 'patiotuerca'
        row['date'] = datetime.today()
        row['url'] = res.url
        row['title'] = response.xpath('//h1/text()')[0]
        row['price'] = int(response.xpath('//h1/text()')[1].strip().strip('$').replace('.', ''))
        
        summary_divs = response.xpath('//section[@id="summary"]/div/div')
        for div in summary_divs:        
            key = get_field(div.xpath('./*/text()')).strip()
            value = div.xpath('./text()')
            if len(value) > 1:
                value = value[1].strip()
            else:
                value = ''
            row[key] = value
            
        technicaldata_divs = response.xpath('//section[@id="technicalData"]/div/p')
        for div in technicaldata_divs:
            key = get_field(div.xpath('./small/text()'))
            value = get_field(div.xpath('./span/text()'))
            row[key] = value
            
        with self.db_insert_lock:
                    self.collction.insert_one(row)

    def scrap(self):
        
        pool = ThreadPool(self.threads)
        
        print('Collecting Patiotuerca Links')        
        total_links = set()
        for links in pool.imap(self.get_links, self.page_numbers):
            total_links |= set(links)
            
        total_links = list(total_links)
        len_total_links = len(total_links)        
        print('Scraping Patiotuerca Links')
        for r, row in enumerate(pool.imap(self.get_fields, total_links)): 
            if r%200==0:
                print('{} out of {}'.format(r, len_total_links))

if __name__ == '__main__':
    scraper = Patiotuerca()
    scraper.scrap()

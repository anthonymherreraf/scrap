import requests
from lxml.html import fromstring
from multiprocessing.pool import ThreadPool
from datetime import datetime
import pymongo
import threading

def get_field(text):
    if text:
        return text[0]
    return ''

class Patiodeautos:
    def __init__(self):
        self.client = pymongo.MongoClient()
        self.db = self.client.vehicles
        self.collction = self.db.patiodeautos
        self.db_insert_lock = threading.Lock()

        url = 'http://patiodeautos.com/vehiculos'
        res = requests.get(url)
        response = fromstring(res.text)
        self.paganation_url = 'http://patiodeautos.com/vehiculos?page={}&cantidad=100&precio_desde=-&precio_hasta=-'.format
        self.base_url = 'http://patiodeautos.com'
        last_page = int(int(response.xpath('//h1/text()')[0].strip().strip('(').split(')')[0])/100)+1
        self.pages = range(1, last_page+1)
        
    def get_links(self, page_number):
        res = requests.get(self.paganation_url(page_number))
        response = fromstring(res.text)
        links = response.xpath('//div[@class="col-8"]/div[@class="content"]/a')    
        rows = []
        for l, link in enumerate(links):
            row = {}
            row['source'] = 'patiodeautos'
            row['url'] = self.base_url + get_field(link.xpath('./@href'))        
            row['Marca'] = get_field(link.xpath('div/div[1]/div/h3/text()'))
            row['Modelo'] = get_field(link.xpath('div/div[2]/div/h3/text()'))
            row['Año'] = get_field(link.xpath('div/div[3]/div/h3/text()'))
            rows.append(row)
        return rows

    def get_fields(self, r):
        row = self.total_rows[r]
        for i in range(3):
            try:
                res = requests.get(row['url'], timeout=10)
                if 'Error 404' in res.text:
                    break
                response = fromstring(res.text)
                row['date'] = datetime.today()
                row['title'] = response.xpath('//h2/text()')[0]
                row['price'] = int(response.xpath('//label[@class="price"]/text()')[0].strip().strip('$').replace('.', ''))    
                details_divs = response.xpath('//div[@class="content"]//div[@class="data"]/div[@class="content"]/div[@class="row"]')
                for div in details_divs:
                    div_1, div_2 = div.xpath('./div[1]'), div.xpath('./div[2]')
                    if div_1 and div_2:
                        key = ''.join([d.strip() for d in div_1[0].itertext() if d.strip()]).strip().strip(':')
                        value = ''.join([d.strip() for d in div_2[0].itertext() if d.strip()]).strip()
                        row[key] = value  
                with self.db_insert_lock:
                    self.collction.insert_one(row)
            except:
                pass
    
    def scrap(self):
        threads = 20
        pool = ThreadPool(threads)
        
        print('Collecting Patiodeautos Links')
        self.total_rows = []
        for rows in pool.imap(self.get_links, self.pages):
            self.total_rows += rows

        len_total_rows = len(self.total_rows)
        total_rows_range = list(range(0,len_total_rows))
        print('Scraping Patiodeautos Links')            
        for r, row in enumerate(pool.imap(self.get_fields, total_rows_range)):    
            if r%200==0:
                print('{} out of {}'.format(r, len_total_rows))

if __name__ == '__main__':
    scraper = Patiodeautos()
    scraper.scrap()

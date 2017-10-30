from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
import json

import requests
from lxml.html import fromstring
from multiprocessing.pool import ThreadPool
from datetime import datetime, timedelta, time
import pymongo
import threading

import time

from tkinter import *
from tkinter import ttk
from tkinter import messagebox

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

from django.contrib.auth.decorators import login_required

# Create your views here.

# Clases

def filtro(url, titulo, precio):

    url = url.upper()
    titulo = titulo.upper()

    tienemotourl = url.find("MOTO")
    tienemotorurl = url.find("MOTOR")
    tienebiciurl = url.find("BICI")
    tienebicititulo = titulo.find("BICI")

    
    return (((precio > 3000) or ((tienemotourl != -1) and (precio > 500) and ((tienemotorurl == -1)))) and (tienebiciurl == -1) and (tienebicititulo == -1))
        


class Olx:

    def __init__(self):
        self.client = pymongo.MongoClient()
        self.db = self.client.vehicles2
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
            
            prueba = filtro(row['url'],row['title'],row['price'])

            if (prueba != False):

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


    def getTotalLinks(self):
        pool = ThreadPool(32)
        
        total_links = set()
        for links in pool.imap(self.get_links, self.paganation_links):
            total_links |= set(links)
            
        total_links = list(total_links)
        len_total_links = len(total_links)

        values={
            'len_total_links':len_total_links
        }
        return values


class Mercadolibre:
    def __init__(self):
        self.client = pymongo.MongoClient()
        self.db = self.client.vehicles2
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
            
            prueba = filtro(row['url'],row['title'],row['price'])

            if (prueba != False):
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



    def getTotalLinks(self):
        pool = ThreadPool(32)
        
        total_links = set()
        for links in pool.imap(self.get_links, self.paganation_links):
            total_links |= set(links)
            
        total_links = list(total_links)
        len_total_links = len(total_links)

        values={
            'len_total_links':len_total_links
        }
        return values




def get_field(text):
    if text:
        return text[0]
    return ''

class Patiodeautos:
    def __init__(self):
        self.client = pymongo.MongoClient()
        self.db = self.client.vehicles2
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
                
                prueba = filtro(row['url'],row['title'],row['price'])

                if (prueba != False):

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
        #threads = 32
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


    def getTotalLinks(self):
        threads = 20
        #threads = 32
        pool = ThreadPool(threads)
        
        self.total_rows = []
        for rows in pool.imap(self.get_links, self.pages):
            self.total_rows += rows

        len_total_rows = len(self.total_rows)

        values={
            'len_total_links':len_total_rows
        }
        return values




class Patiotuerca:
    threads = 16
    #threads = 32
    def __init__(self):
        self.client = pymongo.MongoClient()
        self.db = self.client.vehicles2
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
        
        prueba = filtro(row['url'],row['title'],row['price'])

        if (prueba != False):

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


    def getTotalLinks(self):
        pool = ThreadPool(self.threads)
        
        total_links = set()
        for links in pool.imap(self.get_links, self.page_numbers):
            total_links |= set(links)
            
        total_links = list(total_links)
        len_total_links = len(total_links) 

        values={
            'len_total_links':len_total_links
        }
        return values






# def

@login_required
def index(request):
    """
    View function for home page of site.
    """
    # Render the HTML template index.html with the data in the context variable
    return render(
        request,
        'scrap/index.html'
    )

@login_required
def crear_mercadolibre(request):
    """
    scraper.client = pymongo.MongoClient()
    scraper.db = scraper.client.vehicles2

    scraper.collction = scraper.db.mercadolibre
    scraper.db_insert_lock = threading.Lock()

    url = 'https://vehiculos.mercadolibre.com.ec/'
    pag_url = 'https://vehiculos.mercadolibre.com.ec/_Desde_{}'.format
    res = requests.get(url)
    response = fromstring(res.text)
    try:
        results_num = int(response.xpath('//p[@class="page"]/strong/text()')[0])
    except:
        results_num = int(response.xpath('//div[@class="quantity-results"]/text()')[0].strip().split(' ')[0].replace('.', ''))
    scraper.paganation_links = [pag_url(i) for i in range(1,results_num,48)]
    scraper.scrap()
    """
    #scraper = Mercadolibre()
    #scrap(scraper)
    #exec(open('/scrap/scrip/mercadolibre.py').read())
    scraper = Mercadolibre()
    scraper.scrap()
    #return render(request,'scrap/index.html')
    values={
        'situacion':'ok'
    }

    #return HttpResponseRedirect('/')
    #return values  
    return HttpResponse(json.dumps(values), content_type='application/json')  



def get_links_mercadolibre(request):
    print(request)
    if request.user.is_authenticated():
        scraper = Mercadolibre()
        values = scraper.getTotalLinks()
        return HttpResponse(json.dumps(values), content_type='application/json')
    else:
        jsonr = json.dumps({ 'authenticated': False })
        return HttpResponse(json.dumps(jsonr), content_type='application/json')


@login_required
def crear_olx(request):
    scraper = Olx()
    scraper.scrap()
    #return render(request,'scrap/index.html')
    values={
        'situacion':'ok'
    }
    #return values 
    return HttpResponse(json.dumps(values), content_type='application/json')  


def get_links_olx(request):

    print(request)
    if request.user.is_authenticated():
        scraper = Olx()
        values = scraper.getTotalLinks()
        return HttpResponse(json.dumps(values), content_type='application/json')
    else:
        jsonr = json.dumps({ 'authenticated': False })
        return HttpResponse(json.dumps(jsonr), content_type='application/json')





@login_required
def crear_patiodeautos(request):
    scraper = Patiodeautos()
    scraper.scrap()
    #return render(request,'scrap/index.html')
    values={
        'situacion':'ok'
    }
    #return values 
    return HttpResponse(json.dumps(values), content_type='application/json') 


def get_links_patiodeautos(request):

    print(request)
    if request.user.is_authenticated():
        scraper = Patiodeautos()
        values = scraper.getTotalLinks()
        return HttpResponse(json.dumps(values), content_type='application/json')
    else:
        jsonr = json.dumps({ 'authenticated': False })
        return HttpResponse(json.dumps(jsonr), content_type='application/json')



@login_required
def crear_patiodetuerca(request):
    scraper = Patiotuerca()
    scraper.scrap()
    #return render(request,'scrap/index.html')
    values={
        'situacion':'ok'
    }
    #return values 
    return HttpResponse(json.dumps(values), content_type='application/json') 


def get_links_patiodetuerca(request):

    print(request)
    if request.user.is_authenticated():
        scraper = Patiotuerca()
        values = scraper.getTotalLinks()
        return HttpResponse(json.dumps(values), content_type='application/json')
    else:
        jsonr = json.dumps({ 'authenticated': False })
        return HttpResponse(json.dumps(jsonr), content_type='application/json')




def ssl(List):
    return sorted(list(set(List)))

def get_first(List):
    if List:
        return List[0]
    return ''

def get_total_df_and_collections(db, needed_fields):
    collection_names = db.collection_names()  

    dfs = [pd.DataFrame(list(db[n].find())) for n in collection_names]# if n != 'olx']
    #print(dfs)
    collection_names = ['All'] + collection_names
    total_df = pd.concat([df[needed_fields] for df in dfs]).fillna('-')
    total_df = total_df[total_df['price']<200000]
    total_df['Año'] = total_df['Año'].astype(str)
    total_df['Marca'] = total_df['Marca'].apply(lambda x:str(x).upper())    
    return total_df, collection_names

class Application(Frame):
    client = pymongo.MongoClient()
    db = client.vehicles2
    
    needed_fields = ['Marca', 'Modelo', 'Año', 'price', 'date', 'source', 'url']
    fields = ['source', 'Marca', 'Modelo', 'Año', 'url']
    
    df, collection_names = get_total_df_and_collections(db, needed_fields)    
    brands = ssl(df[fields[0]])

    def __init__(self, master=None, Frame=None):
        Frame.__init__(self, master)
        #super(Application,self).__init__()
        #self.createWidgets()     
        #print(self)

    def getUpdateData_Brand(self):
        temp_df = self.df.copy()
        if self.SourceCombo == 'All':
            values_filter = ssl(temp_df['Marca'].astype(str))
        else:        
            values_filter = ssl(temp_df[temp_df['source'] == self.SourceCombo.get()]['Marca'].astype(str))
        #self.BrandCombo['values'] = values_filter
        print(values_filter)
        #self.BrandCombo.set('')
        #self.ModelCombo.set('')
        #self.YearCombo.set('')
        #self.LinkCombo.set('')
        #self.get_average_std()

    def getUpdateData_Brand2(self, SourceCombo):
        temp_df = self.df.copy()
        if SourceCombo == 'All':
            values_filter = ssl(temp_df['Marca'].astype(str))
        else:        
            values_filter = ssl(temp_df[temp_df['source'] == SourceCombo]['Marca'].astype(str))
        #print(values_filter)
        return values_filter


    def getUpdateData_Model(self,  event):
        temp_df = self.df.copy()
        if self.SourceCombo.get() != 'All':
            temp_df =  temp_df[temp_df['source'] == self.SourceCombo.get()]
        values_filter = ssl(temp_df[temp_df['Marca'] == self.BrandCombo.get()]['Modelo'].astype(str))
        self.ModelCombo['values'] = values_filter
        self.ModelCombo.set('')
        self.YearCombo.set('')
        self.LinkCombo.set('')
        self.get_average_std()

    def getUpdateData_Model2(self, SourceCombo, BrandCombo):
        temp_df = self.df.copy()
        if SourceCombo != 'All':
            temp_df =  temp_df[temp_df['source'] == SourceCombo]

        values_filter = ssl(temp_df[temp_df['Marca'] == BrandCombo]['Modelo'].astype(str))
        #print(values_filter)
        return values_filter


    def getUpdateData_Year(self,  event):
        temp_df = self.df.copy()
        if self.SourceCombo.get() != 'All':
            temp_df =  temp_df[temp_df['source'] == self.SourceCombo.get()]
        temp_df =  temp_df[temp_df['Marca'] == self.BrandCombo.get()]  
        values_filter = ssl(temp_df[temp_df['Modelo'] == self.ModelCombo.get()]['Año'])
        self.YearCombo['values'] = values_filter
        self.YearCombo.set('')
        self.LinkCombo.set('')
        self.get_average_std()

    def getUpdateData_Year2(self, SourceCombo, BrandCombo, ModelCombo):
        temp_df = self.df.copy()
        if SourceCombo != 'All':
            temp_df =  temp_df[temp_df['source'] == SourceCombo]
        temp_df =  temp_df[temp_df['Marca'] == BrandCombo] 
        values_filter = ssl(temp_df[temp_df['Modelo'] == ModelCombo]['Año'])
        #print(values_filter)
        return values_filter


    def getUpdateData_Link(self,  event):
        temp_df = self.df.copy()
        if self.SourceCombo.get() != 'All':
            temp_df =  temp_df[temp_df['source'] == self.SourceCombo.get()]
        temp_df =  temp_df[temp_df['Marca'] == self.BrandCombo.get()]
        temp_df =  temp_df[temp_df['Modelo'] == self.ModelCombo.get()] 
        values_filter = ssl(temp_df[temp_df['Año'] == self.YearCombo.get()]['url'])
        self.LinkCombo['values'] = values_filter
        self.LinkCombo.set('')
        self.get_average_std()

    def getUpdateData_Link2(self, SourceCombo, BrandCombo, ModelCombo, YearCombo):
        temp_df = self.df.copy()
        if SourceCombo != 'All':
            temp_df =  temp_df[temp_df['source'] == SourceCombo]
        temp_df =  temp_df[temp_df['Marca'] == BrandCombo] 
        temp_df =  temp_df[temp_df['Modelo'] == ModelCombo]
        values_filter = ssl(temp_df[temp_df['Año'] == YearCombo]['url'])
        #print(values_filter)
        return values_filter


    def plot2(self, SourceCombo, BrandCombo, ModelCombo, YearCombo, LinkCombo, IniciofechaCombo, FinfechaCombo):
        source = SourceCombo
        #print(source)
        brand = BrandCombo
        model = ModelCombo
        year = YearCombo
        url = LinkCombo
        values = [source, brand, model, year, url]
        #print(source)
        #print(brand)
        #print(model)
        #print(year)
        #print(url)
        
        plot_df = self.df.copy()
        #print(plot_df)


       
        start_date = IniciofechaCombo
        if start_date:
            start_date = datetime.strptime(start_date, '%d/%m/%Y')
            plot_df = plot_df[plot_df['date']>=start_date]

        end_date = FinfechaCombo
        if end_date:
            end_date = datetime.strptime(end_date, '%d/%m/%Y')
            plot_df = plot_df[plot_df['date']<=end_date]
        


        #print(self.fields)
        #thefields = ['source', 'Marca', 'Modelo', 'Año', 'url']

        #print("los fields: ")
        #print(self.fields)
        #print("los values: ")
        #print(values)
        for field, value in zip(self.fields, values):
            if (field == 'source') and (value == 'All'):
                continue
            if not value:
                continue
            if plot_df.empty:
                break
            plot_df = plot_df[plot_df[field]==value]
            
        #print(plot_df)
        plot_df.sort_values(by='date', inplace=True)
        #x = matplotlib.dates.date2num(plot_df['date'].tolist())
        #print(plot_df['date'])
        #print(datetime(plot_df['date'].tolist()))


        x = (matplotlib.dates.date2num(plot_df['date'].tolist())).tolist()

        #x = plot_df['date'].tolist()
        #x = ['2017-10-05 15:17:16.624']
        #y = plot_df['price']
        y = plot_df['price'].tolist()
        #print("x es: ")
        #print(x)
        #print("y es: ")
        #print(y)

        newx = []
        elementaux = 0
        for fechaplotmat in x:
            elementaux = datetime.fromordinal(int(fechaplotmat)) + timedelta(days=fechaplotmat%1)
            #print(elementaux)
            #print("y ahora")
            elementaux = time.mktime(elementaux.timetuple())
            #print(elementaux)
            newx.append(elementaux)


        #print(newx)

        #return x, y
        return newx, y


    def table2(self, SourceCombo, BrandCombo, ModelCombo, YearCombo, LinkCombo, IniciofechaCombo, FinfechaCombo, inicio, fin):
        source = SourceCombo
        #print(source)
        brand = BrandCombo
        model = ModelCombo
        year = YearCombo
        url = LinkCombo
        inicio = int(inicio)
        fin = int(fin)
        values = [source, brand, model, year, url]
        #print(source)
        #print(brand)
        #print(model)
        #print(year)
        #print(url)
        
        plot_df = self.df.copy()
        #print(plot_df)


       
        start_date = IniciofechaCombo
        if start_date:
            start_date = datetime.strptime(start_date, '%d/%m/%Y')
            plot_df = plot_df[plot_df['date']>=start_date]

        end_date = FinfechaCombo
        if end_date:
            end_date = datetime.strptime(end_date, '%d/%m/%Y')
            plot_df = plot_df[plot_df['date']<=end_date]
        


        #print(self.fields)
        #thefields = ['source', 'Marca', 'Modelo', 'Año', 'url']

        #print("los fields: ")
        #print(self.fields)
        #print("los values: ")
        #print(values)
        for field, value in zip(self.fields, values):
            if (field == 'source') and (value == 'All'):
                continue
            if not value:
                continue
            if plot_df.empty:
                break
            plot_df = plot_df[plot_df[field]==value]
            
        #print(plot_df)


        #plot_df.sort_values(by='date', inplace=True)




        plot_df.sort_values(by='price', inplace=True)




        #plot_df.head(n=100)
        #x = matplotlib.dates.date2num(plot_df['date'].tolist())

        #print(plot_df['date'])

        #x = (matplotlib.dates.date2num(plot_df['date'].tolist())).tolist()
        #x = plot_df['date'].tolist()
        #y = plot_df['price']
        total = len(plot_df['source'].tolist())
        """
        col_source = (plot_df['source']).tolist()
        col_brand = (plot_df['Marca']).tolist()
        col_model = (plot_df['Modelo']).tolist()
        col_year = (plot_df['Año']).tolist()
        col_price = (plot_df['price']).tolist()
        col_url = (plot_df['url']).tolist()
        """

        col_source = (plot_df['source'].tolist())[inicio:(fin + 1)]
        col_brand = (plot_df['Marca'].tolist())[inicio:(fin + 1)]
        col_model = (plot_df['Modelo'].tolist())[inicio:(fin + 1)]
        col_year = (plot_df['Año'].tolist())[inicio:(fin + 1)]
        col_price = (plot_df['price'].tolist())[inicio:(fin + 1)]
        col_url = (plot_df['url'].tolist())[inicio:(fin + 1)]


        #print("x es: ")
        #print(x)
        #print("y es: ")
        #print(y)

        values={
            'col_source':col_source,
            'col_brand':col_brand,
            'col_model':col_model,
            'col_year':col_year,
            'col_price':col_price,
            'col_url':col_url,
            'total':total
        }


        return values


    def getUpdateData_Labels(self,  event):
        self.get_average_std()

    def get_average_std(self):
        source = self.SourceCombo.get()
        brand = self.BrandCombo.get()
        model = self.ModelCombo.get()
        year = self.YearCombo.get()
        url = self.LinkCombo.get()
        values = [source, brand, model, year, url]
        temp_df = self.df.copy()

        start_date = self.Start.get()
        if start_date:
            start_date = datetime.strptime(start_date, '%d/%m/%Y')
            temp_df = temp_df[temp_df['date']>=start_date]

        end_date = self.End.get()
        if end_date:
            end_date = datetime.strptime(end_date, '%d/%m/%Y')
            temp_df = temp_df[temp_df['date']<=end_date]
            
        for field, value in zip(self.fields, values):
            if (field == 'source') and (value == 'All'):
                continue
            if not value:
                continue
            if temp_df.empty:
                break
            temp_df = temp_df[temp_df[field]==value]
            
        average = temp_df['price'].mean()
        std = temp_df['price'].std()

        try:
            self.average_label['text'] = int(average)
        except:
            self.average_label['text'] = ''
        try:
            self.std_label['text'] = int(std)
        except:
            self.std_label['text'] = ''
        


    def get_average_std2(self, SourceCombo, BrandCombo, ModelCombo, YearCombo, LinkCombo, IniciofechaCombo, FinfechaCombo):
        source = SourceCombo
        #print(source)
        brand = BrandCombo
        model = ModelCombo
        year = YearCombo
        url = LinkCombo
        values = [source, brand, model, year, url]
        #print(source)
        #print(brand)
        #print(model)
        #print(year)
        #print(url)
        
        temp_df = self.df.copy()
        #print(temp_df)


       
        start_date = IniciofechaCombo
        if start_date:
            start_date = datetime.strptime(start_date, '%d/%m/%Y')
            temp_df = temp_df[temp_df['date']>=start_date]

        end_date = FinfechaCombo
        if end_date:
            end_date = datetime.strptime(end_date, '%d/%m/%Y')
            temp_df = temp_df[temp_df['date']<=end_date]
        


        #print(self.fields)
        #thefields = ['source', 'Marca', 'Modelo', 'Año', 'url']

        #print("los fields: ")
        #print(self.fields)
        #print("los values: ")
        #print(values)
        for field, value in zip(self.fields, values):
            if (field == 'source') and (value == 'All'):
                continue
            if not value:
                continue
            if temp_df.empty:
                break
            temp_df = temp_df[temp_df[field]==value]
            


        average = temp_df['price'].mean()
        std = temp_df['price'].std()

        try:
            average_label = int(average)
        except:
            average_label = ''
        try:
            std_label = int(std)
        except:
            std_label = ''



        values={
            'average_label':average_label,
            'std_label':std_label
        }


        return values


@login_required
def presentacion(request):
    app = Application()
    #app.SourceCombo = 'All'
    sources = ssl(app.df['source'].astype(str))
    #brands = app.getUpdateData_Brand2('patiotuerca')
    values={
        'sources':sources
    }
    return render(request, 'scrap/presentacion.html',values)
    #return HttpResponseRedirect('/')
    #return HttpResponseRedirect('scrap/presentacion.html')
    #return render(request,'scrap/presentacion.html',app)
    #return get_template('scrap/presentacion.html').render(app)
    #return render_to_string('scrap/presentacion.html', app)

@login_required
def tablas(request):
    app = Application()
    #app.SourceCombo = 'All'
    sources = ssl(app.df['source'].astype(str))
    #brands = app.getUpdateData_Brand2('patiotuerca')
    values={
        'sources':sources
    }
    return render(request, 'scrap/tablas.html',values)


def get_brand(request, nombre_source):
    #print(nombre_source)
    app = Application()
    brands = app.getUpdateData_Brand2(nombre_source)

    list_brands = {}
    list_brands[0] = " "
    i = 1
    for brand in brands:
        #print(brand)
        list_brands[i] = brand
        i += 1
    return HttpResponse(json.dumps(list_brands))



def get_model(request, nombre_source, nombre_brand):
    #print(nombre_brand)
    app = Application()
    models = app.getUpdateData_Model2(nombre_source, nombre_brand)

    list_models = {}
    list_models[0] = " "
    i = 1
    for model in models:
        #print(model)
        list_models[i] = model
        i += 1
    return HttpResponse(json.dumps(list_models))


def get_year(request, nombre_source, nombre_brand, nombre_model):
    #print(nombre_model)
    app = Application()
    years = app.getUpdateData_Year2(nombre_source, nombre_brand, nombre_model)

    list_years = {}
    list_years[0] = " "
    i = 1
    for year in years:
        #print(year)
        list_years[i] = year
        i += 1
    return HttpResponse(json.dumps(list_years))


def get_link(request, nombre_source, nombre_brand, nombre_model, nombre_year):
    #print(nombre_year)
    app = Application()
    links = app.getUpdateData_Link2(nombre_source, nombre_brand, nombre_model, nombre_year)

    list_links = {}
    list_links[0] = " "
    i = 1
    for link in links:
        #print(year)
        list_links[i] = link
        i += 1
    return HttpResponse(json.dumps(list_links))


def get_plot(request):
    if request.is_ajax():
        nombre_source = request.GET.get('nombre_source')
        nombre_brand = request.GET.get('nombre_brand')
        nombre_model = request.GET.get('nombre_model')
        nombre_year = request.GET.get('nombre_year')
        nombre_link = request.GET.get('nombre_link')
        nombre_iniciofecha = request.GET.get('nombre_iniciofecha')
        nombre_finfecha = request.GET.get('nombre_finfecha')
        if nombre_source == " ":
            nombre_source = ""
        if nombre_brand == " ":
            nombre_brand = ""
        if nombre_model == " ":
            nombre_model = ""
        if nombre_year == " ":
            nombre_year = ""
        if nombre_link == " ":
            nombre_link = "" 
        if nombre_iniciofecha == " ":
            nombre_iniciofecha = ""
        if nombre_finfecha == " ":
            nombre_finfecha = ""                                   
        #print("veamos")
        #print(data)

        """
        values={
            'nombre_source':nombre_source,
            'nombre_brand':nombre_brand,
            'nombre_model':nombre_model,
            'nombre_year':nombre_year,
            'nombre_link':nombre_link
        }
        """
    

        app = Application()
        ejex, ejey = app.plot2(nombre_source, nombre_brand, nombre_model, nombre_year, nombre_link, nombre_iniciofecha, nombre_finfecha)

        #print("en el eje x: ")
        #print(ejex)
        #print("en el eje y: ")
        #print(ejey)

        values={
            'ejex':ejex,
            'ejey':ejey,
        }

        return HttpResponse(json.dumps(values), content_type='application/json')


def get_table(request):
    if request.is_ajax():
        nombre_source = request.GET.get('nombre_source')
        nombre_brand = request.GET.get('nombre_brand')
        nombre_model = request.GET.get('nombre_model')
        nombre_year = request.GET.get('nombre_year')
        nombre_link = request.GET.get('nombre_link')
        nombre_iniciofecha = request.GET.get('nombre_iniciofecha')
        nombre_finfecha = request.GET.get('nombre_finfecha')
        inicio = request.GET.get('inicio')
        fin = request.GET.get('fin')
        if nombre_source == " ":
            nombre_source = ""
        if nombre_brand == " ":
            nombre_brand = ""
        if nombre_model == " ":
            nombre_model = ""
        if nombre_year == " ":
            nombre_year = ""
        if nombre_link == " ":
            nombre_link = "" 
        if nombre_iniciofecha == " ":
            nombre_iniciofecha = ""
        if nombre_finfecha == " ":
            nombre_finfecha = ""                                   
        #print("veamos")
        #print(data)

        """
        values={
            'nombre_source':nombre_source,
            'nombre_brand':nombre_brand,
            'nombre_model':nombre_model,
            'nombre_year':nombre_year,
            'nombre_link':nombre_link
        }
        """
    

        app = Application()
        values = app.table2(nombre_source, nombre_brand, nombre_model, nombre_year, nombre_link, nombre_iniciofecha, nombre_finfecha, inicio, fin)

        #print("en el eje x: ")
        #print(ejex)
        #print("en el eje y: ")
        #print(ejey)



        return HttpResponse(json.dumps(values), content_type='application/json')



def get_average(request):
    if request.is_ajax():
        nombre_source = request.GET.get('nombre_source')
        nombre_brand = request.GET.get('nombre_brand')
        nombre_model = request.GET.get('nombre_model')
        nombre_year = request.GET.get('nombre_year')
        nombre_link = request.GET.get('nombre_link')
        nombre_iniciofecha = request.GET.get('nombre_iniciofecha')
        nombre_finfecha = request.GET.get('nombre_finfecha')
        if nombre_source == " ":
            nombre_source = ""
        if nombre_brand == " ":
            nombre_brand = ""
        if nombre_model == " ":
            nombre_model = ""
        if nombre_year == " ":
            nombre_year = ""
        if nombre_link == " ":
            nombre_link = "" 
        if nombre_iniciofecha == " ":
            nombre_iniciofecha = ""
        if nombre_finfecha == " ":
            nombre_finfecha = ""                                   

    

        app = Application()
        values = app.get_average_std2(nombre_source, nombre_brand, nombre_model, nombre_year, nombre_link, nombre_iniciofecha, nombre_finfecha)


        return HttpResponse(json.dumps(values), content_type='application/json')

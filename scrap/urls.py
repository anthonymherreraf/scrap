from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^presentacion/', views.presentacion, name='presentacion'),
    url(r'^tablas/', views.tablas, name='tablas'),
    url(r'^crear_mercadolibre/', views.crear_mercadolibre, name='crear_mercadolibre'),
    url(r'^get/links_mercadolibre/$', views.get_links_mercadolibre, name='get_links_mercadolibre'),
    url(r'^crear_olx/', views.crear_olx, name='crear_olx'),
    url(r'^get/links_olx/$', views.get_links_olx, name='get_links_olx'),
    url(r'^crear_patiodeautos/', views.crear_patiodeautos, name='crear_patiodeautos'),
    url(r'^get/links_patiodeautos/$', views.get_links_patiodeautos, name='get_links_patiodeautos'),
    url(r'^crear_patiodetuerca/', views.crear_patiodetuerca, name='crear_patiodetuerca'),
    url(r'^get/links_patiodetuerca/$', views.get_links_patiodetuerca, name='get_links_patiodetuerca'),
    #url(r'^get/brand/(?P<nombre_brand>)/$', views.get_brand, name='get_brand'),
    url(r'^get/brand/(?P<nombre_source>[\w-]+)/$', views.get_brand, name='get_brand'),
    url(r'^get/model/(?P<nombre_source>[\w-]+)/(?P<nombre_brand>[0-9a-zA-Z% ]+)/$', views.get_model, name='get_model'),
    url(r'^get/year/(?P<nombre_source>[\w-]+)/(?P<nombre_brand>[0-9a-zA-Z% ]+)/(?P<nombre_model>[0-9a-zA-Z% ]+)/$', views.get_year, name='get_year'),
    url(r'^get/link/(?P<nombre_source>[\w-]+)/(?P<nombre_brand>[0-9a-zA-Z% ]+)/(?P<nombre_model>[0-9a-zA-Z% ]+)/(?P<nombre_year>[0-9a-zA-Z% ]+)/$', views.get_link, name='get_link'),
    url(r'^get/plot/$', views.get_plot, name='get_plot'),
    url(r'^get/table/$', views.get_table, name='get_table'),
    url(r'^get/average/$', views.get_average, name='get_average'),
]
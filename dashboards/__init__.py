from dashboards.urls import register
from django.utils.module_loading import autodiscover_modules



def get_urlpatterns():
    autodiscover_modules('views')
    return register.get_urlpatterns()



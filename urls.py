from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
#from dashboards.urls import register
from dashboards import get_urlpatterns
from dashboards.views import login,logout,get_user_home


urlpatterns = [
    url(r'^$', get_user_home, name='home'),
    url(r'^login/$', login, name='login'),
    url(r'^logout/$', logout, name='logout'),
    url(r'', include(get_urlpatterns() ) ),
]

urlpatterns += [
    url(r'^admin/login/$', RedirectView.as_view(url='/login/', permanent=True), name='go-to-login'),
    url(r'^admin/logout/$', RedirectView.as_view(url='/logout/', permanent=True),name='go-to-logout' ),
    url(r'^admin/', include(admin.site.urls)),
]

#urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

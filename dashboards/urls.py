from django.conf import urls

# to register the URLs for your API endpoints, decorate the view class with.
class UrlRegister(object):
    
    def __init__(self):
        self.urlpatterns = []
        
    def __call__(self, view):
        p = urls.url(view.url_regex, view.as_view())
        self.urlpatterns.append(p)
        return view
        
    def get_urlpatterns(self):
        return self.urlpatterns
        
register = UrlRegister()




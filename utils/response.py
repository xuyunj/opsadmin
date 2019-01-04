from django.conf import settings
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect,HttpResponse
from authority.shortcuts import get_page_menu
    

class CommonResponse(object):
    """
    When render template, It'll add public data.
    """
    
    @staticmethod
    def _iresult(data, content_type=None ):
        if not content_type:
            content_type = '%s; charset=%s' % (settings.DEFAULT_CONTENT_TYPE,
                                               settings.DEFAULT_CHARSET)
        return HttpResponse(data, content_type )
        
    @staticmethod
    def _iredirect( url ):
        return HttpResponseRedirect(url)
       
    @staticmethod
    def _isimple_response(view, resp = {} ):
        return render_to_response(view, resp )
        
    @staticmethod
    def _isupply_response(request, view, data={}):
        """
        Using this function that you should ensure user has login in.
        Here is the top menu and the left menu.You can adjust the menu tree for page layout.
        """
        
        resp = get_page_menu(request)
        resp['username'] = request.user.username
        resp['logout_url'] = settings.LOGOUT_URL
        resp.update( data )
        return render_to_response(view, resp )


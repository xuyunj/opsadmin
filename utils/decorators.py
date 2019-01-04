from django.conf import settings
from django.http import HttpResponseRedirect,HttpResponseForbidden

    
def login_perm_required(perm_check=True):
    """
    Checks the user is logged in, or else redirecting
    to the log-in page if necessary.
    If perm_check is true, checks whether a user has a particular permission
    enabled, or else given the PermissionDenied exception.
    """
    
    def decorator(view_func):
    
        def wrapped_view(cls, request, *args, **kwargs ):
            request_url = request.path_info
            if request.user.is_authenticated():
                if perm_check and request_url not in request.session[settings.PERMISSION_SESSION_KEY]:
                    return HttpResponseForbidden()
                return view_func(cls, request, *args, **kwargs)
            else:
                return HttpResponseRedirect( settings.LOGIN_URL + '?next=' + request_url )
        return wrapped_view
        
    return decorator

       
    
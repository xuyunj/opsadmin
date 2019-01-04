#coding:utf-8
from django.contrib import auth
from django.conf import settings
from utils.response import CommonResponse
from django.contrib.auth.decorators import login_required
import authority


class ErrorCode(object):
    
    not_user = '不存在的用户，请联系系统管理员'
    is_not_active = '非活动用户，请联系系统管理员'
    username_or_passwd_empty = '用户名或密码不能为空'
      
      
@login_required(login_url=settings.LOGIN_URL)
def get_user_home(request):
    return CommonResponse._isupply_response(request, 'index.html')
    
    
def login(request):
    if 'GET' == request.method:
        next = request.GET.get('next', '/')
        if request.user.is_authenticated():
            return CommonResponse._iredirect( next )
        return CommonResponse._isimple_response('login.html', {'next': next})
        
    username = request.POST.get('username')
    password = request.POST.get('password')
    
    if not username or not password :
        return CommonResponse._isimple_response('login.html', {'error': ErrorCode.username_or_passwd_empty} )
      
    user = auth.authenticate( username=username, password=password )
    if not user:
        return CommonResponse._isimple_response('login.html', {'error': ErrorCode.not_user} )
    if not user.is_active:
        return CommonResponse._isimple_response('login.html', {'error': ErrorCode.is_not_active} )
    auth.login(request, user)
    authority.shortcuts.set_user_permissions(request)
    return CommonResponse._iredirect( request.POST.get('next', '/') )
    

def logout(request):
    next_page = '/login/'
    return auth.views.logout(request, next_page)
        

    
#def serve_404_error(request, *args, **kwargs):
#    """Registered handler for 404. We just return a simple error"""
#    return render("404.html", request, dict(uri=request.build_absolute_uri()))
#
#def serve_500_error(request, *args, **kwargs):
#    """Registered handler for 500. We use the debug view to make debugging easier."""
#    exc_info = sys.exc_info()
#    return render("500.html", request, {'traceback': traceback.extract_tb(exc_info[2])}

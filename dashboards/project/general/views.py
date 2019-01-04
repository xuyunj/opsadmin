#coding:utf-8
import json
from dashboards import urls
from django.views import generic
from django.conf import settings
from utils.response import CommonResponse
from authority.shortcuts import login_perm_required
from .models import Machine


@urls.register
class GmIndex(generic.View, CommonResponse):
    
    url_regex = r'^gm/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        return self._isupply_response(request, 'general/gm_index.html', {})
    

@urls.register    
class GmMachine(generic.View, CommonResponse):

    url_regex = r'^gm/machine/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        machines = Machine.get_machine_list()
        return self._isupply_response(request, 'general/gm_machine_list.html', {'records': machines})
        
        
@urls.register    
class GmMachineAdd(generic.View, CommonResponse):

    url_regex = r'^gm/machine/add/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        machines = Machine.get_machine_list()
        return self._isupply_response(request, 'general/gm_machine_add.html', {'records': machines})
        
    def post(self, request, *args, **kwags):
        return self._iresult( Machine.add_machine(request.POST, request.user.username) )
    
    
@urls.register
class AnsibleData(generic.View):

    url_regex = r'^gm/data/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        return self._iresult("OK")
        
    def post(self, request, *args, **kwargs):
        pass
        
    
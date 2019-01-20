#coding:utf-8
import os
import json
from dashboards import urls
from django.views import generic
from django.conf import settings
from utils.response import CommonResponse
from authority.shortcuts import login_perm_required
from .models import Machine
from dashboards.project.brm.models import App
from utils import path_utils


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
class TimelyRecord(generic.View, CommonResponse):

    url_regex = r'^gm/timelyRecord/$'
    
    def get(self, request, *args, **kwargs):
        finish = 0
        file_content = '...'
        id = request.GET.get('id')
        app = App.objects.get(id=id)
        host = request.GET.get('host')
        record_path = os.path.join(
            settings.COMMAND_TIMELY_RECORD, app.publish_name, str(request.user.id), host )
        if os.path.exists(record_path):
            with open(record_path, 'r') as f:
                file_content = f.read()
                #file_content['']
                if file_content[-6:] == "finish":
                    file_content = file_content[:-6]
                    finish = 1
        return self._iresult( json.dumps({'content': file_content, 'finish': finish }) )
        
    
    def post(self, request, *args, **kwargs):
        uid = request.POST.get('uid')
        name = request.POST.get('name')
        host = request.POST.get('host')
        record_dir = os.path.join(settings.COMMAND_TIMELY_RECORD, name, uid)
        path_utils.ensure_dir( record_dir )
        with open(os.path.join(record_dir, host) , 'a+') as f:
            f.write(request.POST.get('msg'))
            f.flush()
        return self._iresult("OK")
       
        
    
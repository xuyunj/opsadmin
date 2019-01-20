import os
import json
import chardet
from django.conf import settings
from dashboards import urls
from django.views import generic
from django.http import QueryDict
from utils.response import CommonResponse
from authority.shortcuts import login_perm_required
from dashboards.project.general.models import UniUser
from dashboards.executor.models import Task
from .models import App,AppNode,Template,Record
from utils import path_utils



@urls.register
class BrmIndex(generic.View, CommonResponse):

    url_regex = r'^brm/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        return self._iredirect('/brm/list/')
        
 
@urls.register
class BusinessSystem(generic.View, CommonResponse):

    url_regex = r'^brm/list/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        data = {'apps': App.objects.all() }
        return self._isupply_response(request, 'brm/brm_list.html', data)


@urls.register
class BusinessMachine(generic.View, CommonResponse):

    url_regex = r'^brm/machine/$'
    
    def get(self, request, *args, **kwargs):
        ssh_username = request.GET.get('ssh_username')
        machines = UniUser.get_user_machins(ssh_username)
        machines = [ (machine.ssh_machine.id, machine.ssh_machine.ssh_ip) for machine in machines ]
        return self._iresult(json.dumps(machines))
        
        
@urls.register
class BusinessAdd(generic.View, CommonResponse):

    url_regex = r'^brm/add/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        publish_types = Template.get_template()
        publish_users = UniUser.get_all_users()
        data = {'publish_types': publish_types, 'publish_users': publish_users}
        return self._isupply_response(request, 'brm/brm_add.html', data )
       
    @login_perm_required(perm_check=True)
    def post(self, request, *args, **kwargs):
        nodes = []
        obj = App.objects.create(
            publish_name = request.POST.get('publish_name'),
            publish_alias = request.POST.get('publish_alias'),
            publish_type = Template.objects.get(id=request.POST.get('publish_type')),
            publish_user = request.POST.get('publish_user'),
            publish_path = request.POST.get('publish_path'),
            publish_scmurl = request.POST.get('publish_scmurl'),
            created_by = request.user.username,
        )
    
        publish_machine = request.POST.get('publish_machine', [] )
        for id in publish_machine.split(','):
            if not id: continue
            nodes.append( AppNode(app=obj, machine_id=id) )
        obj.publish_num = len(nodes)
        AppNode.objects.bulk_create( nodes )
        obj.save()
        return self._iredirect("/brm/list/")

        
@urls.register
class BusinessUpdate(generic.View, CommonResponse):

    url_regex = r'^brm/update/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        id = request.GET.get('id')
        app = App.objects.get(id=id)
        publish_types = Template.get_template()
        publish_users = UniUser.get_all_users()
        
        source_nodes = []
        target_nodes = AppNode.objects.filter(app = app)
        machines = UniUser.get_user_machins(app.publish_user)
        for machine in machines:
            if machine.ssh_machine.id in [ node.machine.id for node in target_nodes]:
                continue
            source_nodes.append(machine)
        
        data = {'publish_types': publish_types, 
            'publish_users': publish_users, 
            'app': app, 'source_nodes': source_nodes, 'target_nodes': target_nodes}
        return self._isupply_response(request, 'brm/brm_update.html', data )
       
    @login_perm_required(perm_check=True)
    def post(self, request, *args, **kwargs):
        nodes = []
        publish_name = request.POST.get('publish_name')
        if not App.objects.filter(publish_name=publish_name).exists():
            pass
        else:
            obj = App.objects.get(publish_name=publish_name)
            obj.publish_type = Template.objects.get(id=request.POST.get('publish_type'))
            obj.publish_user = request.POST.get('publish_user')
            obj.publish_path = request.POST.get('publish_path')
            obj.publish_scmurl = request.POST.get('publish_scmurl')
            obj.created_by = request.user.username
 
            publish_machine = request.POST.get('publish_machine', [] )
            AppNode.objects.filter(app=obj).delete()
            for id in publish_machine.split(','):
                if not id: continue
                nodes.append( AppNode(app=obj, machine_id=id) )
            obj.publish_num = len(nodes)
            AppNode.objects.bulk_create( nodes )
            obj.save()
        return self._iredirect("/brm/list/")
      
      
@urls.register
class BusinessDelete(generic.View, CommonResponse):

    url_regex = r'^brm/delete/$'

    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        id = request.GET.get('id')
        App.objects.get(id=id).delete()
        return self._iredirect("/brm/list/")
        
        
@urls.register
class BusinessRelease(generic.View, CommonResponse):

    url_regex = r'^brm/release/$'
    
    @login_perm_required(perm_check=True)
    def post(self, request, *args, **kwargs):
        uuid = request.POST.get('uuid')
        appid = request.POST.get('appid')
        notice =  request.POST.getlist('notice')
        Task.objects.create(
            route_key = "RELEASE",
            json_data = json.dumps({
                'appid': appid, 
                'websocketid': uuid, 'username':request.user.username })
        )
        return self._iresult( json.dumps({'code': 1}) )
        
        
@urls.register
class BusinessRecord(generic.View, CommonResponse):

    url_regex = r'^brm/record/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        id = request.GET.get('id')
        records = Record.objects.filter(app_id = id )
        data = {'records': Record.objects.all() }
        return self._isupply_response(request, 'brm/brm_record.html', data )
        

@urls.register
class BrmConfigure(generic.View, CommonResponse):

    url_regex = r'^brm/configure/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        id = request.GET.get('id')
        app = App.objects.get(id=id)
        target_nodes = AppNode.objects.filter(app = app)
        data = {'name': app.publish_name, 'target_nodes': target_nodes}
        return self._isupply_response(request, 'brm/brm_configure.html', data )
        

@urls.register
class BrmConfigureFiles(generic.View, CommonResponse):

    url_regex = r'^brm/configure/files/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        id = request.GET.get('id')
        host = request.GET.get('host')
        app = App.objects.get(id=id)
        result = app.publish_type.get_profiles( host, app.publish_user  )
        return self._iresult( json.dumps(result) )
    
    @login_perm_required(perm_check=True)
    def post(self, request, *args, **kwargs):
        extvar = dict()
        id = request.POST.get('id')
        app = App.objects.get(id=id)
        extvar['user'] = app.publish_user
        extvar['host'] = request.POST.get('host')
        extvar['filepath'] = request.POST.get('filename')
        app.publish_type.get_profile_content( app.publish_name, **extvar)
        
        profile_content = ""
        configure_file_name = os.path.basename(extvar['filepath'])
        local_path = os.path.join(settings.CONFIGURE_BACKUP, app.publish_name, configure_file_name )
        with open(local_path, 'r' ) as f:
            content = f.read()
            charset = chardet.detect(content).get('encoding')
            profile_content = content.decode(charset).encode('utf-8')
        return self._iresult( json.dumps( {'code': 1, 'profile_content': profile_content }) )
        
    def put(self, request, *args, **kwargs):
        result = {}
        extvar = dict()
        Put = QueryDict(request.body, encoding=request.encoding)
        id = Put.get('id')
        app = App.objects.get(id=id)
        region = Put.get('region', 0)
        if 0 == int(region):    # Just one
            extvar['host'] = Put.get('host')
        else:
            extvar['nodes'] = AppNode.objects.filter(app = app ).all()
        extvar['user'] = app.publish_user
        
        extvar['configure_file_name'] = os.path.basename( Put.get('configure_file') )
        configure_file_name = extvar['configure_file_name'] + '.cur'
        extvar['filepath'] = os.path.join(settings.CONFIGURE_BACKUP, app.publish_name, configure_file_name)
        path_utils.writedoc2unix(extvar['filepath'], Put.get('profile_content') )
        data = app.publish_type.save_profile_content(region, **extvar )
        for host, info in data.items(): 
            result[host] = info['status']
        return self._iresult( json.dumps( result ) )

     
@urls.register
class BrmServerControl(generic.View, CommonResponse):

    url_regex = r'^brm/servercontrol/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        id = request.GET.get('id')
        app = App.objects.get(id=id)
        target_nodes = AppNode.objects.filter(app = app)
        handlers = app.publish_type.get_handlers()
        data = {'name': app.publish_name, 'target_nodes': target_nodes, 'handlers': handlers}
        return self._isupply_response(request, 'brm/brm_servercontrol.html', data )
       
    @login_perm_required(perm_check=True)       
    def post(self, request, *args, **kwargs):
        resource = []
        id = request.POST.get('id')
        app = App.objects.get(id=id)
        appname = app.publish_name
        path_utils.clear_cachr_dir(appname, str(request.user.id)) # clear
        pubrange = request.POST.get('publish_machine', 'all')
        
        nodes = AppNode.objects.filter(app = app ).all()
        if 'all' != pubrange: 
            pubnode = []
            for node in nodes:
                if not node.machine.ssh_ip in pubrange.split(','):
                    continue
                pubnode.append(node)
        else:
            pubnode = nodes
            
        optype = request.POST.get('optype')
        info = app.publish_type.get_handlers(optype)
        
        for node in pubnode:
            resource.append({
                    'host': node.machine.ssh_ip, 
                    'port': node.machine.ssh_port, 
                    'user': app.publish_user,
            })
        Task.objects.create(
            route_key = "COMMAND",
            json_data = json.dumps({
                'appid': id, 
                'resource': resource, 
                'optype': optype,
                'uid': str(request.user.id),
                'url': settings.TIMELY_RECORD_URL})
        )
        return self._iresult( json.dumps( {'resource':resource, 'cmd':info[0]['cmd'] } ) )
            

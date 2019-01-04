import os
import json
import uuid
import pysvn
from django.conf import settings
from .models import App,Record
from dashboards.executor.management.event import event_ins
from utils import path_utils



class SvnClient(object):
    
    def __init__(self, user, passwd):
        self.client = pysvn.Client()
        self.client.set_default_username(user)
        self.client.set_default_password(passwd)
            

@event_ins.register(route_key='RELEASE')
def do_release_task(data):
    print 'data--->: ', data
    data = json.loads(data)
    webscoketid = data['websocketid']
    app = App.objects.get(id=data['appid'])
    try:
        # first, Svn checkout latest version.
        svn = SvnClient(settings.SVN_USER, settings.SVN_PASSWD)
        outpath = os.path.join(
            settings.SVN_OUTPATH, 
            str(uuid.uuid1() ), 
            os.path.basename(app.publish_scmurl)  )
        path_utils.ensure_dir( outpath )
        svn.client.checkout(app.publish_scmurl, outpath )
    
        # second, Wiping '.svn' each of directory.
        current_version, total_size = path_utils.filter_path( outpath, ['.svn'] )
        
        # Third, Transfer the packet to the remote path.
        extra_vars=dict(
            source=outpath, 
            target=app.publish_path, 
            webscoketid=webscoketid, 
            total=total_size, appid=data['appid'] )
        playbook_result = app.run_playbook( extra_vars )
        print 'playbook_result: ', playbook_result
        
        # forth, Update db data and record operation.
        operation_status = 1
        for v in playbook_result.values():
            if v['status'] != "ok":
                operation_status = 2
                break
        app.publish_status = 2
        app.current_version = current_version
        playbook_result['version'] = current_version
        app.save()
        ret = Record.objects.create( app = app, 
                                  action = 'RELEASE',
                                  status = operation_status,
                                  details = json.dumps(playbook_result),
                                  created_by = data['username'],)
        print 'ret-------->: ', ret
    except Exception, e:
        print 'run_playbook error: ', e
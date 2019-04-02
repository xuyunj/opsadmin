import os
import json
import uuid
import pysvn
from django.conf import settings
from .models import App,Record
from dashboards.executor.management.event import event_ins
from utils import path_utils
import traceback
import logging


class SvnClient(object):
    
    def __init__(self, user, passwd):
        self.client = pysvn.Client()
        self.client.set_default_username(user)
        self.client.set_default_password(passwd)
            

@event_ins.register(route_key='RELEASE')
def do_release_task(data):
    logging.info('recv data: %s', data)
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
        result = Record.objects.create( app = app, 
                                  action = 'RELEASE',
                                  status = operation_status,
                                  details = json.dumps(playbook_result),
                                  created_by = data['username'],)
        logging.info("do_release_task result: %s", result)
    except Exception, e:
        logging.error('error in do_release_task: %s', traceback.format_exc() )
        

@event_ins.register(route_key='COMMAND')        
def do_command_task(data):
    try:
        logging.info('recv data: %s', data)
        data = json.loads(data)
        app = App.objects.get(id=data['appid'])
        result = app.publish_type.do_handle(
            app.publish_name, data['resource'], data['optype'], data['uid'], data['url'] )
        for host, info in result.items():
            record_path = os.path.join(
                settings.COMMAND_TIMELY_RECORD, app.publish_name, data['uid'], host )
            with open(record_path, 'a+') as f:
                f.write('finish')
                f.flush()
        logging.info("do_command_task result: %s", result)
    except:
        logging.error('error in do_command_task: %s', traceback.format_exc() )
    
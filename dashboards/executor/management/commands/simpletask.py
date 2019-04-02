#coding:utf-8
import sys
import time
import json
import threading
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.module_loading import autodiscover_modules
from django.utils import autoreload, six
from dashboards.executor.management.event import event_ins
from dashboards.executor.models import Task


autodiscover_modules('task')


# Program end event
_END_EVENT_ = threading.Event()
_END_EVENT_.clear()


class Command(BaseCommand):
    
        
    def add_arguments(self, parser):
        parser.add_argument('-q', '--quit', action='store_true', 
            help = 'This is the primary class for executing asynchronous task. ')
        parser.add_argument('--noreload', action='store_false', dest='use_reloader', default=True,
            help='Tells Django to NOT use the auto-reloader.')
        
    def handle(self, *args, **options):
        """
        Runs the server, using the autoreloader if needed
        """
        use_reloader = options.get('use_reloader')

        if use_reloader:
            autoreload.main(self.inner_run, None, options)
        else:
            self.inner_run(None, **options)
            
    def inner_run(self, *args, **options):
    
        quit_command = 'CTRL-BREAK' if sys.platform == 'win32' else 'CONTROL-C'
        
        self.stdout.write((
            "%(started_at)s\n"
            "Django version %(version)s, using settings %(settings)r\n"
            "Starting development server\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "started_at": datetime.now().strftime('%B %d, %Y - %X'),
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "quit_command": quit_command,
        })
        try:
            while not _END_EVENT_.isSet():
                tasks = Task.objects.order_by('run_level')[0:10]
                if not tasks:
                    _END_EVENT_.wait(1.0)
                    continue
                for task in tasks:
                    data = json.loads( task.json_data )
                    if data.has_key('iscron') and int(data['iscron']) == 1:
                        current_time = datetime.now()
                        runtime = datetime.strptime(data['runtime'], '%Y-%m-%d %H:%M')
                        if current_time < runtime :
                            _END_EVENT_.wait(1.0)
                            continue
                    event_ins.dealt(task.route_key, task.json_data )
                    task.delete()
        except Exception, e:
            self.stdout.write('run error. Detail error info as follows:  %s' % e)
        
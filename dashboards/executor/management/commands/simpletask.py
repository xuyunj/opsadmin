#coding:utf-8
import time,json
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.module_loading import autodiscover_modules
from dashboards.executor.models import Task
from dashboards.project.brm.models import App
from dashboards.executor.management.event import event_ins

autodiscover_modules('task')


class Command(BaseCommand):
    help = (
        "This is the primary class for executing asynchronous task. "
    )
    
    def add_arguments(self, parser):

        parser.add_argument(
            '-q',
            '--quit',
            action='store_true',
            help = self.help,
        )
        
    def handle(self, *args, **options):
        try:
            while True:
                tasks = Task.objects.all()
                if not tasks:
                    time.sleep(1)
                    continue
                task = tasks[0]
                event_ins.dealt(task.route_key, task.json_data )
                Task.objects.get(id=task.id).delete()
        except Exception, e:
            self.stdout.write('run error. Detail error info as follows:  %s' % e)

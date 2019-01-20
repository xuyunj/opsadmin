#coding:utf-8
import os
import yaml
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from ansible.module_utils._text import to_text
from dashboards.project.general.models import Machine
from utils.ansibclient import AnsibleAPI

    
class CommonModel(models.Model):

    created_by = models.CharField(max_length=30)
    created_time = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True


@python_2_unicode_compatible
class Template(CommonModel):
    """
    A publish template is a reusable job definition for applying a project (with
    playbook).
    """
    name = models.CharField(unique=True, max_length=30)
    profile = models.CharField(max_length=100)
    handlers = models.TextField(null=True, blank=True)
    playbook = models.TextField()
    
    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = 'Template'
        verbose_name_plural = verbose_name
      
    @classmethod
    def get_template(cls, name=None):
        return cls.objects.all() if not name else cls.objects.filter(name=name).all()
        
    def get_profiles(self, host, user):
        machine = Machine.objects.get(ssh_ip=host)
        ansib = AnsibleAPI([{
            'host': machine.ssh_ip, 
            'port': machine.ssh_port, 
            'user': user,
        }])
        result = ansib.exec_shell( "ls -l %s | grep ^-" % self.profile )
        if result[host]['status'] != 'ok':
            out = result[host]['result']['stderr']
        else:
            stdout_lines = result[host]['result']['stdout_lines']
            out = [ os.path.join(self.profile,line.split(' ')[-1]) for line in stdout_lines ]
        return {'status': result[host]['status'], 'out': out }
        
    def get_profile_content(self, app_name, **kwargs):
        machine = Machine.objects.get(ssh_ip=kwargs['host'])
        ansib = AnsibleAPI([{
            'host': machine.ssh_ip, 
            'port': machine.ssh_port, 
            'user': kwargs['user'],
        }])
        local_path = os.path.join(
            settings.CONFIGURE_BACKUP, 
            app_name,
            #'{{ inventory_hostname }}',
            os.path.basename(kwargs['filepath']) )
        return ansib.get_file(kwargs['filepath'],  local_path)
        
    def save_profile_content(self, region, **kwargs):
        resource = []
        if 0 == int(region):
            host = kwargs.get('host')
            machine = Machine.objects.get(ssh_ip=host)
            resource.append({
                'host': machine.ssh_ip, 
                'port': machine.ssh_port, 
                'user': kwargs.get('user'),
            })
        else:
            nodes = kwargs.get('nodes')
            for node in nodes:
                resource.append({
                    'host': node.machine.ssh_ip, 
                    'port': node.machine.ssh_port, 
                    'user': kwargs.get('user'),
                })
        ansib = AnsibleAPI(resource)
        remote_path = os.path.join(self.profile, kwargs['configure_file_name'] )
        return ansib.put_file(kwargs['filepath'], remote_path )
        
    def get_handlers(self, optype=None):
        handlers_dict = {}
        handlers = yaml.load(self.handlers) if self.handlers else []
        map(lambda handler: handlers_dict.update(handler), handlers )
        if optype:
            return handlers_dict.get(optype)
        return handlers_dict
        
    def do_handle(self, name, resource, optype, uid, url ):
        handlers_dict = {}
        handlers = yaml.load(self.handlers) if self.handlers else []
        map(lambda handler: handlers_dict.update(handler), handlers )
        info = handlers_dict.get(optype)
        ansib = AnsibleAPI(resource)
        return ansib.exec_timely_command( info[0]['cmd'], url, name, uid )
        
        
class AppNode(models.Model):
    """
    Application publishing node.
    """
    app = models.ForeignKey("App", on_delete=models.CASCADE)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = 'AppNode'
        verbose_name_plural = verbose_name
        
   
@python_2_unicode_compatible        
class Plugin(CommonModel):
    """
    Plug-ins that may be required during the distribution process.
    """
    app = models.ForeignKey("App", null=True, blank=True, on_delete=models.SET_NULL)
    pre_release = models.TextField()
    post_release = models.TextField()
    
    def __str__(self):
        return self.app.publish_name
        
    class Meta:
        verbose_name = 'Plugin'
        verbose_name_plural = verbose_name

        
@python_2_unicode_compatible
class App(CommonModel):
    """
    Application information
    """
    status = (
        (1, 'offline'),
        (2, 'online'),
        (3, 'unknown'),
    )
    
    publish_name = models.CharField(unique=True, max_length=30)
    publish_alias = models.CharField(unique=True, max_length=30)
    publish_type = models.ForeignKey("Template", null=True, blank=True, on_delete=models.SET_NULL)
    publish_user = models.CharField(max_length=30)
    publish_path = models.CharField(max_length=1024,default='',)
    publish_scmurl = models.URLField(blank=False)
    publish_num = models.IntegerField( null=True, blank=True )
    publish_status = models.IntegerField( choices=status, default=1)
    publish_time = models.DateTimeField(default=timezone.now)
    publish_runstat = models.IntegerField( choices=status, default=1)
    current_version = models.CharField(null=True, blank=True, max_length=30)
    
    def __str__(self):
        return "%s(%s)" % (self.publish_alias, self.publish_name)
        
    class Meta:
        verbose_name = 'App'
        verbose_name_plural = verbose_name
        
    def run_playbook(self, extra_vars={} ):
        resource = []
        nodes = AppNode.objects.filter(app_id = self.id).all()
        for node in nodes:
            resource.append({
                'host': node.machine.ssh_ip, 
                'port': node.machine.ssh_port, 
                'user': self.publish_user,
                'pass': 'service!@#'
            })   
        ansib = AnsibleAPI(resource)
        cache_key = os.path.join(os.getcwd(), self.publish_type.name)
        file_data = to_text(self.publish_type.playbook, errors='surrogate_or_strict')
        parsed_data = ansib.loader.load(data=file_data, file_name=self.publish_type.name, show_content=True)
        ansib.loader._FILE_CACHE[cache_key] = parsed_data
        return ansib.run_playbook([self.publish_type.name, ], extra_vars )
        
 
@python_2_unicode_compatible 
class Record(CommonModel):
    """
    Application operation record.
    """
    status = (
        (1, 'SUCCESS'),
        (2, 'FAILED'),
    )
    app = models.ForeignKey("App", null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(null=True, blank=True, max_length=30)
    status = models.IntegerField( choices=status, default=1)
    details = models.TextField()
    
    def __str__(self):
        return self.app.publish_name
        
    class Meta:
        verbose_name = 'Record'
        verbose_name_plural = verbose_name
    
    
    
    
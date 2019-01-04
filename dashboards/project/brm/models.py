#coding:utf-8
import os
from django.db import models
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
    playbook = models.TextField()
    
    def __str__(self):
        return self.name
      
    @classmethod
    def get_template(cls, name=None):
        return cls.objects.all() if not name else cls.objects.filter(name=name).all()
    
    class Meta:
        verbose_name = 'Template'
        verbose_name_plural = verbose_name
        
        
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
    
    
    
    
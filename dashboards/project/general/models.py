#coding:utf-8
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.db.models import Count
from utils.ansibclient import AnsibleAPI
    
        
      
class UniUser(models.Model):
    ssh_username = models.CharField(blank=True, max_length=20, verbose_name='SSH username')
    ssh_password = models.CharField(blank=True, max_length=64,verbose_name='SSH password')
    ssh_password_expire = models.DateTimeField(null=True, blank=True,verbose_name='Password expire' )
    ssh_machine = models.ForeignKey("Machine", null=True, blank=True, on_delete=models.CASCADE, verbose_name="machine")
    
    @property
    def needs_ssh_password(self):
        return True if self.ssh_password == 'ASK' else False
        
    @classmethod
    def get_all_users(cls):
        return cls.objects.values('ssh_username').annotate(Count("ssh_username"))
      
    @classmethod
    def get_user_machins(cls, username):
        return cls.objects.filter(ssh_username=username).all()
    
    class Meta:
        verbose_name = 'UniUser'
        verbose_name_plural = verbose_name
        unique_together = ('ssh_username','ssh_machine')
        
        
class Machine(models.Model):
    ssh_ip = models.GenericIPAddressField( unique=True)
    ssh_port = models.IntegerField(default=22)
    os_type = models.IntegerField(choices=((1,'linux'), (2, 'windows')),default=1)
    created_by = models.CharField(max_length=30)
    created_time = models.DateTimeField(default=timezone.now)
    
    def __str__ (self):
        return self.ssh_ip
    
    class Meta:
        verbose_name = 'Machine'
        verbose_name_plural = verbose_name
        
    
    @classmethod
    def get_machine_list(cls):
        return cls.objects.all()
    
    @classmethod
    def add_machine(cls, data, createdby, isappend=True):
        resource = []
        resource.append({
                'host': data.get('hosts'), 
                'port': data.get('port'), 
                'user': data.get('user'),
                'pass': data.get('password'),
            })  

        secret_key_config = {
            'ssh_dir': '~/.ssh',
            'ssh_key': data.get('sshkey'),
            'authorized_keys': 'authorized_keys',
            'redirect_symbol': '>>' if isappend else '>'
        }
        prefix = "  copying key to %s@%s:%s/%s..." %(data.get('hosts'),
                                                    data.get('user'),
                                                    secret_key_config['ssh_dir'],
                                                    secret_key_config['authorized_keys'])
                                                    
        key_cmd_string = ('mkdir -p %(ssh_dir)s;'
                'echo "%(ssh_key)s" %(redirect_symbol)s %(ssh_dir)s/%(authorized_keys)s;'
                'chmod 644 %(ssh_dir)s/%(authorized_keys)s;'
                'chmod 700 %(ssh_dir)s') % secret_key_config
                
        ansib = AnsibleAPI(resource)
        result = ansib.exec_shell(key_cmd_string)
        if result[data.get('hosts')]['status'] =='failed':
            return prefix + 'FAILED!'
        obj = cls.objects.create( 
            ssh_ip = data.get('hosts'), ssh_port = data.get('port'), created_by = createdby,)
        if obj:
            UniUser.objects.create(ssh_username = data.get('user'),ssh_machine=obj)
        return prefix + 'SUCCESS!'
    

@python_2_unicode_compatible    
class Inventory(models.Model):
    name = models.CharField(max_length=30, unique=True, verbose_name="Inventory name")
    machines = models.ManyToManyField("Machine", blank=True, verbose_name="Machine")
    
    def __str__ (self):
        return self.name
    
    class Meta:
        verbose_name = 'Inventory'
        verbose_name_plural = verbose_name
    


class Credential(models.Model):
    '''
    A credential contains information about how to talk to a remote set of hosts
    Usually this is a SSH key location, and possibly an unlock password.
    If used with sudo, a sudo password should be set if required.
    '''
    #ssh_key_data = models.TextField(blank=True, verbose_name='SSH private key')
    #ssh_key_unlock = models.CharField(max_length=64, blank=True, verbose_name='SSH key unlock')
    
    #@property
    #def needs_ssh_key_unlock(self):
    #    return 'ENCRYPTED' in self.ssh_key_data and\
    #           (not self.ssh_key_unlock or self.ssh_key_unlock == 'ASK')
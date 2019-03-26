#coding:utf-8
from django.db import models
from django.db import IntegrityError
from authority.models import User
from django.utils.encoding import python_2_unicode_compatible
from django.db.models import Count
from utils.ansibclient import AnsibleAPI
from utils.saltapi import SaltAPI


@python_2_unicode_compatible 
class Asset(models.Model):
    """
    资产总表
    """
    
    asset_types = (
        (1, '服务器'),
        (2, '网络设备'),
        (3, '存储设备'),
        (4, '安全设备'),
        (5, '软件资产'),
    )

    asset_status = (
        (0, '在线'),
        (1, '下线'),
        (2, '未知'),
        (3, '故障'),
        (4, '备用'),
    )

    sn = models.CharField(max_length=128, unique=True, verbose_name="资产序列号")
    name = models.CharField(max_length=64, unique=True, verbose_name="资产名称")
    category = models.SmallIntegerField(choices=asset_types, default=1, verbose_name='资产类型')
    oem = models.ForeignKey('Manufacturer', null=True, blank=True, verbose_name='制造商')
    contract = models.ForeignKey('Contract', null=True, blank=True, verbose_name='合同')
    status = models.SmallIntegerField(choices=asset_status, default=0, verbose_name='资产状态')
    tags = models.ManyToManyField('Tag', blank=True, verbose_name='标签')
    memo = models.TextField(null=True, blank=True, verbose_name='备注')
    admin = models.ForeignKey(User, null=True, blank=True, verbose_name='资产管理员', related_name='admin')
    approved_by = models.ForeignKey(User, null=True, blank=True, verbose_name='批准人', related_name='approved_by')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='批准日期')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新日期')

    def __str__(self):
        return '<%s>  %s' % (self.get_category_display(), self.name)

    class Meta:
        verbose_name = '资产总表'
        verbose_name_plural = verbose_name
        ordering = ['-created_time']


@python_2_unicode_compatible
class ServerDevice(models.Model):
    """
    服务器设备
    """
    
    sub_types = (
        (1, '刀片机'),
        (2, '小型机'),
        (3, 'PC服务器'),
    )

    adding_ways = (
        ('auto', '自动添加'),
        ('manual', '手工录入'),
    )

    asset = models.OneToOneField('Asset', on_delete=models.CASCADE ) #联级删除
    category = models.SmallIntegerField(choices=sub_types, default=4, verbose_name='服务器类型')
    model = models.CharField(max_length=128, null=True, blank=True, verbose_name='型号')
    cabinet = models.ForeignKey('Cabinet', null=True, blank=True, verbose_name='归属机柜')
    ordinal = models.CharField(max_length=30, null=True, blank=True, verbose_name='机柜序号')
    manageip = models.GenericIPAddressField(null=True, blank=True, verbose_name='管理IP')
    os_type = models.CharField(max_length=64, blank=True, null=True, verbose_name='系统类型')
    os_distribution = models.CharField(max_length=64, blank=True, null=True, verbose_name='发行版本')
    os_release = models.CharField(max_length=64, blank=True, null=True, verbose_name='系统版本')
    created_by = models.CharField(choices=adding_ways, max_length=32, default='auto', verbose_name="添加方式")

    def __str__(self):
        return '%s--%s--%s <sn:%s>' % (self.asset.name, self.get_category_display(), self.model, self.asset.sn)

    class Meta:
        verbose_name = '服务器'
        verbose_name_plural = verbose_name


class SecurityDevice(models.Model):
    """
    安全设备
    """
    
    sub_types = (
        (1, '防火墙'),
        (2, '入侵检测设备'),
        (3, '互联网网关'),
        (4, '运维审计系统'),
    )

    asset = models.OneToOneField('Asset')
    category = models.SmallIntegerField(choices=sub_types, default=0, verbose_name="设备类型")

    def __str__(self):
        return self.asset.name + "--" + self.get_category_display() + " id:%s" % self.id

    class Meta:
        verbose_name = '安全设备'
        verbose_name_plural = verbose_name


class StorageDevice(models.Model):
    """
    存储设备
    """
    
    sub_types = (
        (1, '磁盘阵列'),
        (2, '网络存储器'),
        (3, '磁带库'),
        (4, '磁带机'),
    )

    asset = models.OneToOneField('Asset')
    category = models.SmallIntegerField(choices=sub_types, default=0, verbose_name="设备类型")

    def __str__(self):
        return self.asset.name + "--" + self.get_category_display() + " id:%s" % self.id

    class Meta:
        verbose_name = '存储设备'
        verbose_name_plural = verbose_name


class NetworkDevice(models.Model):
    """
    网络设备
    """
    
    sub_types = (
        (0, '路由器'),
        (1, '交换机'),
        (2, '负载均衡'),
        (4, 'VPN设备'),
    )

    asset = models.OneToOneField('Asset')
    category = models.SmallIntegerField(choices=sub_types, default=0, verbose_name="设备类型")
    model = models.CharField(max_length=128, null=True, blank=True, verbose_name="设备型号")
    firmware = models.CharField(max_length=128, blank=True, null=True, verbose_name="设备固件版本")
    port_num = models.SmallIntegerField(null=True, blank=True, verbose_name="端口个数")
    vlan_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name="VLanIP")
    intranet_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name="内网IP")
    detail = models.TextField(null=True, blank=True, verbose_name="详细配置")

    def __str__(self):
        return '%s--%s--%s <sn:%s>' % (self.asset.name, self.get_category_display(), self.model, self.asset.sn)

    class Meta:
        verbose_name = '网络设备'
        verbose_name_plural = verbose_name


class Software(models.Model):
    """
    付费软件
    """
    sub_types = (
        (0, '操作系统'),
        (1, '办公\开发软件'),
        (2, '业务软件'),
    )

    category = models.SmallIntegerField(choices=sub_types, default=0, verbose_name="软件类型")
    license_num = models.IntegerField(default=1, verbose_name="授权数量")
    version = models.CharField(max_length=64, unique=True, help_text='例如: CentOS release 6.7 (Final)',
                               verbose_name='软件/系统版本')

    def __str__(self):
        return '%s--%s' % (self.get_category_display(), self.version)

    class Meta:
        verbose_name = '软件/系统'
        verbose_name_plural = verbose_name


class CPU(models.Model):
    """
    CPU组件
    """

    asset = models.OneToOneField('Asset')
    cpu_model = models.CharField(max_length=128, blank=True, null=True, verbose_name='CPU型号')
    cpu_count = models.PositiveSmallIntegerField(default=1, verbose_name='物理CPU个数')
    cpu_core_count = models.PositiveSmallIntegerField(default=1, verbose_name='CPU核数')

    def __str__(self):
        return self.asset.name + ":   " + self.cpu_model

    class Meta:
        verbose_name = 'CPU'
        verbose_name_plural = verbose_name


class RAM(models.Model):
    """
    内存组件
    """
    
    sn = models.CharField(max_length=128, blank=True, null=True, verbose_name='SN号')
    asset = models.ForeignKey('Asset')
    model = models.CharField(max_length=128, blank=True, null=True, verbose_name='内存型号')
    manufacturer = models.CharField(max_length=128, blank=True, null=True, verbose_name='制造商')
    slot = models.CharField(max_length=64, verbose_name='插槽')
    capacity = models.IntegerField(blank=True, null=True, verbose_name='内存大小(GB)')

    def __str__(self):
        return '%s: %s: %s: %s' % (self.asset.name, self.model, self.slot, self.capacity)

    class Meta:
        verbose_name = '内存'
        verbose_name_plural = verbose_name
        unique_together = ('asset', 'slot')  # 同一资产下的内存，根据插槽的不同，必须唯一


class Disk(models.Model):
    """
    硬盘组件
    """

    interface_types = (
        ('SATA', 'SATA'),
        ('SAS', 'SAS'),
        ('SCSI', 'SCSI'),
        ('SSD', 'SSD'),
        ('unknown', 'unknown'),
    )

    sn = models.CharField(max_length=128, verbose_name='SN号')
    asset = models.ForeignKey('Asset')
    slot = models.CharField(max_length=64, blank=True, null=True, verbose_name='插槽位')
    model = models.CharField(max_length=128, blank=True, null=True, verbose_name='型号')
    manufacturer = models.CharField(max_length=128, blank=True, null=True, verbose_name='磁盘制造商')
    capacity = models.FloatField(blank=True, null=True, verbose_name='磁盘大小(GB)')
    interface_type = models.CharField(max_length=16, choices=interface_types, default='unknown', verbose_name='接口类型')

    def __str__(self):
        return '%s:  %s:  %s:  %sGB' % (self.asset.name, self.model, self.slot, self.capacity)

    class Meta:
        verbose_name = '硬盘'
        verbose_name_plural = verbose_name
        unique_together = ('asset', 'sn')


class NIC(models.Model):
    """
    网卡组件
    """

    asset = models.ForeignKey('Asset')
    name = models.CharField(max_length=64, blank=True, null=True, verbose_name='名称')
    model = models.CharField(max_length=128, verbose_name='型号')
    mac = models.CharField(max_length=64, verbose_name='MAC地址')
    ip = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP')
    netmask = models.CharField(max_length=64, blank=True, null=True, verbose_name='掩码')
    #up = models.BooleanField(default=False)
    bonding = models.CharField(max_length=64, blank=True, null=True, verbose_name='绑定地址')

    def __str__(self):
        return '%s:  %s:  %s' % (self.asset.name, self.model, self.mac)

    class Meta:
        verbose_name = '网卡'
        verbose_name_plural = verbose_name
        unique_together = ('asset', 'model', 'mac')  # 资产、型号和mac必须联合唯一。防止虚拟机中的特殊情况发生错误。


@python_2_unicode_compatible 
class IDC(models.Model):
    """
    机房
    """
    name = models.CharField(max_length=64, unique=True, verbose_name='名称')
    address = models.CharField(max_length=64, unique=True, verbose_name='地址')
    phone = models.CharField(max_length=32, blank=True, null=True, verbose_name='联系人')
    memo = models.CharField(max_length=128, blank=True, null=True, verbose_name='备注')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '机房'
        verbose_name_plural = verbose_name


@python_2_unicode_compatible         
class Cabinet(models.Model):
    """
    机柜
    """
    idc = models.ForeignKey('IDC')
    name = models.CharField(max_length=64, verbose_name='名称')
    size = models.SmallIntegerField(verbose_name='机柜大小(U)')
    memo = models.CharField(max_length=128, blank=True, null=True, verbose_name='备注')
    
    def __str__(self):
        return '%s|%s' % (self.idc.name, self.name)
        
    class Meta:
        verbose_name = '机柜'
        verbose_name_plural = verbose_name
        unique_together = ('idc', 'name')
    

@python_2_unicode_compatible 
class Manufacturer(models.Model):
    """
    厂商
    """

    name = models.CharField(max_length=64, unique=True, verbose_name='厂商名称')
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name='支持电话')
    memo = models.CharField(max_length=128, blank=True, null=True, verbose_name='备注')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '厂商'
        verbose_name_plural = verbose_name


class BusinessUnit(models.Model):
    """
    业务线
    """

    name = models.CharField(max_length=64, unique=True, verbose_name='业务线')
    parent = models.ForeignKey('self', blank=True, null=True, related_name='parent_level')
    memo = models.CharField(max_length=64, blank=True, null=True, verbose_name='备注')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '业务线'
        verbose_name_plural = verbose_name


@python_2_unicode_compatible 
class Contract(models.Model):
    """
    合同
    """

    sn = models.CharField(max_length=128, unique=True, verbose_name='合同号')
    name = models.CharField(max_length=64, verbose_name='合同名称')
    price = models.IntegerField(verbose_name='合同金额')
    detail = models.TextField(blank=True, null=True, verbose_name='合同详细')
    start_day = models.DateField(blank=True, null=True, verbose_name='生效日期')
    end_day = models.DateField(blank=True, null=True, verbose_name='失效日期')
    license_num = models.IntegerField(blank=True, null=True, verbose_name='license数量')
    memo = models.TextField(blank=True, null=True, verbose_name='备注')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建日期')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='修改日期')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '合同'
        verbose_name_plural = verbose_name


@python_2_unicode_compatible 
class Tag(models.Model):
    """
    标签
    """
    name = models.CharField(max_length=32, unique=True, verbose_name='标签名')
    created_time = models.DateField(auto_now_add=True, verbose_name='创建日期')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '标签'
        verbose_name_plural = verbose_name


@python_2_unicode_compatible        
class GatherAgent(models.Model):
    """
    采集程序
    """
 
    agent_type = (
        (1, 'myparamiko'),
        (2, 'mysaltstack'),
    )
    
    name = models.CharField(max_length=32, blank=True, null=True,unique=True, verbose_name="名称")
    genre = models.SmallIntegerField(choices=agent_type, default=1, verbose_name='类别')
    scheme = models.CharField(max_length=128, blank=True, null=True, verbose_name='配置')
    
    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = '采集程序'
        verbose_name_plural = verbose_name
        
    def get_connection_params(self, ip):
        if self.genre == 1:
            user, port = self.scheme.split(';')
            host = {'host': ip, 'port': int(port),'user': user, }
        elif self.genre == 2:
            url, user, passwd = self.scheme.split(';')
            host = {'host': ip, 'pass': passwd,'user': user, }
        else:
            print "The type of gather agent is not found. " 
            return False
        
        connection = self.get_genre_display()
        return connection, host 
        
        
    

@python_2_unicode_compatible         
class VirtHost(models.Model):
    """
    虚拟机
    """
    
    virt_status = (
        (0, '在线'),
        (1, '下线'),
        (2, '未知'),
        (3, '故障'),
        (4, '备用'),
    )
    
    adding_ways = (
        ('auto', '自动添加'),
        ('manual', '手工录入'),
    )
    
    business_ip = models.GenericIPAddressField(unique=True, verbose_name='业务IP')
    business_unit = models.ForeignKey('BusinessUnit', null=True, blank=True, verbose_name=u'属于的业务线')
    hosted_on = models.ForeignKey('ServerDevice', related_name='hosted_on_server',
                                  blank=True, null=True, verbose_name="宿主机")
    status = models.SmallIntegerField(choices=virt_status, default=0, verbose_name='资产状态')
    gather_agent = models.ForeignKey('GatherAgent', verbose_name=u'采集程序')
    created_by = models.CharField(choices=adding_ways, max_length=32, default='auto', verbose_name="添加方式")
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='批准日期')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新日期')
    
    def __str__(self):
        return self.business_ip
        
    class Meta:
        verbose_name = '虚拟机'
        verbose_name_plural = verbose_name
    
    def get_virtbasic(self):
        try:
            return self.virtbasic
        except Exception, e:
            return VirtBasic(virthost=self)
            
    def get_virtuser(self, user_id):
        try:
            return VirtUser.objects.filter(virthost=self, user_id=user_id)[0]
        except Exception, e:
            return VirtUser(virthost=self, user_id=user_id)
        
    def gather_facts(self):     
    
        channel, host = self.gather_agent.get_connection_params(self.business_ip)
        ansib = AnsibleAPI([host], connection=channel)
        try:
            result = ansib.gather_facts()
            facts = result[self.business_ip]['result']['ansible_facts']
        except Exception, e:
            print "Ansible gather facts error: %s" % e 
            return False
            
        basic = self.get_virtbasic()
        basic.hostname = facts["ansible_hostname"]
        basic.cpu_core_count = facts["ansible_processor_vcpus"]
        basic.memory_size = facts["ansible_memtotal_mb"]
        #basic.swap_size = facts["ansible_memory_mb"]["swap"]["total"]
        basic.disk_size = sum([int(facts["ansible_devices"][i]["sectors"]) * \
                          int(facts["ansible_devices"][i]["sectorsize"]) / 1024 / 1024 / 1024 \
                          for i in facts["ansible_devices"] if i[0:2] in ("sd", "ss")])
        basic.os_type = facts["ansible_system"]
        basic.os_distribution = facts["ansible_distribution"]
        basic.os_release = facts["ansible_distribution_version"]
        basic.save()
        
        # Virt User
        sysuser = self.get_virtuser(facts["ansible_user_id"])
        sysuser.user_dir = facts["ansible_user_dir"]
        sysuser.user_shell = facts["ansible_user_shell"]
        sysuser.save()
        
        # Virt Nic
        facts['ansible_interfaces'].remove('lo')
        for interface in facts['ansible_interfaces']:
            virtnic = VirtNic(virthost=self)
            virtnic.name = interface
            key = 'ansible_' + interface.replace('-', '_')
            virtnic.status = 1 if facts[key]['active'] else 0 
            virtnic.mac = facts[key]['macaddress']
            virtnic.ip =  facts[key]['ipv4']['address'] if facts[key].has_key('ipv4') else ""
            virtnic.netmask = facts[key]['ipv4']['netmask'] if facts[key].has_key('ipv4') else ""
            #virtnic.speed = facts[key]['speed'] if facts[key].has_key('speed') else ""
            try:
                virtnic.save()
            except IntegrityError:
                pass
            
        return True
       

@python_2_unicode_compatible         
class VirtBasic(models.Model):

    virthost = models.OneToOneField('VirtHost', on_delete=models.CASCADE)
    hostname = models.CharField(max_length=128, unique=True, verbose_name='主机名')
    cpu_core_count = models.PositiveSmallIntegerField(default=1, blank=True, null=True, verbose_name='CPU核数')
    cpu_model = models.CharField(max_length=128, blank=True, null=True, verbose_name='CPU型号')
    memory_size = models.FloatField(blank=True, null=True, verbose_name='内存大小(M)')
    disk_size = models.FloatField(blank=True, null=True, verbose_name='磁盘大小(G)')
    os_type = models.CharField(max_length=64, blank=True, null=True, verbose_name='系统类型')
    os_distribution = models.CharField(max_length=64, blank=True, null=True, verbose_name='发行版本')
    os_release = models.CharField(max_length=64, blank=True, null=True, verbose_name='系统版本')
    
    def __str__(self):
        return '%s basic info' % self.hostname
        
    class Meta:
        verbose_name = '虚拟机基础信息'
        verbose_name_plural = verbose_name
 

@python_2_unicode_compatible   
class VirtNic(models.Model):
    """
    虚拟机网卡
    """
    
    nic_status = (
        (0, 'DOWN'),
        (1, 'UP'),
    )

    virthost = models.ForeignKey('VirtHost')
    name = models.CharField(max_length=64, blank=True, null=True, verbose_name='名称')
    mac = models.CharField(max_length=64, verbose_name='MAC地址')
    ip = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP')
    netmask = models.GenericIPAddressField(blank=True, null=True, verbose_name='掩码')
    status = models.SmallIntegerField(choices=nic_status, default=0, verbose_name='状态')
    bonding = models.CharField(max_length=64, blank=True, null=True, verbose_name='绑定地址')

    def __str__(self):
        return '%s:  %s:  %s' % (self.virthost.business_ip, self.name, self.mac)

    class Meta:
        verbose_name = '虚拟机网卡'
        verbose_name_plural = verbose_name
        unique_together = ('virthost', 'name', 'mac')  
        

@python_2_unicode_compatible        
class VirtUser(models.Model):
    virthost = models.ForeignKey('VirtHost')
    user_id = models.CharField(max_length=32, verbose_name='用户名')
    user_dir = models.CharField(max_length=64, verbose_name='家目录')
    user_shell = models.CharField(max_length=64, verbose_name='命令解释')
    
    def __str__(self):
        return '%s:  %s' % (self.virthost.business_ip, self.user_id)
        
    class Meta:
        verbose_name = '系统用户'
        verbose_name_plural = verbose_name
        unique_together = ('virthost', 'user_id')
        
    @classmethod
    def get_all_users(cls):
        return cls.objects.values('user_id').annotate(Count("user_id"))
        
    @classmethod
    def get_user_machins(cls, user_id):
        return cls.objects.filter(user_id=user_id).all()
    

#coding:utf-8
from django.contrib import admin
from django.utils.translation import ugettext, ugettext_lazy as _
from .models import UniUser,Machine,Inventory


class UniUserAdmin(admin.ModelAdmin):
    list_display = ['ssh_username', 'ssh_password_expire', 'ssh_machine']
    
    

class MachineAdmin(admin.ModelAdmin):
    list_display = ['ssh_ip', 'ssh_port', 'os_type', 'created_by', 'created_time' ]
    

class InventoryAdmin(admin.ModelAdmin):
    filter_horizontal = ('machines',)
    
 
    
        
admin.site.register(UniUser, UniUserAdmin)
admin.site.register(Machine, MachineAdmin)
admin.site.register(Inventory, InventoryAdmin)
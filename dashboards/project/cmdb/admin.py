from django.contrib import admin
from . import models


class AssetAdmin(admin.ModelAdmin):
    list_display = ['category', 'name', 'status', 'approved_by', 'created_time', "updated_time"]


admin.site.register(models.Asset, AssetAdmin)
admin.site.register(models.ServerDevice)
admin.site.register(models.StorageDevice)
admin.site.register(models.SecurityDevice)
admin.site.register(models.BusinessUnit)
admin.site.register(models.Contract)
admin.site.register(models.CPU)
admin.site.register(models.Disk)
#admin.site.register(models.EventLog)
admin.site.register(models.IDC)
admin.site.register(models.Manufacturer)
admin.site.register(models.NetworkDevice)
admin.site.register(models.NIC)
admin.site.register(models.RAM)
admin.site.register(models.Software)
admin.site.register(models.Tag)
admin.site.register(models.Cabinet)
admin.site.register(models.GatherAgent)
admin.site.register(models.VirtHost)
admin.site.register(models.VirtBasic)
admin.site.register(models.VirtNic)


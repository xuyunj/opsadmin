#coding:utf-8
import os
import json
from dashboards import urls
from django.views import generic
from django.conf import settings
from utils.response import CommonResponse
from authority.shortcuts import login_perm_required
from .models import Asset,IDC,Cabinet,VirtHost


@urls.register
class CmdbIndex(generic.View, CommonResponse):
    
    url_regex = r'^cmdb/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        return self._isupply_response(request, 'cmdb/cm_index.html', {})
        
        
@urls.register
class CmdbAsset(generic.View, CommonResponse):
    
    url_regex = r'^cmdb/list/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        assets = Asset.objects.all()
        return self._isupply_response(request, 'cmdb/cm_list.html', {'assets': assets})
        
@urls.register
class CmdbAssetDetail(generic.View, CommonResponse):
    
    url_regex = r'^cmdb/detail/$'
    #url_regex = r'^cmdb/detail/(?P<asset_id>[0-9]+)/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        id = request.GET.get('asset_id')
        asset = Asset.objects.get(id= id)
        return self._isupply_response(request, 'cmdb/cm_detail.html', {'asset': asset})

        
@urls.register
class CmdbRoom(generic.View, CommonResponse):
    
    url_regex = r'^cmdb/room/$'
    
    @login_perm_required(perm_check=True)
    def get(self, request, *args, **kwargs):
        idcs = IDC.objects.all()
        for idc in idcs:
            devices = 0
            for cabinet in idc.cabinet_set.all():
                devices += len(cabinet.serverdevice_set.all())
            idc.devices = devices
        return self._isupply_response(request, 'cmdb/cm_room.html', {'idcs': idcs})
        
@urls.register
class CmdbCabinet(generic.View, CommonResponse):
    
    url_regex = r'^cmdb/cabinet/$'
    
    @login_perm_required(perm_check=False)
    def get(self, request, *args, **kwargs):
        id = request.GET.get('idc_id')
        cabinets = Cabinet.objects.filter(idc_id= id)
        return self._isupply_response(request, 'cmdb/cm_cabinet.html', {'cabinets': cabinets})
        
    @login_perm_required(perm_check=False)
    def post(self, request, *args, **kwargs):
        devices = {}
        position = []
        cabinet_id = request.POST.get('cabinet_id')
        cabinet = Cabinet.objects.get(id= cabinet_id)
        for device in cabinet.serverdevice_set.all():
            start, end = device.ordinal.split(',')
            devices[start] = {'sn': device.asset.sn, 'space': int(end) - int(start) + 1 }
            position.append( start )
        data = {'name': cabinet.name, 
                'size': cabinet.size, 'devices': devices, 'position': position, 'idc': cabinet.idc.name, }
        return self._iresult( json.dumps(data) )
        
    
@urls.register
class CmdbVirtHost(generic.View, CommonResponse):
    
    url_regex = r'^cmdb/virthost/$'
    
    @login_perm_required(perm_check=False)
    def get(self, request, *args, **kwargs):
        virthosts = VirtHost.objects.all()
        return self._isupply_response(request, 'cmdb/cm_virthost.html', {'virthosts': virthosts})
        
@urls.register
class VirtHostDetail(generic.View, CommonResponse):
    
    url_regex = r'^cmdb/virthost/detail/$'
    
    @login_perm_required(perm_check=False)
    def get(self, request, *args, **kwargs):
        hostid = request.GET.get('id')
        virthost = VirtHost.objects.get(id=hostid)
        return self._isupply_response(request, 'cmdb/cm_virtdetail.html', {'virthost': virthost})


@urls.register
class VirtHostRefresh(generic.View, CommonResponse):
    
    url_regex = r'^cmdb/virthost/refresh/$'
    
    @login_perm_required(perm_check=False)
    def get(self, request, *args, **kwargs):
        hostid = request.GET.get('id')
        virtmachine = VirtHost.objects.get(id=hostid)
        stat = 'ok' if virtmachine.gather_facts() else 'error'
        return self._iresult(stat)


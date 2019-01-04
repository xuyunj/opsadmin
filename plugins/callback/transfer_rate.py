
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
from ansible.plugins.callback import CallbackBase
import urllib
import urllib2
from django.conf import settings


class CallbackModule(CallbackBase):

    @staticmethod
    def runner_on_rate(value, total, **kwargs ):
        plus = 1 if value == total else 0
        try:
            msg = dict(
                appid = kwargs['appid'],
                name = kwargs['name'],
                value = value,
                plus = plus,
                allsize = kwargs['allsize'],
            )
            params = {'udid': kwargs['socketid'], 'msg': json.dumps(msg) }
            url = settings.WEBSOCKET_NOTIFY_URL + '?' + urllib.urlencode(params)
            req = urllib2.Request( url )
            resp = urllib2.urlopen(req)
            print(resp.read())
            resp.close()
        except Exception , e:
            print('error in runner_on_rate: ', e)
    
    
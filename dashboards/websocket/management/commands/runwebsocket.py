#coding:utf-8
import os
import re
import time,json
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
import tornado.web
import tornado.ioloop
import tornado.websocket


naiveip_re = re.compile(r"""^(?:
(?P<addr>
    (?P<ipv4>\d{1,3}(?:\.\d{1,3}){3}) |         # IPv4 address
    (?P<ipv6>\[[a-fA-F0-9:]+\]) |               # IPv6 address
    (?P<fqdn>[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*) # FQDN
):)?(?P<port>\d+)$""", re.X)
DEFAULT_PORT = "9000"


class CustomerSet(object):

    
    def __init__(self):
        self.__clients = {}
    
    def __contains__(self, key):
        return key in self.__clients
        
    def __getitem__(self, key):
        return self.__clients[key]
        
    def __setitem__(self, key, value):
        self.__clients[key] = value
        
    def __delitem__(self, key):
        del self.__clients[key]
        
    def get(self, key, default=None):
        return self.__clients.get(key, default)
  
    def has_key(self, key):
        return key in self.__clients

    def keys(self):
        return self.__clients.keys()
        
    def values(self):
        return self.__clients.values()
        
    def items(self):
        return self.__clients.items()
        
        
class Client(object):
    def __init__(self, udid, ws):
        self.udid = udid
        self.ws = ws
        
        
class WebSocketHandler(tornado.websocket.WebSocketHandler):
        
    def check_origin(self, origin):
        """
        Allow cross-domain
        """
        return True

    def open(self):
        print("WebSocket opened")
        self.udid = self.get_argument('udid')     
        clients = self.application.settings['websocket_clients']
        if clients.has_key(self.udid):
            self.close(1001, 'Connected elsewhere')
        clients[self.udid] = Client(self.udid, self)
    
    def on_message(self, message):
        if message is None:
            return
        
        #self.write_message(u"You said: " + message)
        self.broadcast(message)
        
    def broadcast(self, message):

        clients = self.application.settings['websocket_clients']
        for client in clients.values():
            client.ws.write_message(message)
    
    def on_close(self):
        clients = self.application.settings['websocket_clients']
        del clients[self.udid]
        print("WebSocket closed {0}".format(self.udid) )
        
        
class SendToClientHandler(tornado.web.RequestHandler):

    def get(self):
        udid = self.get_argument('udid')
        message = self.get_argument('msg')
        
        has_sent = False
        clients = self.application.settings['websocket_clients']
        client = clients.get(udid)
        if client:
            client.ws.write_message(message)
            has_sent = True
        if has_sent:
            result = {'code': 1000, 'msg': "OK" }
        else:
            result = {'code': 1002, 'msg': "The `{0}` client was not found.".format(udid) }
        self.write( result )
        
        
class App(tornado.web.Application):

    def __init__(self):
    
        handlers = [
            (r"/channel", WebSocketHandler),
            (r"/sendto", SendToClientHandler),
        ]

        settings = dict(
            debug = True,
            autoescape = None,
            #default_handler_class = NotFoundHandler,
            static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template"),
            websocket_clients = CustomerSet()
        )
        super( App , self ).__init__(handlers , **settings )
        

class Command(BaseCommand):
   
   
    def add_arguments(self, parser):
        parser.add_argument('addrport', nargs='?',
            help='Optional port number, or ipaddr:port')
        parser.add_argument('--ipv6', '-6', action='store_true', dest='use_ipv6', default=False,
            help='Tells Django to use an IPv6 address.')
            
        
    def handle(self, *args, **options):
    
        self.use_ipv6 = options.get('use_ipv6')
        if self.use_ipv6 and not socket.has_ipv6:
            raise CommandError('Your Python does not support IPv6.')
        self._raw_ipv6 = False
        if not options.get('addrport'):
            self.addr = ''
            self.port = DEFAULT_PORT
        else:
            m = re.match(naiveip_re, options['addrport'])
            if m is None:
                raise CommandError('"%s" is not a valid port number '
                                   'or address:port pair.' % options['addrport'])
            self.addr, _ipv4, _ipv6, _fqdn, self.port = m.groups()
            if not self.port.isdigit():
                raise CommandError("%r is not a valid port number." % self.port)
            if self.addr:
                if _ipv6:
                    self.addr = self.addr[1:-1]
                    self.use_ipv6 = True
                    self._raw_ipv6 = True
                elif self.use_ipv6 and not _fqdn:
                    raise CommandError('"%s" is not a valid IPv6 address.' % self.addr)
        if not self.addr:
            self.addr = '::1' if self.use_ipv6 else '127.0.0.1'
            self._raw_ipv6 = bool(self.use_ipv6)
        self.run(**options)
            
    def run(self, **options):
        """
        Runs the websocket server.
        """
        try:
            application = App()
            application.listen(self.port, self.addr)
            tornado.ioloop.IOLoop.current().start()
        except Exception, e:
            self.stdout.write('run error. Detail error info as follows:  %s' % e)

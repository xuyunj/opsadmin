#coding:utf-8
import os
import json
import logging
import tornado.web
import tornado.ioloop
import tornado.websocket



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
        允许跨域
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
        
        
        
class IndexHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("test.html")
        
        
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
            (r"/", IndexHandler),
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

 

application = App()
application.listen(9000)
tornado.ioloop.IOLoop.current().start()



        
        

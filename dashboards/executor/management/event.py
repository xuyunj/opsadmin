

class Event(object):
    """
    The mapping of events to functions
    """
    
    def __init__(self):
        self._func_mapping = dict()
        
    def dealt(self, route_key, data ):
        """
        Get the dealt handle by route key.
        """
        func = self._func_mapping.get( route_key )
        if not func:
            print 'need not handle %s %s' % (route_key,data)
            return
        func( data )
        
    def register(self, route_key):
        
        def decorate(handele):
            self._func_mapping[route_key] = handele
            return handele
         
        return decorate
        
event_ins = Event()
        
        
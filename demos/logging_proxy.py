#!/usr/bin/env python
#
# logging_proxy.py: Demonstrates how to inherit the Session class so that we can easily get notifications of I/O events .
#                   The idea - by overriding 6 simple function, we get all the I/O events we need in order to fully monitor
#                   the connection (new connnection,got-data, close-connection)


import tornado.ioloop
import maproxy.proxyserver
import maproxy.session
import string   # for the "filter"




class LoggingSession(maproxy.session.Session):
    """
    This class simply overrides the major "session" functions of the parent-class.
    The idea is very simple: every time the proxy has done "something" , we will
    "intercept" the  call , print the data and .
    Note that the actually code is very small. all my comments and explanations taking too much space !

    There are 6 functions that we would like to monitor:
    -  new_connection      : New session
    -  on_p2s_done_connect : When the session is connected to the server
    -  on_c2p_done_read    : C->S data
    -  on_p2s_done_read    : C<-S data
    -  on_c2p_close        : Client closes he connection
    -  on_p2s_close        : Server closes he connection
    
    """
    
    # Class variable: counter for the number of connections
    running_counter=0
    
    
    def __init__(self,*args,**kwargs):
        """
        Currently overriding the "__init__" is not really required since the parent's 
        __init__ is doing absolutely nothing, but it is a good practice for
        the future... (future updates)
        """
        super(LoggingSession,self).__init__(*args,**kwargs)


    #def new_connection(self,stream : tornado.iostream.IOStream ,address,proxy):
    def new_connection(self,stream ,address,proxy):
        """
        Override the maproxy.session.Session.new_connection() function
        This function is called by the framework (proxyserver) for every new session
        """
        # Let's increment the "autonumber" (remember: this is single-threaded, so on lock is required)
        LoggingSession.running_counter+=1
        self.connid=LoggingSession.running_counter
        print("#%-3d: New Connection on %s" % (self.connid,address))
        super(LoggingSession,self).new_connection(stream,address,proxy)

    def on_p2s_done_connect(self):
        """
        Override the maproxy.session.Session.on_p2s_done_connect() function
        This function is called by the framework (proxyserver) when the session is 
        connected to the target-server
        """
        print("#%-3d: Server connected" % (self.connid))
        super(LoggingSession,self).on_p2s_done_connect()



    def on_c2p_done_read(self,data):
        """
        Override the maproxy.session.Session.on_c2p_done_read(data) function
        This function is called by the framework (proxyserver) when we get data from the client 
        (to the target-server)
        """
        # First, let's call the parent-class function (on_cp2_done_read),
        # this will minimize network delay and complete the operation
        super(LoggingSession,self).on_c2p_done_read(data)

        # Now let simply print the data (print just the printable characters)
        print("#%-3d:C->S (%d bytes):\n%s" % (self.connid,len(data),filter(lambda x: x in string.printable, data)) )
        

    def on_p2s_done_read(self,data):
        """
        Override the maproxy.session.Session.on_p2s_done_read(data) function
        This function is called by the framework (proxyserver) when we get data from the server 
        (to the client)
        """
        # First, let's call the parent-class function (on_p2s_done_read),
        # this will minimize network delay and complete the operation
        super(LoggingSession,self).on_p2s_done_read(data)
        
        # Now let simply print the data (print just the printable characters)
        print("#%-3d:C<-S (%d bytes):\n%s" % (self.connid,len(data),filter(lambda x: x in string.printable, data)) )
    
    def on_c2p_close(self):
        """
        Override the maproxy.session.Session.on_c2p_close() function.
        This function is called by the framework (proxyserver) when the client closes the connection
        """
        print("#%-3d: C->S Closed" % (self.connid))
        super(LoggingSession,self).on_c2p_close()

    def on_p2s_close(self):
        """
        Override the maproxy.session.Session.on_p2s_close() function.
        This function is called by the framework (proxyserver) when the server closes the connection
        """
        print("#%-3d: C<-S Closed" % (self.connid))
        super(LoggingSession,self).on_p2s_close()
        




class LoggingSessionFactory(maproxy.session.SessionFactory):
    """
    This session-factory will be used by the proxy when new sessions
    need to be generated .
    We only need a "new" function that will generate a session object
    that derives from maproxy.session.Session.
    The session that we create is our lovely LoggingSession that we declared
    earlier
    """
    def __init__(self):
        super(LoggingSessionFactory,self).__init__()
    def new(self,*args,**kwargs):
        return LoggingSession(*args,**kwargs)
        



# HTTP->HTTP
# On your computer, browse to "http://127.0.0.1:81/" and you'll get http://www.google.com
# The only "special" argument is the "session_factory" that ponits to a new instance of LoggingSessionFactory.
# By using our special session-factory, the proxy will create the 
# LoggingSession instances (instead of default Session instances)
server = maproxy.proxyserver.ProxyServer("www.google.com",80,session_factory=LoggingSessionFactory())
server.listen(81)
print("http://127.0.0.1:81 -> http://www.google.com")    
tornado.ioloop.IOLoop.instance().start()

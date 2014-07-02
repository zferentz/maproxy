#!/usr/bin/env python
import tornado
import tornado.tcpserver
import maproxy.session




class ProxyServer(tornado.tcpserver.TCPServer):
    """
    TCP Proxy Server .

    """
    def __init__(self,
                 target_server,target_port,
                 client_ssl_options=None,server_ssl_options=None,
                 session_factory=maproxy.session.SessionFactory(),
                 *args,**kwargs):
        """
        ProxyServer initializer functin (constructor) .
        Input Parameters:
            target_server           : the proxied-server IP
            target_port             : the proxied-server port
            client_ssl_options      : Configure this proxy as SSL terminator  (decrypt all data).
                                      Standard Tornado's SSL options dictionary
                                      (e.g.: keyfile and certfile to specify Server-Certificate)
            server_ssl_options      : Encrypt all outgoing data with SSL. this variables has 3 options:
                                      1. True:       enable SSL . default settings
                                      2. False/None: disalbe SSL
                                      3. Standard Tornado's SSL options dictionary
                                         (e.g.: keyfile and certfile to specify Client-Certificate)
            args,kwargs             : will be passed directly to the Tornado engine
        """
        assert(session_factory , issubclass(session_factory.__class__,maproxy.session.SessionFactory))
        self.session_factory=session_factory

        
        # First, get the server's address and port . 
        # This is the proxied server that we'll connect to
        self.target_server=target_server
        self.target_port=target_port
        
        # Now, remember the SSL potions
        # client_ssl_options : use it if you want an SSL listener (if you want that the proxy will have an SSL listener)
        # server_ssl_options:  use it if you want an SSL connection to the proxy server (if your target server is SSL)
        self.client_ssl_options=client_ssl_options
        self.server_ssl_options=server_ssl_options
        
        # Nromalize SSL options:
        # If the server is SSL, the tornado expects a dictionary, so let's change the True to {}
        # If the caller provided "ssl=False", we need to make it None
        if self.server_ssl_options is True:
            self.server_ssl_options={}
        if self.server_ssl_options is False:
            self.server_ssl_options=None
        if self.client_ssl_options is False:
            self.client_ssl_options=None

        # Session-List
        self.SessionsList=[]
        
        # call Tornado's Engine . pass args/kwargs directly
        super(ProxyServer,self).__init__(ssl_options=self.client_ssl_options,*args,**kwargs)
        
    
        
        
    def handle_stream(self, stream, address):
        """
        The proxy will call this function for every new connection as a callback
        This is the Session starting point: we initiate a new session and add it to the sessions-list
        """
        assert isinstance(stream,tornado.iostream.IOStream)
        #session=maproxy.session.Session(stream,address,self)
        session=self.session_factory.new()   # Use the factory to create new session
        session.new_connection(stream,address,self)
        self.SessionsList.append(session)

    def remove_session(self,session):
        assert (  isinstance(session, maproxy.session.Session) )
        assert ( session.p2s_state==maproxy.session.Session.State.CLOSED )
        assert ( session.c2p_state ==maproxy.session.Session.State.CLOSED )
        self.SessionsList.remove(session)
        self.session_factory.delete(session)

    def get_connections_count(self):
        return len(self.SessionsList)
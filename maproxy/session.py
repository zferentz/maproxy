#!/usr/bin/env python

import tornado
import socket
import maproxy.proxyserver



class Session(object):
    """
    The Session class if the heart of the system.
    - We create the session when  a client connects to the server (proxy). this connection is "c2p"
    - We create a connection to the server (p2s)
    - Each connection (c2p,p2s) has a state (Session.State) , can be CLOSED,CONNECTING,CONNECTED
    - Initially, when c2p is created we :
        - create the p-s connection
        - start read from c2p
    - Completion Routings:
        - on_XXX_done_read:
          When we get data from one side, we initiate a "start_write" to the other side .
          Exception: if the target is not connected yet, we queue the data so we can send it later
        - on_p2s_connected:
          When p2s is connected ,we start read from the server . 
          if queued data is available (data that was sent from the c2p) we initiate a "start_write" immediately
        - on_XXX_done_write:
          When we're done "sending" data , we check if there's more data to send in the queue. 
          if there is - we initiate another "start_write" with the queued data
        - on_XXX_close:
          When one side closes the connection, we either initiate a "start_close" on the other side, or (if already closed) - remove the session
    - I/O routings:
        - XXX_start_read: simply start read from the socket (we assume and validate that only one read goes at a time)
        - XXX_start_write: if currently writing , add data to queue. if not writing - perform io_write...
        
    


    """
    class LoggerOptions:
        """
        Logging options - which messages/notifications we would like to log...
        The logging is for development&maintenance. In production set all to False
        """
        # Log charactaristics
        LOG_SESSION_ID=True         # for each log, add the session-id
        # Log different operations
        LOG_NEW_SESSION_OP=False
        LOG_READ_OP=False
        LOG_WRITE_OP=False
        LOG_CLOSE_OP=False
        LOG_CONNECT_OP=False
        LOG_REMOVE_SESSION=False
        
    class State:
        """
        Each socket has a state.
        We will use the state to identify whether the connection is open or closed
        """
        CLOSED,CONNECTING,CONNECTED=range(3)
    
    def __init__(self):
        pass
    #def new_connection(self,stream : tornado.iostream.IOStream ,address,proxy):
    def new_connection(self,stream ,address,proxy):
            # First,validation
            assert isinstance(proxy,maproxy.proxyserver.ProxyServer) 
            assert isinstance(stream,tornado.iostream.IOStream)
            
            # Logging
            self.logger_nesting_level=0         # logger_nesting_level is the current "nesting level"
            if Session.LoggerOptions.LOG_NEW_SESSION_OP:
                self.log("New Session")

            
            # Remember our "parent" ProxyServer 
            self.proxy=proxy

            # R/W flags for each socket
            # Using the flags, we can tell if we're waiting for I/O completion
            # NOTE: the "c2p" and "p2s" prefixes are NOT the direction of the IO, 
            #       they represent the SOCKETS :
            #       c2p means the socket from the client to the proxy
            #       p2s means the socket from the proxy to the server
            self.c2p_reading=False  # whether we're reading from the client
            self.c2p_writing=False  # whether we're writing to the client
            self.p2s_writing=False  # whether we're writing to the server
            self.p2s_reading=False  # whether we're reading from the server

            # Init the Client->Proxy stream
            self.c2p_stream=stream
            self.c2p_address=address
            # Client->Proxy  is connected
            self.c2p_state=Session.State.CONNECTED
            
            # Here we will put incoming data while we're still waiting for the target-server's connection
            self.c2s_queued_data=[] # Data that was read from the Client, and needs to be sent to the  Server
            self.s2c_queued_data=[] # Data that was read from the Server , and needs to be sent to the  client

            # send data immediately to the client ... (Disable Nagle TCP algorithm)
            self.c2p_stream.set_nodelay(True)
            # Let us now when the client disconnects (callback on_c2p_close)
            self.c2p_stream.set_close_callback( self.on_c2p_close)

            # Create the Proxy->Server socket and stream
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            
            if self.proxy.server_ssl_options is not None:
                # if the "server_ssl_options" where specified, it means that when we connect, we need to wrap with SSL
                # so we need to use the SSLIOStream stream
                self.p2s_stream = tornado.iostream.SSLIOStream(s,ssl_options=self.proxy.server_ssl_options)
            else:
                # use the standard IOStream stream
                self.p2s_stream = tornado.iostream.IOStream(s)
            # send data immediately to the server... (Disable Nagle TCP algorithm)
            self.p2s_stream.set_nodelay(True)
            
            # Let us now when the server disconnects (callback on_p2s_close)
            self.p2s_stream.set_close_callback(  self.on_p2s_close )
            # P->S state is "connecting"
            self.p2s_state=self.p2s_state=Session.State.CONNECTING
            self.p2s_stream.connect(( proxy.target_server, proxy.target_port),  self.on_p2s_done_connect )
            

            # We can actually start reading immediatelly from the C->P socket
            self.c2p_start_read()
    
    # Each member-function can call this method to log data (currently to screen)
    def log(self,msg):
        prefix=str(id(self))+":" if Session.LoggerOptions.LOG_SESSION_ID else ""
        prefix+=self.logger_nesting_level*" "*4
        logging.debug(prefix + msg)
        
        

    #  Logging decorator (enter/exit)
    def logger(enabled=True):
        """
        We use this decorator to wrap functions and log the input/ouput of each function
        Since this decorator accepts a parameter, it must return an "inner" decorator....(Python stuff)
        """
        def inner_decorator(func):
            
        
            def log_wrapper(self,*args,**kwargs):

                msg="%s (%s,%s)" % (func.__name__,args,kwargs)

            
                self.log(msg)
                self.logger_nesting_level+=1
                r=func(self,*args,**kwargs)
                self.logger_nesting_level-=1
                self.log("%s -> %s" % (msg,str(r)) )
                return r
            return log_wrapper if enabled else func
            

        return inner_decorator

        
        
    ################
    ## Start Read ##
    ################
    @logger(LoggerOptions.LOG_READ_OP)
    def c2p_start_read(self):
        """
        Start read from client
        """
        assert( not self.c2p_reading)
        self.c2p_reading=True
        try:
            self.c2p_stream.read_until_close(lambda x: None,self.on_c2p_done_read)
        except tornado.iostream.StreamClosedError:
            self.c2p_reading=False

    @logger(LoggerOptions.LOG_READ_OP)
    def p2s_start_read(self):
        """
        Start read from server
        """
        assert( not self.p2s_reading)
        self.p2s_reading=True
        try:
            self.p2s_stream.read_until_close(lambda x:None,self.on_p2s_done_read)
        except tornado.iostream.StreamClosedError:    
            self.p2s_reading=False
    
    
    ##############################
    ## Read Completion Routines ##
    ##############################
    @logger(LoggerOptions.LOG_READ_OP)
    def on_c2p_done_read(self,data):
        # # We got data from the client (C->P ) . Send data to the server
        assert(self.c2p_reading)
        assert(data)
        self.p2s_start_write(data)
        
        
    @logger(LoggerOptions.LOG_READ_OP)
    def on_p2s_done_read(self,data):
        # got data from Server to Proxy . if the client is still connected - send the data to the client
        assert( self.p2s_reading)
        assert(data)
        self.c2p_start_write(data)


    #####################
    ## Write to stream ##
    #####################
    @logger(LoggerOptions.LOG_WRITE_OP)
    def _c2p_io_write(self,data):
        if data is None:
            # None means (gracefully) close-socket  (a "close request" that was queued...)
            self.c2p_state=Session.State.CLOSED
            try:
                self.c2p_stream.close()
            except tornado.iostream.StreamClosedError:
                self.c2p_writing=False
        else:
            self.c2p_writing=True
            try:
                self.c2p_stream.write(data,callback=self.on_c2p_done_write)
            except tornado.iostream.StreamClosedError:
                # Cancel the write, we will get on_close instead...
                self.c2p_writing=False
    @logger(LoggerOptions.LOG_WRITE_OP)
    def _p2s_io_write(self,data):
        if data is None:
            # None means (gracefully) close-socket  (a "close request" that was queued...)
            self.p2s_state=Session.State.CLOSED
            try:
                self.p2s_stream.close()
            except tornado.iostream.StreamClosedError:
                # Cancel the write. we will get on_close instead
                self.p2s_writing=False
        else:
            self.p2s_writing=True
            try:
                self.p2s_stream.write(data,callback=self.on_p2s_done_write)
            except tornado.iostream.StreamClosedError:
                # Cancel the write. we will get on_close instead
                self.p2s_writing=False


    #################
    ## Start Write ##
    #################
    @logger(LoggerOptions.LOG_WRITE_OP)
    def c2p_start_write(self,data):
        """
        Write to client.if there's a pending write-operation, add it to the S->C (s2c) queue
        """
        # If not connected - do nothing...
        if self.c2p_state != Session.State.CONNECTED: return

        if not self.c2p_writing:
            # If we're not currently writing
            assert( not self.s2c_queued_data ) # we expect the  queue to be empty
            
            # Start the "real" write I/O operation
            self._c2p_io_write(data)
        else:
            # Just add to the queue
            self.s2c_queued_data.append(data)
    
    @logger(LoggerOptions.LOG_WRITE_OP)
    def p2s_start_write(self,data):
        """
        Write to the server.
        If not connected yet - queue the data
        If there's a pending write-operation , add it to the C->S (c2s) queue
        """
        
        # If still connecting to the server - queue the data...
        if self.p2s_state == Session.State.CONNECTING:  
            self.c2s_queued_data.append(data)   # TODO: is it better here to append (to list) or concatenate data (to buffer) ?
            return
        # If not connected - do nothing
        if self.p2s_state == Session.State.CLOSED:  
            return
        assert(self.p2s_state == Session.State.CONNECTED)
        
        if not self.p2s_writing:
            # Start the "real" write I/O operation
            self._p2s_io_write(data)
        else:
            # Just add to the queue
            self.c2s_queued_data.append(data)

    
    ##############################
    ## Write Competion Routines ##
    ##############################
    @logger(LoggerOptions.LOG_WRITE_OP)
    def on_c2p_done_write(self):
        """
        A start_write C->P  (write to client) is done .
        if there is queued-data to send - send it
        """
        assert(self.c2p_writing)
        if self.s2c_queued_data:
            # more data in the queue, write next item as well..
            self._c2p_io_write( self.s2c_queued_data.pop(0))
            return
        self.c2p_writing=False
        
    
        
    @logger(LoggerOptions.LOG_WRITE_OP)
    def on_p2s_done_write(self):
        """
        A start_write P->S  (write to server) is done .
        if there is queued-data to send - send it
        """
        assert(self.p2s_writing)
        if self.c2s_queued_data:
            # more data in the queue, write next item as well..
            self._p2s_io_write( self.c2s_queued_data.pop(0))
            return
        self.p2s_writing=False
        


    ######################
    ## Close Connection ##
    ######################
    @logger(LoggerOptions.LOG_CLOSE_OP)
    def c2p_start_close(self,gracefully=True):
        """
        Close c->p connection
        if gracefully is True then we simply add None to the queue, and start a write-operation
        if gracefully is False then this is a "brutal" close:
            - mark the stream is closed
            - we "reset" (empty) the queued-data
            - if the other side (p->s) already closed, remove the session
        
        """
        if self.c2p_state == Session.State.CLOSED:
            return
        if gracefully:
            self.c2p_start_write(None)
            return

        self.c2p_state = Session.State.CLOSED
        self.s2c_queued_data=[]
        self.c2p_stream.close()
        if self.p2s_state == Session.State.CLOSED:
            self.remove_session()
            
            
    @logger(LoggerOptions.LOG_CLOSE_OP)
    def p2s_start_close(self,gracefully=True):
        """
        Close p->s connection
        if gracefully is True then we simply add None to the queue, and start a write-operation
        if gracefully is False then this is a "brutal" close:
            - mark the stream is closed
            - we "reset" (empty) the queued-data
            - if the other side (p->s) already closed, remove the session
        
        """
        if self.p2s_state == Session.State.CLOSED:
            return
        if gracefully:
            self.p2s_start_write(None)
            return

        self.p2s_state = Session.State.CLOSED
        self.c2s_queued_data=[]
        self.p2s_stream.close()
        if self.c2p_state == Session.State.CLOSED:
            self.remove_session()
        

    @logger(LoggerOptions.LOG_CLOSE_OP)
    def on_c2p_close(self):
        """
        Client closed the connection.
        we need to:
        1. update the c2p-state
        2. if there's no more data to the server (c2s_queued_data is empty) - we can close the p2s connection
        3. if p2s already closed - we can remove the session
        """
        self.c2p_state=Session.State.CLOSED
        if self.p2s_state == Session.State.CLOSED:
            self.remove_session()
        else:
            self.p2s_start_close(gracefully=True)
            

    @logger(LoggerOptions.LOG_CLOSE_OP)
    def on_p2s_close(self):
        """
        Server closed the connection.
        We need to update the satte, and if the client closed as well - delete the session
        """
        self.p2s_state=Session.State.CLOSED
        if self.c2p_state == Session.State.CLOSED:
            self.remove_session()
        else:
            self.c2p_start_close(gracefully=True)
        
    ########################
    ## Connect-Completion ##
    ########################
    @logger(LoggerOptions.LOG_CONNECT_OP)
    def on_p2s_done_connect(self):
        assert(self.p2s_state==Session.State.CONNECTING)
        self.p2s_state=Session.State.CONNECTED
        # Start reading from the socket
        self.p2s_start_read()
        assert(not self.p2s_writing)    # As expect no current write-operation ...
        
        # If we have pending-data to write, start writing...
        if self.c2s_queued_data:
            # TRICKY: get thte frst item , and write it...
            # this is tricky since the "start-write" will 
            # write this item even if there are queued-items... (since self.p2s_writing=False)
            self.p2s_start_write( self.c2s_queued_data.pop(0)  )
    
    ###########
    ## UTILS ##
    ###########
    @logger(LoggerOptions.LOG_REMOVE_SESSION)
    def remove_session(self):
        self.proxy.remove_session(self)


class SessionFactory(object):
    """
    This is  the default session-factory. it simply returns a "Session" object
    """
    def __init__(self):
        pass
        
    def new(self,*args,**kwargs):
        """
        The caller needs a Session objet (constructed with *args,**kwargs).
        In this implementation we're simply creating a new object. you can enhance and create a pool or add logs..
        """
        return Session(*args,**kwargs)
    def delete(self,session):
        """
        Delete a session object
        """
        assert( isinstance(session,Session))
        del session
        
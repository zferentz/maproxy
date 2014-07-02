#!/usr/bin/env python

import tornado.tcpserver
import threading
import time
import os
import functools


    


    

        
class IOManager(object):
    """
    The IOManager is responsible for managing one or more servers/proxies.
    You can add/remove servers/proxies as well as manage (start/stop/...) them.
    """
    def __init__(self):
        self._ioloop_thread=None
        self._servers={}     # id->server
        self._ioloop=tornado.ioloop.IOLoop.instance();
        
        # Some "status flags" - so external entities will be able to be notified...
        self._running=threading.Event()
        self._stopping=threading.Event()
        self._stopped=threading.Event()
        self._stopped.set()

        

    def __del__(self):
        self._ioloop.close()

    def get_servers_count(self):
        return len(self._servers)

    def get_connections_count(self):
        n=0
        for id,server in self._servers.items():
            assert isinstance(server , tornado.tcpserver.TCPServer)
            n+=server.get_connections_count()
        return n

        


    def ioloop(self):
        return self._ioloop

    #def add(self,server :   tornado.tcpserver.TCPServer ):
    def add(self,server ):
        """
        Add a TCPServer instace (or derivation) 
        """
        assert isinstance(server, tornado.tcpserver.TCPServer)
        assert self._servers.get(id(server)) is None , "Already Exists"
        self._servers[id(server)]=server
        return id(server)
    
    def remove(self,server):
        server.stop()
        del self._servers[id(server)]
        
        
    
    #def start(self,thread:bool=True ):
    def start(self,thread=True ):
        """
        Start to listen on all servers, and start the IOLoop
        """
        for id,server in self._servers.items():
            assert isinstance(server , tornado.tcpserver.TCPServer)
            server .start()
        
        if os.name=="nt":
            # On Windows, add a simple callback (freq:1sec) to display current number of connections
            import ctypes
            self.fan="|/-\\"
            self.fan_index=0

            def timeout():
                status=""
                if self._running.is_set():
                    status+="running "
                else:
                    status+="not-running"
                if self._stopping.is_set():
                    status+="stopping "
                ctypes.windll.kernel32.SetConsoleTitleA( "%c %s (%d Connections) "% (self.fan[self.fan_index],status,self.get_connections_count()))
                self.fan_index=(self.fan_index+1) % 4
                self._ioloop.add_timeout( time.time()+1 , timeout)

            self._ioloop.add_timeout( time.time()+1 , timeout)
        
        self._stopped.clear()
        self._running.set()
        
        # The next call is the blocking call

        if not thread:
            # Run the ioloop in this thread (default, blocking call)
            self._ioloop_thread=None
            self._ioloop.start()
        else:
            # run the ioloop in a new thread
            def _ioloop_thread():
                self._ioloop.start()
            self._ioloop_thread=threading.Thread( target=_ioloop_thread)
            self._ioloop_thread.start()
    
    
    def stop(self,gracefully=False,wait=False):
        """
        Stop the servers. By default, this function stops the server immediately (not-gracefully) , 
        all current connections will be terminated. You can set this behavior using the "gracefully" parametr.
            gracefully = True: wait forever
            gracefully = False: don't wait at all . terminate
            gracefull = timeout (integer/float) : how much time (seconds) to wait...
        NOTE: This is a nonblocking stop. it means that it will START the stop procedure but will not wait
              In fact, I don't think that it's possible to have a blocking stop in this layer/level
              (since we assume that this will be a callback from within  ab IOLoop-callback..)

             wait : if the ioloop was started as another thread, you can "wait" for the stop operation
        
    TODO (feature): terminate with RST (linger) , ...
        """
        if self._ioloop_thread and self._ioloop_thread.ident != threading.get_ident():
            # If called from another thread - run this procedure from the ioloop...
            self._ioloop.add_callback ( g_IOManager.stop , gracefully=gracefully)
            if wait:
                self._ioloop_thread.join()
            return
        assert wait is False , "You cannot run stop(wait=True) while not starting with start(thread=True)"

        
        self._stopping.set()

        def stop_procedure():
            self._ioloop.stop()
            self._running.clear()
            self._stopping.clear()
            self._stopped.set()

        def stop_if_no_connections(deadline):
            current_time=time.time()
            if self.get_connections_count() == 0 or (deadline and deadline-current_time<=0):
                # No more connections , or deadline has been reached/exceeded
                stop_procedure()
                return
            
            # We either need to wait 1-second (untless next-check), or less
            wait_time=current_time+1 if deadline is None else min( current_time+1,deadline)
            self._ioloop.add_timeout( wait_time , functools.partial(stop_if_no_connections ,deadline) )
            



        # First, stop listening...
        for id,server in self._servers.items():
            assert isinstance(server , tornado.tcpserver.TCPServer)
            server.stop()
        if not gracefully or self.get_connections_count()==0:
            stop_procedure()
            return
        
        if gracefully is True:
            gracefully_timeout=None # Wait forever...
        else:
            assert( isinstance(gracefully,int) or isinstance(gracefully,float)  )
            gracefully_timeout=time.time()+gracefully

        self._ioloop.add_callback(stop_if_no_connections , gracefully_timeout)
                



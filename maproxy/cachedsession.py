#!/usr/bin/env python

import logging
import socket
import time

import tornado

import maproxy.proxyserver
import maproxy.session

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

Session = maproxy.session.Session
LoggerOptions = Session.LoggerOptions

CACHE_KEY_NAME = "cache_key_name"


class CacheSimulator(dict):
    EXPIRATION_IN_SECONDS = 60

    def set(self, key, data):
        """Write to cache key+data

        :param key: key to store
        :param data: data to store
        """
        logger.debug("Cache: soring key '{}'".format(key))
        self[key] = {
            "key": key,
            "timestamp": time.time(),
            "data": data
        }

    def get(self, key):
        """Read item from cache

        :param key:key to retrieve
        :return: data (or None if not found)
        """
        entry = super().get(key)
        if not entry:
            # item not found in cache
            logger.debug("Cache: key '{}' not found".format(key))
            return None

        timestamp = entry["timestamp"]
        if time.time() - timestamp > CacheSimulator.EXPIRATION_IN_SECONDS:
            # Item expired. remove from cache
            logger.debug("Cache: key '{}' expired".format(key))
            del self[key]
            return None

        logger.debug("Cache: key '{}' found".format(key))
        return entry["data"]


g_cache = CacheSimulator()


class CachedSession(Session):
    """Extends the Session with cache

    When we get a new connection - if we have "cached data" - return the cached
    data (and don't even bother opening a socket to the server).

    If we don't have cached data - operate just like standard session however
    keep the data from the server in a cache. Note that we're storing in the
    cache only when the connection is closed (to avoid partial data) !!!!
    """

    # def new_connection(self,stream : tornado.iostream.IOStream ,address,proxy):
    def new_connection(self, stream, address, proxy):
        # First,validation
        assert isinstance(proxy, maproxy.proxyserver.ProxyServer)
        assert isinstance(stream, tornado.iostream.IOStream)

        # Logging
        self.logger_nesting_level = 0  # logger_nesting_level is the current "nesting level"
        if Session.LoggerOptions.LOG_NEW_SESSION_OP:
            self.log("New Session")

        # Remember our "parent" ProxyServer
        self.proxy = proxy

        # R/W flags for each socket
        # Using the flags, we can tell if we're waiting for I/O completion
        # NOTE: the "c2p" and "p2s" prefixes are NOT the direction of the IO,
        #       they represent the SOCKETS :
        #       c2p means the socket from the client to the proxy
        #       p2s means the socket from the proxy to the server
        self.c2p_reading = False  # whether we're reading from the client
        self.c2p_writing = False  # whether we're writing to the client
        self.p2s_writing = False  # whether we're writing to the server
        self.p2s_reading = False  # whether we're reading from the server

        # Init the Client->Proxy stream
        self.c2p_stream = stream
        self.c2p_address = address
        # Client->Proxy  is connected
        self.c2p_state = Session.State.CONNECTED

        # Here we will put incoming data while we're still waiting for the target-server's connection
        self.c2s_queued_data = []  # Data that was read from the Client, and needs to be sent to the  Server
        self.s2c_queued_data = []  # Data that was read from the Server , and needs to be sent to the  client

        # send data immediately to the client ... (Disable Nagle TCP algorithm)
        self.c2p_stream.set_nodelay(True)
        # Let us now when the client disconnects (callback on_c2p_close)
        self.c2p_stream.set_close_callback(self.on_c2p_close)

        self.s2c_stored_data = []  # data to store

        # Here comes the caching...
        # if we have cache - start writing it to the client
        # and don't bother with "p2s (proxy->server) socket
        # if we don't have cache - continue as usual
        cached_data = g_cache.get(CACHE_KEY_NAME)  # no meaning for the key...
        if cached_data:
            cached_data_size = 0
            for b in cached_data:
                cached_data_size += len(b) if b else 0

            logger.debug("using cache ({} bytes)".format(cached_data_size))
            self.p2s_state = Session.State.CLOSED
            self.p2s_stream = None
            self.s2c_queued_data = cached_data[1:]  # close connection when done
            self.s2c_queued_data.append(None)  # close connection when done
            self.c2p_start_write(cached_data[0])
        else:
            logger.debug("no cache")
            # Create the Proxy->Server socket and stream
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

            if self.proxy.server_ssl_options is not None:
                # if the "server_ssl_options" where specified, it means that when we connect, we need to wrap with SSL
                # so we need to use the SSLIOStream stream
                self.p2s_stream = tornado.iostream.SSLIOStream(
                    s, ssl_options=self.proxy.server_ssl_options)
            else:
                # use the standard IOStream stream
                self.p2s_stream = tornado.iostream.IOStream(s)
                # send data immediately to the server... (Disable Nagle TCP algorithm)
                self.p2s_stream.set_nodelay(True)

                # Let us know when the server disconnects (callback on_p2s_close)
                self.p2s_stream.set_close_callback(self.on_p2s_close)
                # P->S state is "connecting"
                self.p2s_state = Session.State.CONNECTING
                self.p2s_stream.connect(
                    (proxy.target_server, proxy.target_port),
                    self.on_p2s_done_connect)

                # We can actually start reading immediately from the C->P socket
                self.c2p_start_read()

    @Session.logger_deco(LoggerOptions.LOG_READ_OP)
    def on_p2s_done_read(self, data):
        """got data from Server to Proxy .
        if the client is still connected - append to the cached-stream
        and send the data to the client
        """
        logger.debug("Adding data to cache (size {})".format(len(data)))
        self.s2c_stored_data.append(data)
        return super().on_p2s_done_read(data)

    @Session.logger_deco(LoggerOptions.LOG_CLOSE_OP)
    def on_p2s_close(self):
        """
        Server closed the connection.
        We need to save all data to the cache,
        update the state, and if the client closed as well - delete the session
        """
        if self.s2c_stored_data:
            cached_data_size = 0
            for b in self.s2c_stored_data:
                cached_data_size += len(b) if b else 0

            logger.debug("Saving data cache ({} bytes)".format(cached_data_size))
            self.s2c_stored_data.append(None)
            g_cache.set(CACHE_KEY_NAME, self.s2c_stored_data)
            self.s2c_stored_data = None  # not required anymore

        return super().on_p2s_close()


class CachedSessionFactory(maproxy.session.SessionFactory):
    """Session factory for cached-sessions"""

    def new(self, *args, **kwargs):
        """
        The caller needs a Session objet (constructed with *args,**kwargs).
        In this implementation we're simply creating a new object. you can enhance and create a pool or add logs..
        """
        return CachedSession(*args, **kwargs)

    def delete(self, session):
        """
        Delete a session object
        """
        assert (isinstance(session, CachedSession))
        del session

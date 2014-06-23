#!/usr/bin/env python

import tornado.ioloop
import maproxy.proxyserver

# HTTPS->HTTP
ssl_certs={     "certfile":  "./certificate.pem",
                "keyfile": "./privatekey.pem" }

# "client_ssl_options=ssl_certs" simply means "listen using SSL"
# "server_ssl_options=True" simply means "connect to server with SSL"
server1 = maproxy.proxyserver.ProxyServer("www.google.com",443, 
                                         client_ssl_options=ssl_certs,
                                         server_ssl_options=True)
server1.listen(83)
print("https://127.0.0.1:83 -> http://www.google.com")

# "client_ssl_options=ssl_certs" simply means "listen using SSL"
# "server_ssl_options=ssl_certs" simply means "connect to server with client-certificates"
server2 = maproxy.proxyserver.ProxyServer("www.google.com",443, 
                                         client_ssl_options=ssl_certs,
                                         server_ssl_options=ssl_certs)
server2.listen(84)
print("https://127.0.0.1:84 -> http://www.google.com (using client-certificates)")

tornado.ioloop.IOLoop.instance().start()
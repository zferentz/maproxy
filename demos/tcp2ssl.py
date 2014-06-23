#!/usr/bin/env python

import tornado.ioloop
from maproxy.proxyserver import ProxyServer
# HTTP->HTTPS
# "server_ssl_options=True" simply means "connect to server with SSL"
server = ProxyServer("www.google.com",443, server_ssl_options=True)
server.listen(82)
print("http://127.0.0.1:82 -> https://www.google.com:443")
tornado.ioloop.IOLoop.instance().start();
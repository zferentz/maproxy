#!/usr/bin/env python

import tornado.ioloop
import maproxy.proxyserver

# HTTPS->HTTP
ssl_certs={     "certfile":  "./certificate.pem",
                "keyfile": "./privatekey.pem" }
# "client_ssl_options=ssl_certs" simply means "listen using SSL"
server = maproxy.proxyserver.ProxyServer("www.google.com",80,
                                         client_ssl_options=ssl_certs)
server.listen(83)
print("https://127.0.0.1:83 -> http://www.google.com")
tornado.ioloop.IOLoop.instance().start()
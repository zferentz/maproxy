#!/usr/bin/env python

import tornado.ioloop
import maproxy.proxyserver



# HTTP->HTTP
# On your computer, browse to "http://127.0.0.1:81/" and you'll get http://www.google.com
server = maproxy.proxyserver.ProxyServer("www.google.com",80)
server.listen(81)
print("http://127.0.0.1:81 -> http://www.google.com")    
tornado.ioloop.IOLoop.instance().start()

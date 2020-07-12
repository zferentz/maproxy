#!/usr/bin/env python3
import tornado.ioloop
import maproxy.proxyserver
import maproxy.cachedsession

server = maproxy.proxyserver.ProxyServer(
    "speedtest.tele2.net",80,
    session_factory=maproxy.cachedsession.CachedSessionFactory()
)
server.listen(5000,address="0.0.0.0")
tornado.ioloop.IOLoop.instance().start()


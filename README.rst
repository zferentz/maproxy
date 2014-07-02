===========
Ma`Proxy
===========

Ma`Proxy is a simple TCP proxy based on `Tornado <http://www.tornadoweb.org/>`_.

Well, maybe not that simple, since it supports:

* TCP -> TCP
    simple reverse proxy.
    Whatever data goes in , goes out

* TCP -> SSL 
    proxy to encrypt incoming data.
    a.k.a stunnel
                      
* SSL -> TCP
    proxy to decrypt incoming data
    a.k.a SSL-terminator or SSL-decryptor

* SSL- > SSL
    whatever gets in will be decrypted and then encrypted again
    
* Each SSL can be used with SSL certificates. including client-certificates !!


Examples:
----------
Let's start with the simplest example - no bells and whistles - a simple TCP proxy::

    #!/usr/bin/env python
    import tornado.ioloop
    import maproxy.proxyserver
    
    # HTTP->HTTP: On your computer, browse to "http://127.0.0.1:81/" and you'll get http://www.google.com
    server = maproxy.proxyserver.ProxyServer("www.google.com",80)
    server.listen(81)
    print("http://127.0.0.1:81 -> http://www.google.com")    
    tornado.ioloop.IOLoop.instance().start()

We are creating a proxy (reverse proxy, to be more accurate) that listens locally on port 81 (0.0.0.0:81) 
and redirect all calls to www.google.com (port 80) .
Note that:
1. This is NOT an HTTP-proxy , since  it operates in the lower TCP layer . this proxy has nothing to do with HTTP
2. we are actually listening on all the IP addresses, not only on 127.0.0.1 .

Now, Let's say that you'd like to listen on a "clear" (non-encrypted) connection but connect to an SSL website,
for example - create a proxy http://127.0.0.1:82 -> https://127.0.0.1:443 , simply update the "server" line::

    #!/usr/bin/env python
    import tornado.ioloop
    import maproxy.proxyserver
    
    # HTTP->HTTP: On your computer, browse to "http://127.0.0.1:81/" and you'll get http://www.google.com
    server = maproxy.proxyserver.ProxyServer("www.google.com",443,server_ssl_options=True)
    server.listen(82)
    print("http://127.0.0.1:82 -> https://www.google.com",)    
    tornado.ioloop.IOLoop.instance().start()

Alternatively, you can listen on SSL port and redirect the connection to a clear-text server.
In order to listen on SSL-port, you need to specify SSL server-certificates as "client_ssl_options"::

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


In the "demos" section of the source-code, you will also find:

* how to connect using SSL client-certificate
* how to inherit the "Session" object (that we internally use)
  and create a logging-proxy (proxy that logs everything) .



Installation:
--------------

    pip install maproxy

Source Code: https://github.com/zferentz/maproxy
Contact Me: zvika d-o-t ferentz a-t gmail d,o,t com  (if you can't figure it out - please don't contact me :)  )




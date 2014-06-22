#!/usr/bin/env python
import os
import sys
from maproxy.iomanager import IOManager
from maproxy.proxyserver import ProxyServer
import signal



g_IOManager=IOManager()


if __name__ == '__main__':

    # Add standard signal handlers -
    # call the "sto()" method when the user hits Ctrl-C
    signal.signal(signal.SIGINT, lambda sig,frame:  g_IOManager.stop())
    signal.signal(signal.SIGTERM, lambda sig,frame:  g_IOManager.stop())
    
    
    bUseSSL=True
    ssl_certs={     "certfile": os.path.join(os.path.dirname(sys.argv[0]), "certificate.pem"),
                    "keyfile": os.path.join(os.path.dirname(sys.argv[0]), "privatekey.pem") }
    
    if not os.path.isfile(ssl_certs["certfile"]) or \
        not os.path.isfile(ssl_certs["keyfile"]):
            print("Warning: SSL-Proxy is disabled . certificate file(s) not found")
            bUseSSL=False

    # HTTP->HTTP
    # On your computer, browse to "http://127.0.0.1:81/" and you'll get http://www.google.com
    server = ProxyServer("www.google.com",80)
    server.listen(81)
    g_IOManager.add(server)
    print("http://127.0.0.1:81 -> http://www.google.com")    

    # HTTP->HTTPS
    # "server_ssl_options=True" simply means "connect to server with SSL"
    server = ProxyServer("www.google.com",443, server_ssl_options=True)
    server.listen(82)
    g_IOManager.add(server)
    print("http://127.0.0.1:82 -> https://www.google.com:443")


    if bUseSSL:
        # HTTPS->HTTP
        # "client_ssl_options=ssl_certs" simply means "listen using SSL"
        server = ProxyServer("www.google.com",80, client_ssl_options=ssl_certs)
        server.listen(83)
        g_IOManager.add(server)
        print("https://127.0.0.1:83 -> http://www.google.com")


        # HTTPS->HTTPS
        # (Listens on SSL , connect to SSL)
        server = ProxyServer("www.google.com",443, client_ssl_options=ssl_certs,server_ssl_options=True)
        server.listen(84)
        g_IOManager.add(server)
        print("https://127.0.0.1:84 -> https://www.google.com:443 ")


        # HTTP->HTTPS , use specific client-certificate
        # "server_ssl_options=ssl_certs" means "connect to SSL-server using the provided client-certificates"
        server = ProxyServer("www.google.com",443, server_ssl_options=ssl_certs)
        server.listen(85)
        g_IOManager.add(server)
        print("http://127.0.0.1:85 -> https://www.google.com:443 (Connect with client-certificates)")


    print("Starting...")
    # the next call to start) is blocking (thread=False)
    # So we simply wait for Ctrl-C
    g_IOManager.start(thread=False)
    print("Stopping...")
    g_IOManager.stop(gracefully=True,wait=False)
    print("Stopped...")
    print("Done")
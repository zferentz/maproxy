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


Examples::
	**TBD:** Add sample-code here

Installation::
	pip install maproxy


maproxy
=======

 Introduction
--------------
Ma'Proxy - My first experiment with Tornado .
This is a simple TCP reverse-proxy with a tiny twist - it can be used as either SSL-terminator (incoming SSL outgoing clear) or SSL-initiator (incoming clear , outgoing SSL . a.k.a STunnel ).


 Background
------------
In my past I was a C/C++ server-side developer. I developed network/system applications that had to deal with a lot of TCP traffic (C10K). Later on I switched to Python and fell in love with the language.
When i've heard about Tornado (http://www.tornadoweb.org/) I was very skeptic - how can  a language which does not even support real multithreading can compete with the art of C/C++ network programming ???
So i've decided to try Tornado  and write some servers  - echo server , proxy server , etc...
Then it hit me - even that C/C++ is probably (much?) faster ,  the ease of use and the design of tornado makes it really easy to write a server that can scale and have no worries about locks ,  locking-hierarchy, EAGAIN  , EWOULDBLOCK and other pains....

So this project, Ma'Proxy is my first attempt to write a Tornado proxy  that can actually be useful.

 What does it do ?
-------------------

The proxy listen on one (or more) listening points and once a connection initiated, it connects to the target-server and act as a proxy.

For example, one can 
The beauty here is that you can easly configure the proxy to use SSL (as either client or server or both), so it supports:
1. TCP -> TCP  (standard TCP proxy)
2. TCP -> SSL  (Add SSL encryption  - STunnel . You can even specify Client-Certificates thanks to OpenSSL and Tornado )
3. SSL -> TCP  (SSL terminator : client connects with SSL , the proxy decrypt the data and connects to the target-server without in clear)
4. SSL -> SSL (SSL terminator + SSL initiator )

 Licensing
-----------
Apache License v2.0



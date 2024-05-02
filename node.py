"""https://cs.berry.edu/~nhamid/p2p/framework-python.html"""

import socket
import traceback

class Node:
    def __init__(self, maxpeers, serverport, myid=None, serverhost = None):
        self.debug = 0

        self.maxpeers = int(maxpeers)
        self.serverport = int(serverport)

        # If not supplied, the host name/IP address will be determined
        # by attempting to connect to an Internet host like Google.
        if serverhost: self.serverhost = serverhost
        else: self.__initserverhost()

            # If not supplied, the peer id will be composed of the host address
            # and port number
        if myid: self.myid = myid
        else: self.myid = '%s:%d' % (self.serverhost, self.serverport)

            # list (dictionary/hash table) of known peers
        self.peers = {}  

            # used to stop the main loop
        self.shutdown = False  

        self.handlers = {}
        self.router = None
        # end constructor
        def makeserversocket(self, port, backlog=5):
            s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
            s.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
            s.bind( ( '', port ) )
            s.listen( backlog )
            return s
        
        def mainloop( self ):
            s = self.makeserversocket( self.serverport )
            s.settimeout(2)
            self.__debug( 'Server started: %s (%s:%d)'
                % ( self.myid, self.serverhost, self.serverport ) )

            while not self.shutdown:
                try:
                    self.__debug( 'Listening for connections...' )
                    clientsock, clientaddr = s.accept()
                    clientsock.settimeout(None)

                    t = threading.Thread( target = self.__handlepeer, args = [ clientsock ] )
                    t.start()
                except KeyboardInterrupt:
                    self.shutdown = True
                    continue
                except:
                    if self.debug:
                        traceback.print_exc()
                        continue
            # end while loop

            self.__debug( 'Main loop exiting' )
            s.close()
import sys
import socket
import select
import random
import settings
import threading
import target as my_target
import client
from http.server import ThreadingHTTPServer

# dumb netcat server, short tcp connection
# $ ~  while true ; do nc -l 8888 < server1.html; done
# $ ~  while true ; do nc -l 9999 < server2.html; done
SERVER_POOL = []

# dumb python socket echo server, long tcp connection
# $ ~  while  python server.py
# SERVER_POOL = [('localhost', 6666)]

#def round_robin(iter):
    # round_robin([A, B, C, D]) --> A B C D A B C D A B C D ...
 #   return next(iter)

def min_load():
    if len(SERVER_POOL) == 0:
        raise LookupError
    result = SERVER_POOL[0]
    min_load = result.thread_count
    for s in SERVER_POOL:
        if s.thread_count < min_load:
            result = s
            min_load = result.thread_count
    return result

class LoadBalancer(object):
    """ Socket implementation of a load balancer.
    Flow Diagram:
    +---------------+      +-----------------------------------------+      +---------------+
    | client socket | <==> | client-side socket | server-side socket | <==> | server socket |
    |   <client>    |      |          < load balancer >              |      |    <server>   |
    +---------------+      +-----------------------------------------+      +---------------+
    Attributes:
        ip (str): virtual server's ip; client-side socket's ip
        port (int): virtual server's port; client-side socket's port
        algorithm (str): algorithm used to select a server
        flow_table (dict): mapping of client socket obj <==> server-side socket obj
        sockets (list): current connected and open socket obj
    """

    flow_table = dict()
    sockets = list()

    socket_counter = dict()

    def __init__(self, ip, port, algorithm='random'):
        self.ip = ip
        self.port = port
        self.algorithm = algorithm

        # init a client-side socket
        self.cs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # the SO_REUSEADDR flag tells the kernel to reuse a local socket in TIME_WAIT state,
        # without waiting for its natural timeout to expire.
        self.cs_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.cs_socket.bind((self.ip, self.port))
        print('init client-side socket: %s' % (self.cs_socket.getsockname(),))
        self.cs_socket.listen(10) # max connections
        self.sockets.append(self.cs_socket)

    def start(self):
        while True:
            read_list, write_list, exception_list = select.select(self.sockets, [], [])
            for sock in read_list:
                # new connection
                if sock == self.cs_socket:
                    #print('='*40+'flow start'+'='*39)
                    self.on_accept()
                    break
                # incoming message from a client socket
                else:
                    try:
                        # In Windows, sometimes when a TCP program closes abruptly,
                        # a "Connection reset by peer" exception will be thrown
                        data = sock.recv(4096) # buffer size: 2^n
                        if data:
                            self.on_recv(sock, data)
                        else:
                            self.on_close(sock)
                            break
                    except:
                        #print(sock)
                        #sock.on_close(sock)
                        self.on_close(sock)
                        break

    def on_accept(self):
        client_socket, client_addr = self.cs_socket.accept()
        #print('client connected: %s <==> %s' % (client_addr, self.cs_socket.getsockname()))
        # select a server that forwards packets to
        try:
            server = self.select_server(SERVER_POOL, self.algorithm)
        except LookupError:
            print('Empty server pool')
            return

        # init a server-side socket
        ss_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            #ss_socket.connect((server_ip, server_port))
            ss_socket.connect(server.server_address)
            #print('init server-side socket: %s' % (ss_socket.getsockname(),))
            #print('server connected: %s <==> %s' % (ss_socket.getsockname(),(socket.gethostbyname(server.server_address[0]), server.server_address[1])))
        except:
            #print("Can't establish connection with remote server, err: %s" % sys.exc_info()[0])
            #print("Closing connection with client socket %s" % (client_addr,))
            client_socket.close()
            SERVER_POOL.remove(server)
            return

        self.sockets.append(client_socket)
        self.sockets.append(ss_socket)

        self.flow_table[client_socket] = ss_socket
        self.flow_table[ss_socket] = client_socket

    def on_recv(self, sock, data):
        #print('recving packets: %-20s ==> %-20s, data: %s' % (sock.getpeername(), sock.getsockname(), [data]))
        # data can be modified before forwarding to server
        # lots of add-on features can be added here
        remote_socket = self.flow_table[sock]
        remote_socket.send(data)
        #print('sending packets: %-20s ==> %-20s, data: %s' % (remote_socket.getsockname(), remote_socket.getpeername(), [data]))

    def on_close(self, sock):
        #print('client %s has disconnected' % (sock.getpeername(),))
        #print('='*41+'flow end'+'='*40)

        ss_socket = self.flow_table[sock]

        try:
            self.sockets.remove(sock)
            self.sockets.remove(ss_socket)
        except:
            print('exception')

        sock.close()  # close connection with client
        ss_socket.close()  # close connection with server

        del self.flow_table[sock]
        del self.flow_table[ss_socket]

    def select_server(self, server_list, algorithm):
        if algorithm == 'random':
            return random.choice(server_list)
        #elif algorithm == 'round robin':
            #return round_robin(ITER)
        elif algorithm == 'minimal load':
            return min_load()
        else:
            raise Exception('unknown algorithm: %s' % algorithm)


# if __name__ == '__main__':
#     try:
#         ip = settings.SERVER_IP
#         port = int(settings.SERVER_PORT)
#         for sa in settings.TARGET_SERVERS[:-1]:
#             threading.Thread(target = my_target.run, kwargs={'server_address': sa, 'handler_class': my_target.HttpGetHandler}, daemon=True).start()
#         threading.Thread(target = my_target.run, kwargs={'server_address':settings.TARGET_SERVERS[-1], 'end_time':10, 'handler_class': my_target.HttpGetHandler}, daemon=True).start()
#         LB = LoadBalancer(ip, port, 'minimal load')
#         threading.Thread(target = client.spam, kwargs={'host': ip, 'port': port}, daemon=True).start()
#         LB.start()
#     except KeyboardInterrupt:
#         print("Ctrl C - Stopping load_balancer")
#         sys.exit(1)

def prepare_targets():

    for server_address in settings.TARGET_SERVERS:
        SERVER_POOL.append(ThreadingHTTPServer(server_address, my_target.HttpGetHandler))

    for httpd in SERVER_POOL[:-1]:
        threading.Thread(target=my_target.run,
                         kwargs={'httpd': httpd},
                         daemon=True).start()

    threading.Thread(target=my_target.run,
                     kwargs={'httpd': SERVER_POOL[-1],
                             'end_time': settings.LAST_SERVER_SHUTDOWN_TIMER},
                     daemon=True).start()

    threading.Timer(settings.LAST_SERVER_RESTART_TIMER, restart_last_server).start()

def restart_last_server():
    print('Restarting last server')
    httpd = ThreadingHTTPServer(settings.TARGET_SERVERS[-1], my_target.HttpGetHandler)
    threading.Thread(target=my_target.run,
                     kwargs={'httpd': httpd},
                     daemon=True).start()
    SERVER_POOL.append(httpd)

def start_spammer(ip, port):
    threading.Thread(target=client.spam, kwargs={'host': ip, 'port': port}, daemon=True).start()

def start_load_balancer(ip, port, algo):
    LB = LoadBalancer(ip, port, algo)
    LB.start()

if __name__ == '__main__':
    ip = settings.SERVER_IP
    port = int(settings.SERVER_PORT)
    alg = 'minimal load'
    try:
        if settings.TEST:
            prepare_targets()
            start_spammer(ip, port)
            start_load_balancer(ip, port, alg)
        else:
            start_load_balancer(ip, port, alg)

    except KeyboardInterrupt:
            print("Ctrl C - Stopping load_balancer")
            sys.exit(1)
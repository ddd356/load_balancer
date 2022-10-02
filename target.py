from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
import time
import threading
import logging
import settings

#logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG, format='%(asctime)s %(message)s')
logging.basicConfig(filename='server.log', level=logging.DEBUG, format='%(asctime)s %(message)s')

def logs(server):
    if server._BaseServer__is_shut_down._flag:
        return
    threading.Timer(settings.LOG_TIMER, logs, [server]).start()
    print(str(server.server_address) + ' ' + 'Threads: ' + str(server.thread_count))
    logging.debug(str(server.server_address) + ' ' + 'Threads: ' + str(server.thread_count))

def end_after(time, server):
    t = threading.Timer(time, shutdown_server, [server])
    t.start()

def shutdown_server(server):
    print('Shutting down server' + str(server.server_address))
    server.shutdown()
    server.server_close()

# def run1(server_class=ThreadingHTTPServer, handler_class=BaseHTTPRequestHandler, server_address=('127.0.0.1', 8000), end_time=0):
#
#   httpd = server_class(server_address, handler_class)
#   httpd.thread_count = 0
#   logs(httpd)
#   if end_time > 0:
#     end_after(end_time, httpd)
#   try:
#       httpd.serve_forever()
#   except KeyboardInterrupt:
#       httpd.server_close()

def run(httpd, end_time=0):

  httpd.thread_count = 0
  logs(httpd)
  if end_time > 0:
    end_after(end_time, httpd)
  try:
      httpd.serve_forever()
  except KeyboardInterrupt:
      httpd.server_close()

class HttpGetHandler(BaseHTTPRequestHandler):
    """Обработчик с реализованным методом do_GET."""

    def do_GET(self):
        global threadCount

        self.server.thread_count +=1
        time.sleep(settings.TARGET_SLEEP_TIMER)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # try:
        #     self.wfile.write('<html><head><meta charset="utf-8">'.encode())
        #     self.wfile.write('<title>Simple HTTP-server.</title></head>'.encode())
        #     self.wfile.write('<body>Answering GET-request.</body></html>'.encode())
        # except:
        #     pass
        self.server.thread_count -= 1

if __name__ == "__main__":
    run(handler_class=HttpGetHandler)
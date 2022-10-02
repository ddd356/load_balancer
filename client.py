import threading
import http.client

def spam(host = '127.0.0.1', port = 8000):
    threading.Timer(0.1, spam, [host, port]).start()
    connection = http.client.HTTPConnection(host, port)
    try:
        connection.request("GET", "/")
        response = connection.getresponse()
        #connection.getresponse()
        #print("Status: {} and reason: {}".format(response.status, response.reason))
        connection.close()
    except:
        print("spammer: exception")


if __name__ == "__main__":
    spam()
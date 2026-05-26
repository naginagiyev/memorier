import socket
from pyftpdlib.servers import FTPServer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.authorizers import DummyAuthorizer

PORT = 2121
USERNAME = "memorier"
PASSWORD = "memorier2026"
USB_PATH = "path\to\your\folder"

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

authorizer = DummyAuthorizer()
authorizer.add_user(USERNAME, PASSWORD, USB_PATH, perm="elradfmwMT")

handler = FTPHandler
handler.authorizer = authorizer
handler.passive_ports = range(60000, 60100)

ip = get_local_ip()
server = FTPServer(("0.0.0.0", PORT), handler)

print(f"✅ FTP Server running!")
print(f"📌 Host:     {ip}")
print(f"📌 Port:     {PORT}")
print(f"📌 Username: {USERNAME}")
print(f"📌 Password: {PASSWORD}")
print(f"📂 Serving:  {USB_PATH}")

server.serve_forever()
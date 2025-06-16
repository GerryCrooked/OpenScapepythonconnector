import socket
from time import strftime
import json
import sys
import os

status = ''

class messclient:
    server = None
    alldata = ''
    nest = 0
    quote = False
    name = "Python"
    user = "SYSTEM"

    def __init__(self, myname='Python', myuser='SYSTEM'):
        self.name = myname
        self.user = myuser
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect(('message', 50000))
        self.server.setblocking(False)

    def join(self, groupname):
        mess = {
            "to": "service",
            "command": "join",
            "group": groupname
        }
        self.send(mess)

    def read(self):
        m = self.realread()
        if m:
            try:
                if m.get('type') == 'ping':
                    reply = {
                        "to": m["sender"],
                        "type": "pong",
                        "replyfrom": self.name
                    }
                    self.send(reply)
                elif m.get('type') == 'status':
                    try:
                        computer_name = os.uname()[1]
                    except AttributeError:
                        computer_name = "unknown"
                    reply = {
                        "to": m["sender"],
                        "type": "statusreply",
                        "computer": computer_name,
                        "program": sys.argv[0],
                        "screen": status
                    }
                    self.send(reply)
            except Exception:
                pass
        return m

    def send(self, mess):
        mess["user"] = self.user
        mess["realto"] = mess["to"]
        mess["date"] = strftime("%Y-%m-%dT%H:%M:%S")
        # JSON serialisieren und als bytes senden
        data = json.dumps(mess).encode('utf-8')
        self.server.send(data)

    def realread(self):
        """
        Liest Nachrichten zeichenweise, erkennt vollständige JSON-Objekte am Nesting-Level.
        """
        try:
            data = self.server.recv(1)
            if not data:
                return None
            self.alldata += data.decode('utf-8')
            if not self.quote:
                if data.decode() in ["{", "["]:
                    self.nest += 1
                elif data.decode() == "\\":
                    d = self.server.recv(1)
                    self.alldata += d.decode('utf-8')
                elif data.decode() in ["}", "]"]:
                    self.nest -= 1
            if data.decode() == "\"":
                if self.quote:
                    self.nest -= 1
                else:
                    self.nest += 1
                self.quote = not self.quote
            if self.nest == 0 and len(self.alldata.strip()) > 0:
                try:
                    d = json.loads(self.alldata.strip())
                    self.alldata = ''
                    return d
                except Exception:
                    # JSON noch nicht vollständig
                    pass
        except Exception:
            pass
        return None

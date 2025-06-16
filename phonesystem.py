# phonesystem.py

import time
import socket
from pyasn1.codec.ber import encoder, decoder
from pyasn1.type import univ, char, namedtype, tag

from acsespec import *
from rose import *
import cstautils
import config

class PhoneSystem:
    id = 0
    connect = None
    hostname = (config.PBX_IP, config.PBX_PORT)
    last = time.time()
    outdebug = False
    indebug = False
    group = "phone"
    server = None
    calls = {}
    usernames = {}
    presence_status = {}

    def __init__(self, host=(config.PBX_IP, config.PBX_PORT), sendto='phone', serv=None):
        self.hostname = host
        self.connect = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.startup(self.hostname)
        self.group = sendto
        self.server = serv
        self.mydb = None
        for ext in config.EXTENSIONS_TO_MONITOR:
            self.presence_status[ext] = "Initialisiere..."

    def startup(self, hostname):
        self.connect.connect(hostname)
        self.connect.setblocking(False)
        
    def timeout(self):
        tm = 20 - (time.time() - self.last)
        return max(tm, 0)

    def resetTimeout(self):
        self.last = time.time()

    def sendAuthenticationRequest(self):
        print("Sende Authentifizierungsanfrage...")
        
        aarq = AARQ_apdu()
        aarq_schema = aarq.getComponentType()
        
        app_context_wrapper = aarq_schema['application-context-name']
        app_context_schema = app_context_wrapper.getType()
        app_context_value = app_context_schema.clone().setComponentByName('', univ.ObjectIdentifier('1.3.12.0.180.1'))
        aarq.setComponentByName('application-context-name', app_context_value)

        if config.CSTA_USER and config.CSTA_PASSWORD:
            print("Versuche Anmeldung mit Benutzername und Passwort...")
            auth_string = f"user={config.CSTA_USER},passwd={config.CSTA_PASSWORD}"
            private_data_choice = CSTAPrivateDataData().setComponentByName('string', auth_string.encode('ascii'))
            login_info = CSTAPrivateData()
            login_info.setComponentByName('manufacturer', univ.ObjectIdentifier('1.3.12.2.218.200'))
            login_info.setComponentByName('data', private_data_choice)
            encoded_login_info = encoder.encode(login_info)

            user_info_wrapper = aarq_schema['user-information']
            user_info_schema = user_info_wrapper.getType()
            user_info_value = user_info_schema.clone()
            
            ext_schema = user_info_value.getComponentType()
            ext_value = ext_schema.clone()
            
            oid_value = univ.ObjectIdentifier('1.3.12.2.218.1.1.1')
            ext_value.setComponentByName('direct-reference', oid_value)

            encoding_value = ext_value.getComponentByName('encoding')
            encoding_value.setComponentByName('single-ASN1-type', encoded_login_info)
            
            user_info_value.setComponentByPosition(0, ext_value)

            aarq.setComponentByName('user-information', user_info_value)
        else:
            print("Versuche passwortlose Anmeldung...")

        self.sendMess(aarq)

    def sendMess(self, mess):
        dat = encoder.encode(mess)
        if self.outdebug:
          print(f"OUT Hex:  {dat.hex()}")
          print(f"OUT ASN1: {mess.prettyPrint()}")
        
        header = b'\x00' + bytes([len(dat)])
        self.connect.sendall(header + dat)

    def NextID(self):
        self.id += 1
        return self.id

    def readmess(self):
        try:
          header = self.connect.recv(2)
          if not header or len(header) < 2:
            return b'' 
          
          length = header[1]
          
          payload = b''
          while len(payload) < length:
            chunk = self.connect.recv(length - len(payload))
            if not chunk:
              return b'' 
            payload += chunk
          return payload 
        except (socket.error, BlockingIOError):
          return b''

    def handleCsta(self, data):
        if not data:
          return
        
        if data == b'P':
            self.sendAuthenticationRequest()
            return

        if self.indebug:
          print(f"IN  Hex:  {data.hex()}")
        try:
          decoded_msg, remaining_bytes = decoder.decode(data, asn1Spec=Rose())
          if self.indebug:
            print(f"IN  ASN1: {decoded_msg.prettyPrint()}")

          obj = decoded_msg.getComponent()
          if obj.isSameTypeWith(AARE_apdu()):
            self.handleAARE(obj)
          elif obj.isSameTypeWith(ReturnResult()):
            self.handleResult(obj)
          elif obj.isSameTypeWith(Invoke()):
            opcode = int(obj.getComponentByName('opcode'))
            self.handleInvoke(opcode, obj)
          elif obj.isSameTypeWith(ABRT_apdu()):
             print("Formelle ABRT-Nachricht (Abbruch) von der Anlage empfangen.")
          elif obj.isSameTypeWith(Reject()):
             print("Formelle REJECT-Nachricht (Ablehnung) von der Anlage empfangen.")
          else:
             print("Unbekannter Nachrichtentyp empfangen.")

        except Exception as e:
          print(f"Fehler beim Dekodieren der Nachricht: {e}")
          print(f"Problematische Hex-Daten: {data.hex()}")

    def handleAARE(self, aare_obj):
        print("\n**************************************************")
        print("***** ERFOLG! Antwort der Anlage empfangen! *****")
        print("**************************************************\n")
        print("Die Authentifizierung wurde von der Anlage akzeptiert.")
        print("Der Inhalt der Antwort wird zur Analyse ausgegeben:")
        print(aare_obj.prettyPrint())
        
        print("\nStarte Überwachung der Nebenstellen...")
        self.StartUpMonitors()

    def SendStatus(self):
        print("Sende System Status Request (Heartbeat)...")
        result = invoke(52)
        result.setComponentByName('opcode', 52)
        result.setComponentByName('invokeid', self.NextID())
        args_choice = args(52)
        args_choice.setComponentByName('systemStatus', CSTACommonArguments())
        result.setComponentByName('args', args_choice)
        ret = Rose(52)
        ret.setComponentByName('invoke', result)
        self.sendMess(ret)
        self.resetTimeout()

    def StartMonitor(self, ext):
        print(f"Starte Monitor für Nebenstelle: {ext}")
        m = invoke(71)
        m.setComponentByName('invokeid', self.NextID())
        m.setComponentByName('opcode', 71)
        
        # --- KORREKTER, STRUKTURIERTER AUFBAU DER NACHRICHT ---
        arg_seq = ArgumentSeq()
        
        mon_obj = CSTAObject()
        dev_id = DeviceID()
        dev_id.setComponentByName('dialingNumber', NumberDigits(ext))
        mon_obj.setComponentByName('device', dev_id)
        
        arg_parts = ArgumentSeqParts()
        arg_parts.setComponentByName('moniterObject', mon_obj)
        
        arg_seq.setComponentByPosition(0, arg_parts)
        
        args_choice = args(71)
        args_choice.setComponentByName('ArgSeq', arg_seq)
        
        m.setComponentByName('args', args_choice)
        
        self.sendMess(m)

    def StartUpMonitors(self):
        for ext in config.EXTENSIONS_TO_MONITOR:
          self.StartMonitor(ext)
          time.sleep(0.1)

    def handleResult(self, result_obj):
        invoke_id = int(result_obj.getComponentByName('invokeid'))
        print(f"Ergebnis für InvokeID {invoke_id} erhalten.")
        if self.indebug:
          print(result_obj.prettyPrint())

    def handleInvoke(self, opcode, invoke_obj):
        if opcode == 21:
          self.handleEvent(invoke_obj)
        elif opcode == 52:
          print("System Status von PBX abgefragt, sende Antwort...")
          result = ReturnResult()
          result.setComponentByName('invokeid', invoke_obj.getComponentByName('invokeid'))
          res_args = Result()
          res_seq = ResultSeq()
          res_seq.setComponentByPosition(0, univ.Choice().setComponentByName('opcode', univ.Integer(52)))
          res_seq.setComponentByPosition(1, univ.Choice().setComponentByName('null', univ.Null()))
          res_args.setComponentByName('ResultSeq', res_seq)
          ret = Rose()
          ret.setComponentByName('returnResult', result)
          self.sendMess(ret)
        else:
          print(f"Unbehandelter Invoke-Opcode empfangen: {opcode}")
          if self.indebug:
            print(invoke_obj.prettyPrint())

    def handleEvent(self, event_obj):
        args_seq = event_obj.getComponentByName("args").getComponentByName("ArgSeq")
        event_type_id = -1
        event_info_obj = None
        for part in args_seq:
          choice = part.getComponent()
          if choice.isSameTypeWith(EventTypeID()):
            event_type_id = int(choice.getComponentByName("cSTAform"))
          elif choice.isSameTypeWith(EventInfo()):
            event_info_obj = choice
        if event_info_obj:
          parsed_event = cstautils.EventInfo(event_info_obj, event_type_id, "", self)
          if parsed_event.dest and parsed_event.dest in self.presence_status:
            neuer_status = self.presence_status[parsed_event.dest]
            if parsed_event.eventtype in ['Established', 'Conference', 'Transferred']:
              neuer_status = f"Im Gespräch (mit {parsed_event.calling or parsed_event.called or 'unbekannt'})"
            elif parsed_event.eventtype in ['Hold']:
                neuer_status = "Im Gespräch (gehalten)"
            elif parsed_event.eventtype in ['Delivered', 'Reached', 'Originated']:
                neuer_status = "Klingelt"
            elif parsed_event.eventtype in ['Cleared', 'CallCleared']:
                neuer_status = "Verfügbar"
            elif parsed_event.eventtype in ['AgentNotReady', 'OutOfService', 'DoNotDisturb']:
                neuer_status = "Nicht verfügbar"
            elif parsed_event.eventtype == 'AgentLoggedOff':
                neuer_status = "Abgemeldet"
            elif parsed_event.eventtype in ['AgentReady', 'BackInService', 'AgentLoggedOn']:
                neuer_status = "Verfügbar"
            if self.presence_status[parsed_event.dest] != neuer_status:
                self.presence_status[parsed_event.dest] = neuer_status
                self.print_presence_report()

    def print_presence_report(self):
        print("\n--- PRÄSENZSTATUS-UPDATE ---")
        print("=" * 30)
        for ext, status in self.presence_status.items():
            print(f"Nebenstelle: {ext:<10} | Status: {status}")
        print("=" * 30)
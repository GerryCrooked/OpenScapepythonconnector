# cstautils.py

from pyasn1.type import univ
import config
from rose import *

# Event-Typ-Namen bleiben unverändert
eventtypes = {
  1: 'CallCleared', 2: 'Conference', 3: 'Cleared', 4: 'Delivered', 5: 'Diverted',
  6: 'Established', 7: 'Failed', 8: 'Hold', 9: 'Reached', 10: 'Originated',
  11: 'Queued', 12: 'Retrieved', 13: 'Initiated', 14: 'Transferred',
  101: 'CallInfo', 102: 'DoNotDisturb', 103: 'Forwarding', 104: 'MessageWaiting',
  201: 'AgentLoggedOn', 202: 'AgentLoggedOff', 203: 'AgentNotReady', 204: 'AgentReady',
  205: 'AgentWorkNotReady', 206: 'AgentWorkReady', 301: 'BackInService',
  302: 'OutOfService', 401: 'PrivateEvent'
}

def getPhoneNum(device_object):
    """ Extrahiert eine Telefonnummer aus verschiedenen DeviceID-Typen. """
    if not device_object:
        return None
    
    component = device_object.getComponent()
    
    # Navigiere durch die verschachtelten Strukturen
    if component.isSameTypeWith(ExtendedDeviceID()):
        component = component.getComponent()
    if component.isSameTypeWith(DeviceID()):
        component = component.getComponent()
    
    # Endgültige Prüfung
    if component.isSameTypeWith(univ.Null()) or str(component) == '':
        return None
        
    return str(component)

def isLocal(phonenum):
    """ Prüft, ob eine Nummer in unserer Liste der überwachten Nebenstellen ist. """
    return phonenum in config.EXTENSIONS_TO_MONITOR

class EventInfo:
  """
  Diese Klasse zerlegt das komplexe EventInfo-Objekt von der PBX
  in leichter handhabbare Attribute.
  """
  def __init__(self, event_info_obj, event_type_id, monitor_cross_ref_id, callstate_manager):
    self.eventtype = eventtypes.get(event_type_id, f'Unknown_{event_type_id}')
    self.dest = None
    self.calling = None
    self.called = None
    self.cause = None
    
    # Durchlaufe alle Teile des Events und extrahiere die Informationen
    for part in event_info_obj:
        choice = part.getComponent()
        
        # Die Nebenstelle, auf die sich das Event bezieht (z.B. wer den Hörer abhebt)
        if choice.isSameTypeWith(SubjectDeviceID()):
            self.dest = getPhoneNum(choice)

        # Wer ruft an?
        elif choice.isSameTypeWith(CallingDeviceID()):
            self.calling = getPhoneNum(choice)

        # Wer wird angerufen?
        elif choice.isSameTypeWith(CalledDeviceID()):
            self.called = getPhoneNum(choice)
            
        # Grund für das Event (z.B. "busy", "noAnswer")
        elif choice.isSameTypeWith(univ.Enumerated()):
            self.cause = str(choice)
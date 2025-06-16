#!/usr/bin/env python3

import socket
import select
import time
import sys
# Lokale Module importieren
import phonesystem
import config

def main():
    """
    Hauptfunktion zum Starten des CSTA-Monitors.
    """
    print("Starte CSTA Presence Monitor...")
    print(f"Verbinde mit PBX auf {config.PBX_IP}:{config.PBX_PORT}")

    phone_system = None # Vorab definieren für den finally-Block
    try:
        phone_system = phonesystem.PhoneSystem(
            host=(config.PBX_IP, config.PBX_PORT)
        )
        phone_system.indebug = config.DEBUG_INCOMING
        phone_system.outdebug = config.DEBUG_OUTGOING

    except ConnectionRefusedError:
        print(f"Fehler: Verbindung zu {config.PBX_IP}:{config.PBX_PORT} wurde abgelehnt.")
        print("Stelle sicher, dass die IP und der Port korrekt sind und der CSTA-Dienst auf der Anlage läuft.")
        sys.exit(1)
    except OSError as e:
        print(f"Netzwerkfehler: {e}")
        sys.exit(1)

    print("Verbindung erfolgreich hergestellt.")
    phone_system.sendAuthenticationRequest()

    try:
        while True:
            readable, _, exceptional = select.select(
                [phone_system.connect],
                [],
                [phone_system.connect],
                phone_system.timeout() + 0.1
            )

            if exceptional:
                print("!!! Socket-Fehler aufgetreten. Verbindung wird beendet. !!!")
                break

            for sock in readable:
                csta_data = phone_system.readmess()
                if csta_data:
                    phone_system.handleCsta(csta_data)
                else:
                    # --- NEUE DIAGNOSE-LOGIK ---
                    # recv() gibt leere Bytes zurück -> die Gegenseite hat die Verbindung geschlossen.
                    print("\n!!! Verbindung wurde von der Telefonanlage geschlossen. !!!")
                    print("----------------------------------------------------------")
                    print("Mögliche Ursachen:")
                    print("  1. Falscher User/Passwort in config.py.")
                    print("  2. CSTA-Benutzer auf der Anlage nicht berechtigt oder Dienst deaktiviert.")
                    print("  3. Die von uns gesendeten Protokoll-OIDs sind für diese Anlage falsch.")
                    print("----------------------------------------------------------")
                    # Schleife und Programm beenden
                    return

            if not readable and not exceptional:
                phone_system.SendStatus()

    except KeyboardInterrupt:
        print("\nMonitor wird durch Benutzer beendet.")
    finally:
        if phone_system and phone_system.connect:
            phone_system.connect.close()
            print("Verbindung geschlossen.")

if __name__ == "__main__":
    main()
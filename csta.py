# csta.py (korrigiert)

import binascii
from rose import *

from pyasn1.codec.ber import decoder, encoder
from pyasn1.type import univ

inp1 = (
    'a1720201010201337e6aa1687d660606'
    '2b0c89368374045c0103e80000000000'
    '0003e900000000000000000000000000'
    '00000000000000000000000000000000'
    '00000000000000000000000000000000'
    '00000000000000000000000000000000'
    '00000000000000000000000000000000'
    '00000000'
)

inp = (
    'a22e020203e830280201347d2306062b'
    '0c8936837404190301000013888ec90b'
    '61b59ffe4d8bd6ef1fb0fd798926d400'
)

inp = (
    'a1720201020201337e6aa1687d66'
    '06062b0c89368374045c0103e8000000'
    '00000003e90000000000000000000000'
    '00000000000000000000000000000000'
    '00000000000000000000000000000000'
    '00000000000000000000000000000000'
    '00000000000000000000000000000000'
    '000000000000'
)

# Der Dekodierungs-Teil bleibt unverändert
input_bytes = binascii.unhexlify(inp1)
print("--- Dekodierte Eingabe ---")
print(decoder.decode(input_bytes, asn1Spec=rose)[0])
print("--------------------------\n")


# --- KORRIGIERTER TEIL FÜR DIE KODIERUNG ---
print("--- Neu kodierte Ausgabe ---")

# Das Hauptobjekt, das die Nachricht enthält
stat = Rose()

# Das 'returnResult'-Objekt
result = ReturnResult()
result.setComponentByName('opcode', univ.Integer(52))
result.setComponentByName('invokeid', 1000)

# --- KORREKTUR START ---
# Anstatt direkt univ.Null() zuzuweisen, erstellen wir zuerst ein 'Result'-Objekt.
# Laut rose.py muss die 'args'-Komponente vom Typ 'Result' sein.
result_args = Result()

# Innerhalb dieses 'Result'-Objekts wählen wir die 'null'-Option aus.
result_args.setComponentByName('null', univ.Null())

# Jetzt weisen wir das korrekt typisierte 'result_args'-Objekt der 'args'-Komponente zu.
result.setComponentByName('args', result_args)
# --- KORREKTUR ENDE ---


# Das fertige 'result'-Objekt wird in das 'stat'-Hauptobjekt eingefügt.
stat.setComponentByName('returnResult', result)

# Die Nachricht kodieren und als Hex-String ausgeben.
print(encoder.encode(stat).hex())
print("--------------------------")
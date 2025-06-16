import rose
from acsespec import *
from pyasn1.type import univ, tag
from pyasn1.codec.ber import encoder, decoder

sec = '600aa10806062b0c00813401'
input_bytes = bytes.fromhex(sec)  # Hex-String zu Bytes

# Decode das input_bytes mit rose.rose als ASN.1-Spezifikation
security, _ = decoder.decode(input_bytes, asn1Spec=rose.rose)

# ApplicationContextName mit implizitem Kontext-Tag 1 erzeugen
app = ApplicationContextName().subtype(
    implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)
)
app.setComponentByName('', univ.ObjectIdentifier('1.3.12.0.180.1'))
# Alternativ: '1.3.12.0.218.200'
# app.setComponentByName('', univ.ObjectIdentifier('1.3.12.0.218.200'))

# Neues AARQ_apdu-Objekt erstellen mit application-context-name gesetzt
security = AARQ_apdu().setComponentByName('application-context-name', app)

print("ASN.1 Objekt security:")
print(security)

print("\nUrsprünglicher Hex-String:")
print(sec)

encoded = encoder.encode(security)
print("\nEncodiertes security als Hex:")
print(encoded.hex())

print("\nVergleich original Hex == encodiert:")
print(sec.lower() == encoded.hex())

decoded_again, _ = decoder.decode(encoded, asn1Spec=rose.rose)
print("\nDecodiertes Objekt aus Encodiertem:")
print(decoded_again)

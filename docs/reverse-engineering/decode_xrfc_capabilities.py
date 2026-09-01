"""Decode FUJIFILM X RAW STUDIO's XRFC.DAT capability database into plain XML.

XRFC.DAT ships next to XRFC.dll in the official X RAW STUDIO install
(``C:\\Program Files\\FUJIFILM X RAW STUDIO\\`` on Windows). It is not
encrypted for security -- it's a light obfuscation format used to keep the
per-model tethered-RAW capability table out of a plain-text resource. The
cipher was recovered by decompiling ``CapabilityClass::ReadCapabilityFile``
and the function it calls to decode the payload (Ghidra 12.1.3, XRFC.dll).
See xrfc-capability-database.md for the full writeup and the
already-decoded reference XML.

Format, all fields little-endian:

    offset  size  field
    0       8     magic, must equal 0xFEDCBA9876543210
    8       8     "RandomValue" -- a per-file XOR seed
    16      8     "Time" -- a timestamp, logged but not used in decoding
    24      N     payload, decoded 8 bytes at a time (see below)

Decoding each 8-byte payload chunk:

    1. natural = chunk XOR RandomValue XOR 0xAA559966AA559966
       (natural[0] is the LSB of the XOR result, natural[7] the MSB)
    2. every full chunk except the last is then byte-permuted:
       output[i] = natural[i XOR PHASE_MASK[chunk_index % 4]]
       where PHASE_MASK = [7, 1, 4, 2] (chunk_index is 0-based, counting
       only full 8-byte chunks after the 24-byte header)
    3. the final, possibly-partial chunk (payload_len % 8 bytes) is used
       as-is with no permutation -- just the low N bytes of `natural`.

The decoded payload is a UTF-8 XML document (Boost.PropertyTree XML, per
the DLL's own error strings): a <ConversionCaps> tree mapping
"<Model>_<FirmwareHex>" device strings to a named <PropertyGroup> of
per-property true/false support flags.
"""

import struct
import sys

PHASE_MASK = [7, 1, 4, 2]
MAGIC = 0xFEDCBA9876543210
XOR_CONST = 0xAA559966AA559966


def decode(data: bytes) -> bytes:
    magic, random_value, _time_val = struct.unpack_from("<QQQ", data, 0)
    if magic != MAGIC:
        raise ValueError("bad magic 0x%016x, expected 0x%016x" % (magic, MAGIC))

    body = data[24:]
    key = random_value ^ XOR_CONST

    out = bytearray()
    nfull = len(body) // 8
    tail = len(body) % 8

    for i in range(nfull):
        chunk = struct.unpack_from("<Q", body, i * 8)[0]
        natural = struct.pack("<Q", chunk ^ key)
        mask = PHASE_MASK[i % 4]
        out += bytes(natural[b ^ mask] for b in range(8))

    if tail:
        chunk_bytes = body[nfull * 8 :] + b"\x00" * (8 - tail)
        chunk = struct.unpack_from("<Q", chunk_bytes, 0)[0]
        natural = struct.pack("<Q", chunk ^ key)
        out += natural[:tail]

    return bytes(out)


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: decode_xrfc_capabilities.py <path to XRFC.DAT> <output .xml path>")
        raise SystemExit(1)
    data = open(sys.argv[1], "rb").read()
    decoded = decode(data)
    with open(sys.argv[2], "wb") as f:
        f.write(decoded)
    print("wrote %d bytes to %s" % (len(decoded), sys.argv[2]))


if __name__ == "__main__":
    main()

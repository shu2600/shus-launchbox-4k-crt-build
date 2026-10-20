"""Decode an ECM file (Neill Corlett's CD sector compressor) back to the original image, in Python + numpy.
ECM strips the sync/header/EDC/ECC bytes that can be regenerated; this puts them back.
Usage: py -I unecm.py <in.ecm> [out]   (out defaults to the name without .ecm)"""
import sys, numpy as np

F = np.zeros(256, np.uint8); B = np.zeros(256, np.uint8); EDC = np.zeros(256, np.uint32)
for i in range(256):
    j = ((i << 1) ^ (0x11D if i & 0x80 else 0)) & 0xFF
    F[i] = j; B[i ^ j] = i
    e = i
    for _ in range(8):
        e = (e >> 1) ^ (0xD8018001 if e & 1 else 0)
    EDC[i] = e


def edc(block):                       # block: (N, L) uint8 -> (N,) uint32
    e = np.zeros(block.shape[0], np.uint32)
    for k in range(block.shape[1]):
        e = (e >> np.uint32(8)) ^ EDC[(e ^ block[:, k]) & 0xFF]
    return e


def ecc_index(major_count, minor_count, major_mult, minor_inc):
    size = major_count * minor_count
    idx = np.zeros((major_count, minor_count), np.int64)
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        for minor in range(minor_count):
            idx[major, minor] = index
            index += minor_inc
            if index >= size:
                index -= size
    return idx

P_IDX = ecc_index(86, 24, 2, 86)
Q_IDX = ecc_index(52, 43, 86, 88)


def ecc_block(src, idx):              # src (N, size) -> (N, 2*major)
    vals = src[:, idx]                # (N, major, minor)
    a = np.zeros(vals.shape[:2], np.uint8); b = np.zeros(vals.shape[:2], np.uint8)
    for m in range(vals.shape[2]):
        t = vals[:, :, m]
        a ^= t; b ^= t; a = F[a]
    a = B[F[a] ^ b]
    return np.concatenate([a, a ^ b], axis=1)


def ecc(sec, zero_address):
    if zero_address:
        saved = sec[:, 0xC:0x10].copy(); sec[:, 0xC:0x10] = 0
    sec[:, 0x81C:0x81C + 172] = ecc_block(sec[:, 0xC:0xC + 2064], P_IDX)
    sec[:, 0x8C8:0x8C8 + 104] = ecc_block(sec[:, 0xC:0xC + 2236], Q_IDX)
    if zero_address:
        sec[:, 0xC:0x10] = saved


def put32(sec, off, v):
    sec[:, off:off + 4] = v.view(np.uint8).reshape(-1, 4)


SYNC = np.array([0] + [0xFF] * 10 + [0], np.uint8)


def decode(src, dst):
    f = open(src, "rb"); o = open(dst, "wb")
    if f.read(4) != b"ECM\0":
        raise SystemExit("not an ECM file")
    while True:
        c = f.read(1)[0]; typ = c & 3; num = (c >> 2) & 0x1F; bits = 5
        while c & 0x80:
            c = f.read(1)[0]; num |= (c & 0x7F) << bits; bits += 7
        if num == 0xFFFFFFFF:
            break
        num += 1
        if typ == 0:
            while num:
                n = min(num, 1 << 24); o.write(f.read(n)); num -= n
            continue
        while num:
            n = min(num, 8192); num -= n
            sec = np.zeros((n, 2352), np.uint8)
            if typ == 1:
                raw = np.frombuffer(f.read(n * 2051), np.uint8).reshape(n, 2051)
                sec[:, :12] = SYNC; sec[:, 0xC:0xF] = raw[:, :3]; sec[:, 0xF] = 1; sec[:, 0x10:0x810] = raw[:, 3:]
                put32(sec, 0x810, edc(sec[:, :0x810]))
                ecc(sec, False)
                o.write(sec.tobytes())
            else:
                ln = 0x804 if typ == 2 else 0x918
                raw = np.frombuffer(f.read(n * ln), np.uint8).reshape(n, ln)
                sec[:, 0xF] = 2; sec[:, 0x14:0x14 + ln] = raw; sec[:, 0x10:0x14] = sec[:, 0x14:0x18]
                if typ == 2:
                    put32(sec, 0x818, edc(sec[:, 0x10:0x818]))
                    ecc(sec, True)
                else:
                    put32(sec, 0x92C, edc(sec[:, 0x10:0x92C]))
                o.write(sec[:, 0x10:0x10 + 2336].tobytes())
    o.close()


if __name__ == "__main__":
    a = sys.argv[1:]
    decode(a[0], a[1] if len(a) > 1 else a[0][:-4])

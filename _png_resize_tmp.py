import glob, os, struct, zlib

TARGET_W = 800

def read_png(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'\x89PNG\r\n\x1a\n', 'not png'
    pos, idat, W, H, bd, ct = 8, b'', None, None, None, None
    while pos < len(d):
        ln = struct.unpack('>I', d[pos:pos+4])[0]
        typ = d[pos+4:pos+8]; data = d[pos+8:pos+8+ln]
        if typ == b'IHDR':
            W, H, bd, ct = struct.unpack('>IIBB', data[:10])
        elif typ == b'IDAT':
            idat += data
        elif typ == b'IEND':
            break
        pos += 12 + ln
    assert bd == 8, f'bitdepth {bd} not supported'
    ch = {0:1, 2:3, 4:2, 6:4}[ct]
    raw = zlib.decompress(idat); stride = W * ch
    out, prev, p = bytearray(), bytearray(stride), 0
    for _ in range(H):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p+stride]); p += stride
        if f == 1:
            for i in range(stride):
                a = line[i-ch] if i >= ch else 0
                line[i] = (line[i] + a) & 0xff
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xff
        elif f == 3:
            for i in range(stride):
                a = line[i-ch] if i >= ch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xff
        elif f == 4:
            for i in range(stride):
                a = line[i-ch] if i >= ch else 0
                c = prev[i-ch] if i >= ch else 0
                pp = a + prev[i] - c
                pa, pb, pc = abs(pp-a), abs(pp-prev[i]), abs(pp-c)
                pr = a if (pa <= pb and pa <= pc) else (prev[i] if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xff
        out += line; prev = line
    return W, H, ch, ct, bytes(out)

def resize(px, W1, H1, ch, W2, H2):
    out = bytearray()
    for y2 in range(H2):
        y1 = (y2 + 0.5) * H1 / W2 - 0.5
        y0 = max(0, int(y1)); y1c = min(H1-1, y0+1); dy = y1 - y0
        for x2 in range(W2):
            x1 = (x2 + 0.5) * W1 / W2 - 0.5
            x0 = max(0, int(x1)); x1c = min(W1-1, x0+1); dx = x1 - x0
            def g(ix, iy):
                o = (iy*W1 + ix)*ch
                return px[o:o+ch]
            c00, c10, c01, c11 = g(x0,y0), g(x1c,y0), g(x0,y1c), g(x1c,y1c)
            npix = bytearray(ch)
            for c in range(ch):
                v = (c00[c]*(1-dx)*(1-dy) + c10[c]*dx*(1-dy) + c01[c]*(1-dx)*dy + c11[c]*dx*dy)
                npix[c] = max(0, min(255, int(round(v))))
            out += npix
    return bytes(out)

def write_png_paeth(path, W, H, ch, ct, px):
    stride = W * ch
    raw = bytearray()
    prev = bytearray(stride)
    for y in range(H):
        line = px[y*stride:(y+1)*stride]
        flt = bytearray(stride)
        for i in range(stride):
            a = line[i-ch] if i >= ch else 0
            b = prev[i]
            c = prev[i-ch] if i >= ch else 0
            p = a + b - c
            pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
            pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            flt[i] = (line[i] - pr) & 0xff
        raw.append(4)  # Paeth
        raw += flt
        prev = line
    comp = zlib.compress(bytes(raw), 9)
    def chunk(typ, data):
        return struct.pack('>I', len(data)) + typ + data + struct.pack('>I', zlib.crc32(typ+data) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', W, H, 8, ct, 0, 0, 0)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', comp) + chunk(b'IEND', b''))

def dim(path):
    return struct.unpack('>II', open(path, 'rb').read(33)[16:24])

if __name__ == '__main__':
    for src in sorted(glob.glob('evidence/recon-ai/shots/*.png')):
        name = os.path.basename(src)
        W1, H1, ch, ct, px = read_png(src)
        W2 = TARGET_W
        H2 = max(1, int(round(H1 * W2 / W1)))
        dst = os.path.join('report/assets', name)
        write_png_paeth(dst, W2, H2, ch, ct, resize(px, W1, H1, ch, W2, H2))
        nw, nh = dim(dst)
        assert (nw, nh) == (W2, H2)
        print(f'{name:28s} {W1}x{H1} -> {nw}x{nh}  {os.path.getsize(dst)/1024:.1f} KB')
    print('DONE')

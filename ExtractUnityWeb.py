import sys
import os
import gzip
import struct

def gunzip(in_name, out_name):
    with gzip.open(in_name, mode='rb') as f:
        data = f.read()
    with open(out_name, 'wb') as f:
        f.write(data)

def extract(filepath):
    f = open(filepath, 'rb')
    # Read header
    magic = f.read(16)
    if magic != b'UnityWebData1.0\x00':
        print("[-] Invalid header: " + repr(magic))
        return
    header_length = struct.unpack('<I', f.read(4))[0]
    print("[+] Header length: " + hex(header_length))
    offset = 16 + 4
    # Extract files
    while offset < header_length:
        packet = struct.unpack('<III', f.read(12))
        data_offset, data_length, path_length = packet
        path = f.read(path_length).decode()
        print("- {0} ({1} bytes)".format(path, data_length))
        try:
            os.makedirs('UnityWebData/' + os.path.dirname(path))
        except:
            pass
        whereami = f.tell()
        with open('UnityWebData/' + path, 'wb') as fout:
            f.seek(data_offset)
            data = f.read(data_length)
            fout.write(data)
        f.seek(whereami)
        # Next file
        offset += 12 + path_length

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: {0} run.data.unityweb\n".format(sys.argv[0]))
        print("This script extracts all files from UnityWeb data file. "
              "The target filename is generally named `run.data.unityweb`.")
        exit(1)
    # Gunzip
    created = False
    filepath = sys.argv[1] + '.raw'
    try:
        gunzip(sys.argv[1], filepath)
        print("[+] Decompressed " + sys.argv[1])
        created = True
    except:
        with open(sys.argv[1], 'rb') as f:
            magic = f.read(16)
        if magic == b'UnityWebData1.0\x00':
            print("[+] You specified decompressed file")
            filepath = sys.argv[1]
        else:
            print("[-] Invalid header: " + repr(magic))
            exit(1)
    # Extract
    extract(filepath)
    print("[+] Exiting...")
    # Remove temp file
    if created:
        os.remove(filepath)

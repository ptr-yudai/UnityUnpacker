#!/usr/bin/env python
import sys
import os
import struct
import gzip
try:
    import lzma
except ImportError:
    try:
        import backports.lzma
    except ImportError:
        print("[-] Some UnityFS files requires lzma")
        print("[-] Run `pip install backports.lzma`")
        print("[-] https://pypi.org/project/backports.lzma/")
try:
    import lz4.frame
    import lz4.block
except ImportError:
    print("[-] Some UnityFS files requires lz4")
    print("[-] Run `pip install lz4`")
    print("[-] https://pypi.org/project/lz4/")

def gunzip(in_name, out_name):
    with gzip.open(in_name, mode='rb') as f:
        data = f.read()
    with open(out_name, 'wb') as f:
        f.write(data)

def decompress(data, compress_type, size=-1):
    if compress_type == 1:
        # LZMA
        d = lzma.LZMADecompressor()
        data = d.decompress(data)
        print("[+] Decompressed with LZMA")
    elif compress_type == 2:
        # LZ4
        if size == -1:
            data = lz4.frame.decompress(data)
        else:
            data = lz4.frame.decompress(data, size)
        print("[+] Decompressed with LZ4")
    elif compress_type == 3:
        # LZ4HC
        if size == -1:
            data = lz4.block.decompress(data)
        else:
            data = lz4.block.decompress(data, size)
    elif compress_type == 4:
        # LZHAM
        print("[-] The block is compressed with LZHAM, which is not supported")
        return None
    return data
    
def extract(filepath):
    f = open(filepath, 'rb')
    # Read header
    magic = f.read(8)
    if magic != 'UnityFS\x00':
        print("[-] Invalid header: " + repr(magic))
        return
    version = struct.unpack('>I', f.read(4))[0]
    major_version = ''
    while True:
        c = f.read(1)
        if c == '\x00': break
        major_version += c
    unity_version = ''
    while True:
        c = f.read(1)
        if c == '\x00': break
        unity_version += c
    file_size = struct.unpack('>Q', f.read(8))[0]
    ciblock_size = struct.unpack('>I', f.read(4))[0]
    uiblock_size = struct.unpack('>I', f.read(4))[0]
    flags = struct.unpack('>I', f.read(4))[0]
    print("[+] Format Version: " + str(version))
    print("[+] Unity Major Version: " + major_version)
    print("[+] Unity Version: " + unity_version)
    print("[+] File Size = {0} bytes".format(file_size))
    print("[+] Compressed Block Size = {0} bytes".format(ciblock_size))
    print("[+] Decompressed Block Size = {0} bytes".format(uiblock_size))
    print("[+] flags = " + bin(flags))
    compress_type = flags & 0x3f
    has_dir_info = flags & 0x40
    dir_list_end = flags & 0x80
    compress_algs = ['Not Compressed', 'LZMA', 'LZ4', 'LZ4HC', 'LZHAM']
    print("[+] Compression Type: " + compress_algs[compress_type])
    end_of_header = f.tell()
    if has_dir_info:
        print("[+] This bundle has a directory info")
    if dir_list_end:
        print("[+] The block and directory list is located at the end of this bundle")
        f.seek(-ciblock_size, 2)
    blocks_container = f.read(ciblock_size)
    blocks_container = decompress(blocks_container, compress_type, uiblock_size)
    # Blocks
    guid = blocks_container[:16].encode('hex')
    num_blocks = struct.unpack('>I', blocks_container[16:20])[0]
    print("[+] GUID(?): " + guid)
    print("[+] {0} blocks".format(num_blocks))
    offset = 20
    block_list = []
    for i in range(num_blocks):
        block = blocks_container[offset:offset+10]
        decompressed_size, compressed_size, flag = struct.unpack('>IIH', block)
        block_list.append((decompressed_size, compressed_size, flag))
        offset += 10
    # Nodes
    num_nodes = struct.unpack('>I', blocks_container[offset:offset+4])[0]
    offset += 4
    print("[+] {0} nodes".format(num_nodes))
    node_list = []
    for i in range(num_nodes):
        name_size = blocks_container[offset+20:].index('\x00')
        node = blocks_container[offset:offset+20+name_size]
        node_offset, node_size, flag = struct.unpack('>QQI', blocks_container[offset:offset+20])
        node_name = blocks_container[offset+20:offset+20+name_size]
        node_list.append((node_offset, node_size, flag, node_name))
        offset += 20 + name_size + 1
    # Extract Blocks
    for x, (decompressed_size, compressed_size, flag) in enumerate(block_list):
        print("[+] Block {0} ({1} bytes)".format(x + 1, decompressed_size))
        data = f.read(compressed_size)
        data = decompress(data, flags & 0x3f, decompressed_size)
        try:
            os.makedirs('UnityFS/' + os.path.dirname(path))
        except:
            pass
        with open('UnityFS/__block{0}__'.format(x + 1), 'wb') as fout:
            fout.write(data)
    if dir_list_end == 0:
        end_of_header = f.tell()
    # Extract Nodes
    for (offset, length, flag, path) in node_list:
        print("[+] File: " + path + " ({0} bytes, at {1})".format(length, offset))
        try:
            os.makedirs('UnityFS/' + os.path.dirname(path))
        except:
            pass
        with open('UnityFS/' + path, 'wb') as fout:
            f.seek(end_of_header + offset)
            data = f.read(length)
            fout.write(data)
    f.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: {0} data.unity3d\n".format(sys.argv[0]))
        print("This script extracts all files from UnityFS. "
              "The target filename is generally named `data.unity3d`.")
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
            magic = f.read(8)
        if magic == 'UnityFS\x00':
            print("[+] You specified decompressed file")
            filepath = sys.argv[1]
        else:
            print("[-] Invalid header: " + repr(magic))
            exit(1)
    # Extract
    extract(filepath)
    print("[+] Exiting...")

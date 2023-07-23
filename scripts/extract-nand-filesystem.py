#!/usr/bin/env python3

# Copyright 2023 micheal65536
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>. 

import sys

with open(sys.argv[1], 'rb') as nand_image_file:
    pages = []
    while True:
        page = nand_image_file.read(2112)
        if len(page) == 0:
            break
        if len(page) != 2112:
            print("WARNING: Image is incorrect length (not a multiple of 2112)")
        pages += [(page[0:2048], page[2048:2112][:8])]

if len(pages) != 1024 * 64:
    print("WARNING: Image has incorrect number of pages (not 1024 * 64)")
blocks = []
for index in range(0, 1024):
    blocks += [pages[index * 64:(index + 1) * 64]]

def read_ftl_table(page_data):
    return [int.from_bytes(page_data[i:i+2], 'little') for i in range(0, 2048, 2)][:576]

def get_ftl_table(block_index):
    block = blocks[block_index]
    for index in range(63, -1, -1):
        if block[index][1] != b'\xff' * 8:
            return (read_ftl_table(block[index][0]), block[index][1])
    print("WARNING: could not find non-erased page in block {} when looking for FTL table".format(block_index))
    return (read_ftl_table(block[0][0]), block[0][1])

def get_ftl_table_a():
    table_data, table_oob = get_ftl_table(490)
    if table_oob != b'\xff\xff\x66\xff\xff\x00\xff\xff':
        print("WARNING: FTL table A has incorrect OOB data (expected {}, got {})".format(b'\xff\xff\x66\xff\xff\x00\xff\xff'.hex(), table_oob.hex()))
    return table_data

def get_ftl_table_b():
    table_data, table_oob = get_ftl_table(871)
    if table_oob != b'\xff\xff\x66\xff\xff\x00\xff\xff':
        print("WARNING: FTL table B has incorrect OOB data (expected {}, got {})".format(b'\xff\xff\x66\xff\xff\x00\xff\xff'.hex(), table_oob.hex()))
    return table_data

def get_ftl_table_c():
    table_data, table_oob = get_ftl_table(507)
    if table_oob != b'\xff\xff\x60\xff\x88\x00\xff\xff' and table_oob != b'\xff\xff\x60\xff\x99\x00\xff\xff':
        print("WARNING: FTL table C has incorrect OOB data (expected {} or {}, got {})".format(b'\xff\xff\x60\xff\x88\x00\xff\xff'.hex(), b'\xff\xff\x60\xff\x99\x00\xff\xff'.hex(), table_oob.hex()))
    return table_data

def get_data_block(block_index):
    block_oob_index_field = None
    block_data = b''
    for page_index in range(0, 64):
        oob_data = blocks[block_index][page_index][1]
        if oob_data == b'\xff' * 8:
            print("WARNING: data block {} page {} has erased OOB data".format(block_index, page_index))
        else:
            if oob_data[0] != 0xFF or oob_data[5] != 0xFF:
                print("WARNING: data block {} page {} has unexpected OOB data (got {})".format(block_index, page_index, oob_data.hex()))
            if oob_data[4] != 0xBB:
                print("WARNING: data block {} page {} has unexpected OOB type field (expected 0xBB, got 0x{:02X})".format(block_index, page_index, oob_data[4]))
            index = int.from_bytes(oob_data[2:4], 'little')
            if block_oob_index_field == None:
                block_oob_index_field = index
            elif index != block_oob_index_field:
                print("WARNING: data block {} page {} has unexpected OOB index field (expected {}, got {})".format(block_index, page_index, block_oob_index_field, index))
            page_num = int.from_bytes(oob_data[6:8], 'little')
            if page_num > 63 and page_num != 65535:
                print("WARNING: data block {} page {} has unexpected OOB page_num field (expected 0-63 or 65535, got {})".format(block_index, page_index, page_num))
        block_data += blocks[block_index][page_index][0]
    return (block_data, block_oob_index_field)

data_blocks = []
table_a = get_ftl_table_a()
table_b = get_ftl_table_b()
for table_index in range(0, 512):
    block_index = table_a[table_index]
    if block_index >= 576:
        print("WARNING: block index in FTL table A is outside of expected range (expected 0-575, got {})".format(block_index))
    block_data, block_index_field = get_data_block(block_index)
    if block_index_field != None and block_index_field != table_index:
        print("WARNING: index in data block {} does not match index in FTL table (expected {}, got {})".format(block_index, table_index, block_index_field))
    data_blocks.append(block_data)
for table_index in range(0, 360):
    block_index = table_b[table_index]
    if block_index < 576 or block_index >= 1024:
        print("WARNING: block index in FTL table B is outside of expected range (expected 576-1023, got {})".format(block_index))
    block_data, block_index_field = get_data_block(block_index)
    if block_index_field != None and block_index_field != table_index:
        print("WARNING: index in data block {} does not match index in FTL table (expected {}, got {})".format(block_index, table_index, block_index_field))
    data_blocks.append(block_data)

with open(sys.argv[2], 'wb') as filesystem_image_file:
    for block in data_blocks:
        filesystem_image_file.write(block)

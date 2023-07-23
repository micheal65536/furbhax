# Furby Connect NAND format documentation

Reverse-engineered and documented by micheal65536 on 22 July 2023

## Flash layout

The NAND flash used by the Furby Connect (TC58BVG0S3HTA00) has the following layout: 2048 + 64 bytes/page, 64 pages/block, 1024 blocks total.

Each page has 64 bytes of OOB (out-of-band) data that is not part of the main 2048-byte page. This is sometimes also referred to as the "spare" data area. It is used by the FTL (flash translation layer) for storing metadata about the page. Note that although the TC58BVG0S3HTA00 datasheet in some places refers to the OOB data as the "ECC" data and both the TC58BVG0S3HTA00 and the GeneralPlus MCU make reference to the ability to automatically calculate and check the ECC data when accessing the NAND flash, this functionality is **not** used in the Furby Connect.

Erased pages are filled with 0xFF (both the main and the OOB data is 0xFF). Note that the flash is erased in complete blocks (64 pages) but is programmed (written) in individual pages. Therefore some pages in a given block may remain unprogrammed after others have been written to.

## OOB data format

The OOB data for each page appears to be divided into the following fields. Only the first 8 bytes are used. The remaining bytes appear to always follow the value of byte 5 (field `unknown_2`).

```
byte  |          0           |     1     | 2   3 |  4   |     5     |  6    7  |
------+----------------------+-----------+-------+------+-----------+----------+
field | unused (always 0xFF) | unknown_1 | index | type | unknown_2 | page_num | 
```

Fields are as follows:

* `type` - indicates the type of the block
  - 0xBB - data block
  - 0xFF, 0x88, 0x99 - FTL table (see below)

* `index`
  - for data blocks this is the index (16-bit little-endian) of the block within the FTL table (see below)
  - for table blocks the value depends on the type of table

* `unknown_1`
  - for data blocks this is usually 0x00 but sometimes it has a different value, its purpose is unknown
  - for table blocks this appears to always be 0xFF

* `unknown_2`
  - for data blocks this is always 0xFF
  - for table blocks this appears to always be 0x00

* `page_num`
  - for data blocks this is usually the index (16-bit little-endian) of the page within the block (0-63), but sometimes it is 0xFFFF, its purpose is unknown
  - for table blocks this appears to always be 0xFFFF

## Data blocks

All non-erased pages within the block have the same `type`, `index`, and `unknown_1` values. The `page_num` is different for each page, and is always the index of the page within the block (0 to 63) unless it is 0xFFFF for a particular page (it is not known why the `page_num` is sometimes 0xFFFF or what this means).

In most cases all pages in the block are programmed (written to), although in the case of the last logical volume block the last few pages are unprogrammed as the filesystem is shorter than the complete block. It is not known if the unprogrammed pages are technically considered part of the volume, but left unprogrammed because the filesystem does not completely fill the volume, or if the volume itself is not a complete integer number of blocks in size. The last page has a programmed OOB value but the main area is filled with 0xFF. It is not known if the last page is required to have a programmed OOB value. It is also not known if blocks other than the last logical block are permitted to have unprogrammed pages within them.

## FTL tables

Some blocks are used for storing tables of information that are used by the flash translation layer.

The FTL table blocks appear to operate by first erasing the complete block, then writing to each subsequent page starting from the first when the table needs to be updated. Presumably once the block is full/all pages have been written to, the block is then erased again and the process repeats. Thus in the table blocks, the first pages are programmed while the later pages remain unprogrammed until they are ready to be used. The current/most recent version of the table is located in the highest programmed page of the block (identifiable as it will have a valid OOB value rather than the OOB being filled with 0xFF), while previous pages contain older versions of the table.

All of the programmed pages within a given table block have the same `index` value, which is specific to the type of table. The `type` value may not be the same for all of the pages depending on the table.

There are 3 tables, which I will call tables A, B, and C.

All of the tables share the same format. There are 576 entries in each table, and each entry is a single 16-bit little-endian value. This value is either the index of a NAND block (0-1023) or the value 0xFFFF or 0x7FFF (written as 0xFF7F).

### Tables A and B

These tables contain the mapping of logical volume blocks to NAND blocks. There are two such tables, table A is located at block 490 and table B is located at block 871. It is not known if these positions are fixed or if they are obtained from somewhere. Both tables have an `index` value of 0x66FF and a `type` value of 0xFF.

The first 512 entries contain the NAND block index of the corresponding logical volume block. Each block that is referenced should be a programmed (non-erased) block where the OOB data indicates that it is a data block, and the OOB `index` field should correspond to the index of the block in the table (0-511). The remaining 64 entries in the table contain the NAND block index of erased/free blocks that are available to be reused. Each block that is referenced should be a fully erased block. The values 0x7FFF and 0xFFFF appear to be used as a placeholder for an "empty" entry, with 0xFFFF possibly doubling as an "end of list" marker.

Table A contains the mappings for logical volume blocks 0-511. For table B, only the first 360 entries appear to be valid, and they contain the mappings for logical volume blocks 512-872 (for a total of 872 logical volume blocks, which matches what is expected based on the filesystem header). *Note that the `index` field in the data blocks themselves starts again from 0 for the blocks that are referenced in table B, the `index` field is not the logical volume block index itself but is the index into whichever table the block is listed in.*

Table A contains references only to NAND blocks 0-575. Each NAND block in this range is referenced exactly once (in either the "in use" or the "free for reuse" parts of the list), except for blocks 490 and 507 (which are used for storing FTL tables). There are two placeholder entries in this table (as the table has a total of 576 entries but there are only 574 blocks to reference).

Table B contains references only to NAND blocks 576-1023. Each NAND block in this range that is in use for data is referenced exactly one within the first 360 entries of the table. The last 64 entries are all references to erased blocks (aside from the very last entry which is placeholder 0xFFFF). Of the remaining 152 entries in the middle of the table, the last 67 are placeholders (0x7FFF), the first 23 appear to be references to erased blocks, and the remaining 62 are duplicate references to blocks that are already referenced elsewhere in table B (it is not known why these duplicates exist or what their purpose is). There is no reference anywhere to block 768. Block 871 (which is used for storing table B itself) is referenced within the "duplicate" part of the table but not elsewhere.

### Table C

Table C is located at block 507. It is not known if this position is fixed or if it is obtained from somewhere. The `index` field has the value 0x60FF.

Each updated version of the table appears to be listed twice with alternating `type` values 0x99 and 0x88. In the provided NAND image the first version appears in the first page with `type` value 0x99 and then again in the second page with `type` value 0x88, and the current version is only listed once in the ninth page with `type` value 0x99. It is not known if this will always be the case.

The purpose of table C is not known.

## Stuff I don't understand

There are some things in the provided NAND image that I still don't understand or which don't match the above information:

* Block 768 is unused and is filled with 0x00 (including the OOB data). It is not referenced in any of the FTL tables.

* Some of the blocks in the range 512-575 appear to be ordinary data blocks and are referenced as such in the FTL tables, but their `type` value is 0xFF instead of 0xBB and none of the `page_num` fields are populated (all 0xFFFF).

* The last page of block 1022 has the OOB value `0xFF002400BB003F000000...` whereas according to the other pages in the block it should be `0xFF003D00BBFF3F00FFFF...`. This is a data block that is in use and is not located at any "significant" position in the volume or in the FTL tables, and all pages including the last appear to be filled with ordinary data. Block 1023 (the last NAND block) is also an ordinary data block that is in use, and the OOB values for block 1023 are all normal.

meta:
  id: int_enum
  endian: le
  encoding: utf-8
seq:
  - id: int_enum1
    type: u8
    enum: int_enum1
    -ufwb-id: 123
  - id: int_enum2
    type: u1
    enum: int_enum2
    -ufwb-id: 456
enums:
  int_enum2:
    4: four
    5: five
    6: six
  int_enum1:
    1: one
    2: two
    3: three
-orig-id: int_enum

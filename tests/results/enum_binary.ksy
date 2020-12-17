meta:
  id: binary_enum
  endian: le
  encoding: utf-8
seq:
  - id: binary_enum1
    type: u8
    enum: binary_enum1
    -ufwb-id: 1
    -must-match: 'false'
  - id: binary_enum2
    type: u1
    enum: binary_enum2
    -ufwb-id: 1
    -must-match: 'false'
enums:
  binary_enum2:
    4: four
    5: five
    6: six
  binary_enum1:
    1: one
    2: two
    3: three
-orig-id: binary_enum

meta:
  id: masks
  endian: le
  encoding: utf-8
seq:
  - id: masks_u1
    type: masks_u1
    -ufwb-id: 1
  - id: masks_u2
    type: masks_u2
    -ufwb-id: 2
types:
  masks_u2:
    seq:
      - id: one
        type: b1
        enum: one
        -orig-id: one
      - id: two
        type: b2
        enum: two
        -orig-id: two
      - id: four
        type: b4
        enum: four
        -orig-id: four
      - id: five
        type: b5
        enum: five
        -orig-id: five
      - id: reserved0
        type: b4
    enums:
      four:
        0: zero
        1: one
        2: two
        3: three
        4: four
        5: five
        6: six
        7: seven
        8: eight
        9: nine
        10: ten
        11: eleven
        12: tvelve
        13: thirteen
        14: fourteen
        15: fifteen
      two:
        0: zero
        1: one
        2: two
        3: three
      five:
        31: thirtyone
      one:
        0: 'false'
        1: 'true'
  masks_u1:
    seq:
      - id: one
        type: b1
        enum: one
        -orig-id: one
      - id: two
        type: b2
        enum: two
        -orig-id: two
      - id: four
        type: b4
        enum: four
        -orig-id: four
      - id: reserved0
        type: b1
    enums:
      four:
        0: zero
        1: one
        2: two
        3: three
        4: four
        5: five
        6: six
        7: seven
        8: eight
        9: nine
        10: ten
        11: eleven
        12: tvelve
        13: thirteen
        14: fourteen
        15: fifteen
      two:
        0: zero
        1: one
        2: two
        3: three
      one:
        0: 'false'
        1: 'true'
-orig-id: masks

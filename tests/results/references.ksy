meta:
  id: references
  endian: le
  encoding: utf-8
seq:
  - id: a
    type: a
types:
  a:
    seq:
      - id: referee
        type: u1
        -ufwb-id: 2
    -ufwb-id: 1
    -orig-id: a
  referer:
    seq:
      - id: ref
        type: a
        -ufwb-id: 4
    -ufwb-id: 3
    -orig-id: referer
-orig-id: references

meta:
  id: merger
  endian: le
  encoding: utf-8
seq:
  - id: mergee
    type: mergee
types:
  mergee:
    seq:
      - id: a
        size: 1
        -ufwb-id: 2
    -ufwb-id: 1
    -orig-id: mergee
-orig-id: merger

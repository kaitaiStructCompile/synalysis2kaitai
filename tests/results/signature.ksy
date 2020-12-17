meta:
  id: signature
  endian: le
  encoding: utf-8
seq:
  - id: test
    size: 8
    contents:
      - 8
      - 7
      - 6
      - 5
      - 4
      - 3
      - 2
      - 1
    -ufwb-id: 1
    -must-match: yes
-orig-id: signature

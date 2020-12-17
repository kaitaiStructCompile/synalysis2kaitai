meta:
  id: primitives
  endian: le
  encoding: utf-8
seq:
  - id: u1_non_explicit
    type: u1
    -ufwb-id: 1
  - id: u1
    type: u1
    -ufwb-id: 10
  - id: s1
    type: s1
    -ufwb-id: 11
  - id: u2_non_explicit
    type: u2
    -ufwb-id: 2
  - id: u2
    type: u2
    -ufwb-id: 20
  - id: s2
    type: s2
    -ufwb-id: 21
  - id: u4_non_explicit
    type: u4
    -ufwb-id: 3
  - id: u4
    type: u4
    -ufwb-id: 30
  - id: s4
    type: s4
    -ufwb-id: 31
  - id: u8_non_explicit
    type: u8
    -ufwb-id: 4
  - id: u8
    type: u8
    -ufwb-id: 40
  - id: s8
    type: s8
    -ufwb-id: 41
  - id: b1
    type: b1
    -ufwb-id: 80
    -length-unit: bit
  - id: b2
    type: b2
    -ufwb-id: 81
    -length-unit: bit
  - id: b3
    type: b3
    -ufwb-id: 82
    -length-unit: bit
  - id: b8
    type: b8
    -ufwb-id: 83
    -length-unit: bit
  - id: b16
    type: b16
    -ufwb-id: 84
    -length-unit: bit
  - id: b32
    type: b32
    -ufwb-id: 85
    -length-unit: bit
  - id: b64
    type: b64
    -ufwb-id: 85
    -length-unit: bit
  - id: f4
    type: f4
    -ufwb-id: 50
  - id: f8
    type: f8
    -ufwb-id: 60
  - id: str
    type: str
    size: 8
    -ufwb-id: 70
  - id: strz
    type: strz
    -ufwb-id: 72
  - id: strz1
    type: strz
    -ufwb-id: 73
  - id: strz_newline
    type: strz
    terminator: 10
    -ufwb-id: 74
-orig-id: primitives

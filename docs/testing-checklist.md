# Camera Testing Checklist

Use this checklist when testing a new body or firmware.

## Before Testing

- Charge the camera battery.
- Record body and firmware.
- Record USB mode wording from the camera menu.
- Back up C1-C7 manually or with a known-good tool.
- Use a sacrificial recipe slot if possible.

## Phase 1: USB Discovery

Record:

- USB vendor id
- interface classes
- endpoint directions and types
- whether PTP class `0x06` is present
- whether mass storage class `0x08` is present

Expected for working bodies:

```text
vendor id 0x04CB
PTP interface class 0x06
bulk OUT endpoint
bulk IN endpoint
```

## Phase 2: Session And DeviceInfo

Test:

```text
OPEN_SESSION
GET_DEVICE_INFO
```

Record:

- model string
- response code
- supported device properties
- whether `0xD18C` is present
- whether `0xD18D` is present

If `0xD18C` is missing, stop before write testing.

## Phase 3: Read One Slot

Test C1 first:

```text
SET_DEVICE_PROP_VALUE 0xD18C = 1
GET_DEVICE_PROP_VALUE 0xD18D
GET_DEVICE_PROP_VALUE 0xD18E..0xD1A5
```

Record:

- name readback
- every property code that returns OK
- every property code that fails
- raw payload bytes for unknown codes

## Phase 4: Read All Slots

Repeat the read flow for every exposed custom slot.

For C1-C7 bodies, test:

```text
C1 C2 C3 C4 C5 C6 C7
```

Record total time and failures.

## Phase 5: Name Write

Write a safe short name to one sacrificial slot:

```text
NAMEBENCH-BASIC
```

Read back and compare exactly.

Then test:

- 25-character boundary
- allowed punctuation
- accent folding
- smart apostrophe folding
- unsupported character collapse

## Phase 6: Property Write

Write one simple property first, such as Dynamic Range or Film Simulation.

Then test a full simple recipe:

- Film Simulation: Velvia
- Dynamic Range: DR100
- Grain: Off
- White Balance: Auto
- Highlight: +1
- Shadow: 0
- Color: +2
- Sharpness: 0
- High ISO NR: 0
- Clarity: 0

Read the slot back and compare raw wire values.

## Phase 7: Delay Bench

If writes fail intermittently, test delay values:

```text
0 ms
5 ms
10 ms
20 ms
50 ms
100 ms
150 ms
```

Record:

- first clean delay
- failing property codes
- response codes
- total write time

## Report Format

```text
Body:
Firmware:
USB mode:
Host OS:
Tool:

PTP interface present:
0xD18C present:
0xD18D present:

Read one slot:
Read all slots:
Name write:
Property write:
First clean delay:

Failures:
Raw logs:
Notes:
```

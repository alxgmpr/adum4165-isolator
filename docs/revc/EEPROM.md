# USB2514B development EEPROM

Program U34 (24LC02B-I/SN, address 0x50) with
[eeprom/hub-revc-development.bin](eeprom/hub-revc-development.bin) before expecting
normal enumeration. It is exactly 256 bytes. The generated CSV explains every
byte, and `manifest.json` records SHA-256. Regenerate with `tools/revc/eeprom.py`.
Blank EEPROM is not a valid substitute: this hub reads zero/blank configuration
rather than falling back to its normal strap defaults.

Hold HUB_RESET_N low at TP13 while programming through TP14 SDA and TP15 SCL.
Use TP16 GND2 and 3.3 V logic, with the board's ISO_3V3 already stable. WP is grounded.
Avoid driving an unpowered rail from the programmer. Read back all 256 bytes,
compare the hash, disconnect the programmer, then release reset. Confirm the
actual test-pad net names from the schematic before connecting probes.

CFG_SEL[1:0]=11 selects EEPROM. Configuration enables high speed, multi-TT,
individual port switching and OC sensing, dynamic LOCAL_PWR switching, four
removable ports and a 500 ms port power-on interval. Charging, string descriptors
and differential polarity swaps are disabled. LOCAL_PWR follows qualified
external source selection. A source transition deliberately causes disconnect
and re-enumeration.

The image uses Microchip's **default development identity 0424:2514**, release
0300. It is for evaluation of this prototype. Obtain an authorized VID/PID before
product distribution. The self-powered upstream allowance is 100 mA including
the host-side isolator; bus-powered controller circuitry is declared as 500 mA.
That declaration does not increase available converter power or ensure that a
legacy host will allocate power to children behind this bus-powered hub. Test
host descriptor/power-policy behavior explicitly; do not change the descriptor
to 100 mA merely to conceal the actual circuit load.

Reference: [Microchip DS00001692E, register map and EEPROM programming](https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB251xB-xBi-Data-Sheet-DS00001692.pdf).

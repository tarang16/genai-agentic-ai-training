---
id: KB-1002
title: USB-C monitor not detected on MacBook (M-series)
products: VX2780, TD2455
---
## Applies to
MacBook Air/Pro with Apple M1/M2/M3 connected over a single USB-C cable.

## Steps
1. Use the USB-C cable supplied in the box. Many phone-charging USB-C cables carry USB 2.0 data only and no DisplayPort Alt Mode.
2. Base M1/M2 MacBook Air supports only one external display natively. A second display needs DisplayLink.
3. In OSD > Setup > USB-C Mode, switch from "USB 3.2" to "High Resolution" to dedicate all lanes to video.
4. Update the monitor firmware to 1.0.8 or later (see KB-1004). Firmware 1.0.6 has a known handshake bug with macOS 15 (Jira DISP-412).

## Resolution rate
Resolves about 75% of cases. If macOS 15 and firmware is older than 1.0.8, link the customer to the firmware update.

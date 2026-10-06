---
id: KB-1003
title: Screen flickers or goes black at 144Hz/165Hz
products: VX3218, XG2431
---
## Applies to
Gaming monitors running above 120Hz over DisplayPort or HDMI 2.1, especially with Adaptive Sync / G-Sync Compatible enabled.

## Steps
1. Confirm the cable: DisplayPort 1.4 certified for 165Hz at 1440p. Cheap adapters are the top cause.
2. Toggle Adaptive Sync off in OSD and check whether the flicker stops. If it does, the issue is low-framerate compensation with the GPU.
3. Update GPU drivers; NVIDIA driver 560.xx introduced a known flicker regression that is fixed in 565.xx.
4. Set "Overdrive" to Standard instead of Ultra Fast.

## Resolution rate
Most cases are cable or driver related. Persistent flicker with Adaptive Sync off and a certified cable is a hardware fault: start an RMA.

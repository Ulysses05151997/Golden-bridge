# Recovering a T2 Mac that won't boot macOS

What happened to a 2019 16-inch MacBook Pro (MacBookPro16,1, Apple T2) on 1 November 2026, and what fixed it. The full account is in section 6 of the [position paper](POSITION-PAPER.md#6-what-it-cost-and-what-we-learned-about-the-t2).

## The symptom

A blue screen and a spinner for about three seconds, black for about thirteen, then a reset. Over and over.

Every Apple-signed image failed at the same point:

| Boot target | Result |
|---|---|
| Installed Tahoe (Apple's own sealed snapshot) | Reset |
| Local Recovery | Reset |
| A separate recovery partition, written from Apple's image, 92 of 92 chunks verified | Reset |
| Internet Recovery, current and original | Reset after download |
| Apple Diagnostics | Reset after download |

Arch Linux booted normally throughout, from the same SSD, through the same T2. Verbose boot showed no text: the reset came before Apple's boot loader printed a line.

## What fixed it

A second Mac running Apple Configurator, connected to the broken Mac in DFU mode.

| Step | What it does | Result here |
|---|---|---|
| **Revive** (twice) | Reinstalls the T2's firmware. Keeps your data and the T2's stored state. | Completed both times. Changed nothing. |
| **Restore** | Reinstalls the firmware **and erases** the internal storage and the T2's stored state. | Fixed it completely. The next boot reached recoveryOS, passed Activation Lock, and reinstalled Tahoe. |

Because the fault survived every Apple image and two revives, and cleared only with the restore, it most likely sat in persistent T2 state that a revive preserves. That is an inference, not a measurement. Which command put it there was never recorded.

A restore erases everything on the internal drive, including any Linux install. Save what you need first.

## Rules for anyone experimenting on a T2 Mac

1. Prepare a second Mac with Apple Configurator before any boot experiment, and confirm it can see your machine in DFU mode.
2. Never begin boot-modifying work while a macOS update is staged. Install it or cancel it first.
3. Know the difference between revive and restore. A revive can complete and fix nothing. A restore erases everything.
4. Save anything Linux needs that came from macOS, especially Wi-Fi and Bluetooth firmware, before a restore.
5. Write down every boot-modifying command before you run it. The one thing this project cannot answer is which one ran.

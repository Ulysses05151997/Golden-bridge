# Golden Gate, step one

Applied to the live Tahoe install on the MacBookPro16,1 (macOS 26.7.2 / build
25G332). This is the first step named in the merger decision: keep the Tahoe
kernel exactly as it is, and change nothing below it.

Scope rule from the project owner: *"we keep the Tahoe kernel intact… and we
call it the first step."* And, on honesty: *"I'm not going to pretend. This is
a first step."*

Everything here touches only `$HOME`, user preferences, `~/Applications`, and
`~/Library/LaunchAgents`. Nothing needs root. Nothing touches the sealed
system volume, the boot policy, or NVRAM.

---

## What was applied

| Item | Change | Reversible |
|---|---|---|
| Wallpaper | `~/Pictures/GoldenGate.jpg`, gold-ribbon, 3072×1920 | yes |
| Wallpaper registration | modern wallpaper store, all spaces and displays, FillScreen | yes |
| Appearance | dark mode | yes |
| Accent colour | gold (`AppleAccentColor 3`) | yes |
| Highlight colour | `0.980392 0.807843 0.294118` | yes |
| Dock | 48pt tiles, magnification on, 72pt large | yes |
| Terminal prompt | `Tahoe's Golden Bridge (26.7.2 – Golden Beta)` above the prompt | yes |
| Login item | `~/Library/LaunchAgents/local.goldenfleece.goldenbridge.plist` | yes |
| Panel | `~/Applications/Golden Bridge.app`, ad-hoc signed | yes |

Two implementation notes that cost time and are worth keeping:

- **The legacy `com.apple.desktop.plist` route does not work on this Tahoe.**
  It writes the setting and the desktop ignores it. The modern store —
  `~/Library/Application Support/com.apple.wallpaper/Store/Index.plist` — is
  what the desktop actually reads.
- **The panel needs `KeepAlive`, not just `RunAtLoad`.** Without it, quitting
  the panel ends it for the whole session and it looks broken.

## The panel

Purpose: a label that is honest about what the machine is running, shown at the
moment someone looks. Written in Swift, compiled on the Mac with swiftc 6.3.3,
x86_64, ad-hoc signed with identifier `local.goldenfleece.goldenbridge`.

**It is hidden until About This Mac or System Information opens**, then appears
within about five seconds. Trigger is a poll of `ps -axo comm=` for
`GeneralSettings.appex` (the About pane) or
`/System/Applications/Utilities/System Information.app/Contents/MacOS/System Information`.
Verified both ways: hidden with nothing open, present with either one open.

Deliberately it needs **no** screen-recording or accessibility permission.

Content: `Tahoe's Golden Bridge / BETA`, `Tahoe 26.7.2 · build 25G332`, and one
line stating that the kernel is unmodified Tahoe and this is a project label,
not an OS version.

"Got it" snoozes the panel for 90 seconds. That will make a rapid reopen look
broken. Dropping the snooze is an open decision.

## What cannot be changed

**The version string.** `/System/Library/CoreServices/SystemVersion.plist` is
`root:wheel`, mode `444`, flagged `restricted`. `sw_vers` and
`kern.osproductversion` read it directly.

Tested and disproved: a user-domain `com.apple.SystemProfiler` override was
written, verified to land, verified to have **no effect** on `sw_vers`, then
reverted. So the "small window underneath System Information that says
Tahoe's Golden Bridge" idea is the correct design — the label cannot be the
real version number without SIP off and a reboot.

SIP off plus a Preboot rewrite is a boot modification. It is out of scope by
the project's own rules, and it is the class of change that destroyed the last
attempt.

**Screen capture of the panel.** `screencapture` fails with "could not create
image from display," and `CGWindowListCreateImage` is unavailable on macOS 26
(ScreenCaptureKit only). So the panel's appearance has never been visually
confirmed. Its existence at 440×200 is confirmed through
`CGWindowListCopyWindowInfo`.

## What this step is not

No 27.2 code runs. There is no 27.2 userspace on the Mac: the KDK contains
none, with no `/usr` and no `/Applications`. Running a real 27 binary needs the
full 26B123 payload, which is Apple's and is not distributed with this project.

Step one is an appearance pass and an honest label. It changes what the machine
looks like and says, not what it runs.

## Undo

`restore-tahoe.sh` reverses every user-domain setting. The original `~/.zshrc`
was empty and is backed up at `~/.goldengate/backup/zshrc.bak`; the full backup
directory is `~/.goldengate/backup/`.

The optional login-window text needs root and has not been applied.

## Naming

The bridge referenced is not Glenbrook. It is **Fanny Bridge** in Tahoe City —
officially the Truckee River Bridge, 1928, where the lake's only outlet crosses
under the road. The better fit for the project: Caltrans proposed a bridge
across the mouth of Emerald Bay in the late 1950s; public opposition killed it
in the 1960s. A bridge planned and never built.

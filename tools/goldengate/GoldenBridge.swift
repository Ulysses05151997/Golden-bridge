import Cocoa

// Golden Bridge panel for Golden Fleece.
// Shows a small honest project panel when About This Mac is opened.
// Watches window titles; touches nothing on the system volume.

final class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow?
    var watcher: Timer?
    var wasAboutVisible = false
    var snoozeUntil: Date = .distantPast

    func applicationDidFinishLaunching(_ note: Notification) {
        buildMenu()
        buildWindow()
        startWatching()
    }

    func buildMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Show Panel", action: #selector(showPanel), keyEquivalent: "n")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        NSApp.mainMenu = main
    }

    func buildWindow() {
        let w: CGFloat = 440
        let h: CGFloat = 200
        let win = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: w, height: h),
            styleMask: [.titled, .closable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        win.title = "Golden Bridge"
        win.titlebarAppearsTransparent = true
        win.titleVisibility = .hidden
        win.isMovableByWindowBackground = true
        win.backgroundColor = .clear
        win.isOpaque = false
        win.level = .floating

        let effect = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: w, height: h))
        effect.material = .hudWindow
        effect.blendingMode = .behindWindow
        effect.state = .active
        effect.wantsLayer = true
        effect.layer?.cornerRadius = 14
        effect.layer?.masksToBounds = true

        let gold = NSColor(calibratedRed: 0.98, green: 0.80, blue: 0.29, alpha: 1)

        let title = NSTextField(labelWithString: "Tahoe's Golden Bridge")
        title.font = .systemFont(ofSize: 23, weight: .semibold)
        title.textColor = gold
        title.alignment = .center
        title.frame = NSRect(x: 0, y: h - 66, width: w, height: 30)

        let beta = NSTextField(labelWithString: "  BETA  ")
        beta.font = .systemFont(ofSize: 10, weight: .bold)
        beta.textColor = gold
        beta.alignment = .center
        beta.wantsLayer = true
        beta.layer?.borderWidth = 1
        beta.layer?.borderColor = gold.withAlphaComponent(0.55).cgColor
        beta.layer?.cornerRadius = 5
        beta.frame = NSRect(x: w/2 - 28, y: h - 96, width: 56, height: 18)

        let sub = NSTextField(labelWithString: "Tahoe 26.7.2  ·  build 25G332")
        sub.font = .systemFont(ofSize: 12)
        sub.textColor = .secondaryLabelColor
        sub.alignment = .center
        sub.frame = NSRect(x: 0, y: h - 124, width: w, height: 17)

        let note = NSTextField(wrappingLabelWithString:
            "The kernel is unmodified Tahoe. This is a project label, not an OS version.")
        note.font = .systemFont(ofSize: 11)
        note.textColor = .tertiaryLabelColor
        note.alignment = .center
        note.frame = NSRect(x: 26, y: 40, width: w - 52, height: 34)

        let btn = NSButton(title: "Got it", target: self, action: #selector(dismiss))
        btn.keyEquivalent = "\r"
        btn.bezelStyle = .rounded
        btn.frame = NSRect(x: w/2 - 40, y: 12, width: 80, height: 26)

        effect.addSubview(title)
        effect.addSubview(beta)
        effect.addSubview(sub)
        effect.addSubview(note)
        effect.addSubview(btn)
        win.contentView = effect
        window = win
    }

    @objc func dismiss() {
        snoozeUntil = Date().addingTimeInterval(90)
        window?.orderOut(nil)
    }

    @objc func showPanel() {
        guard let win = window else { return }
        win.center()
        win.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    // Poll the window server for a window whose owner is About This Mac
    // ("System Information" / "About This Mac" are the usual owner names).
    func startWatching() {
        watcher = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            self?.tick()
        }
        RunLoop.main.add(watcher!, forMode: .common)
    }

    func tick() {
        let aboutOpen = Self.aboutPaneOpen()
        if aboutOpen && !wasAboutVisible {
            wasAboutVisible = true
            if Date() >= snoozeUntil { showPanel() }
        } else if !aboutOpen {
            wasAboutVisible = false
        }
    }

    // The About pane lives inside System Settings and has no window title of its
    // own. Opening it spawns GeneralSettings.appex, so that helper's presence is
    // the signal. It needs no screen-recording or accessibility permission.
    static func aboutPaneOpen() -> Bool {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/bin/ps")
        task.arguments = ["-axo", "comm="]
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = FileHandle.nullDevice
        do { try task.run() } catch { return false }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        task.waitUntilExit()
        guard let out = String(data: data, encoding: .utf8) else { return false }
        return out.contains("GeneralSettings.appex")
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let delegate = AppDelegate()
app.delegate = delegate
app.run()

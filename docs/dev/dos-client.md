# DOS client implementation

[Developer index](README.md) · [Building](building.md) · [Architecture](architecture.md)

## Source responsibilities and memory

| Source | Responsibility |
| --- | --- |
| [main.c](../../client/src/main.c) | Connect/authenticate, session state, message loop, local connection notices |
| [protocol.c](../../client/src/protocol.c), [sha256.c](../../client/src/sha256.c) | Frame state machine and HMAC implementation |
| [network.c](../../client/src/network.c), [mtcpadpt.cpp](../../client/src/mtcpadpt.cpp) | Line transport, cooperative packet pumping, TCP lifetime |
| [ui.c](../../client/src/ui.c), [editor.c](../../client/src/editor.c), [controls.c](../../client/src/controls.c) | Viewport, line input, modal dialogs |
| [video.c](../../client/src/video.c), [glyphs.c](../../client/src/glyphs.c) | BIOS/VRAM output and text glyph selection |
| [charset.c](../../client/src/charset.c), [l10n.c](../../client/src/l10n.c) | UTF-8 conversion and EN/DE strings |
| [transcr.c](../../client/src/transcr.c), [chatfile.c](../../client/src/chatfile.c) | Bounded transcript records and staged file saving |

The build uses Open Watcom Large Model (`-ml`) and 8086 target (`-0`). Under Watcom,
the transcript is an explicitly far, static buffer. Do not assume flat pointers,
32-bit `int`, a large stack, protected mode or a newer CPU. The linker reserves
8192 stack bytes; many working buffers are static. Total free-memory requirements
depend on DOS, drivers and TSRs; the public minimum is not a measurement made by
this documentation. [ramdiag.c](../../client/src/ramdiag.c) and
[build-ram-dos.sh](../../tools/build-ram-dos.sh) are the separate diagnostic route.

## 80x25 video and UI

The normal screen has 18 chat rows of 76 cells, an input row and a fixed footer.
`video_plan()` selects monochrome mode 7/B000 or color mode 3/B800. Legacy MDA
identification also uses the BIOS equipment word. Hercules follows monochrome
text behavior; EGA/VGA detection and font calls establish 25 rows. Legacy CGA
color-cell output uses BIOS writes; other paths use the selected VRAM segment.
Cells are cached to avoid unnecessary writes. Exit restores mode, page, text-row
setup and cursor state, but not the old screen contents or original font data.
This describes implementation support for MDA/Hercules/CGA/EGA/VGA, not physical
validation of every adapter or a guarantee about CGA timing.

The header state machine has exactly `CONNECTING`, `ONLINE`, `TX/RX` and `ERROR`.
Normal footer labels remain fixed: PgUp/Dn, F2, F4, F5, F10. Only available-scroll
direction arrows vary with the viewport, including after PgUp/PgDn. Dialogs and
Help/Info overlays have their own footer hints; runtime notices appear in chat.

F1 opens Info (product version, Wire Protocol version, session ID, status and
connected/disconnected state); F4 opens Help. ESC closes overlays. F10 uses an
exit confirmation. The UI remains a keyboard text interface; it has no file-upload, image, URL-opening or tool UI.
The editor supports insertion, Delete/Backspace, Home/End and cursor movement;
Up/Down scroll lines and PgUp/PgDn scroll 18-line pages.

## Network and encoding

Selected mTCP modules are linked into the EXE, configured by
[mtcpcfg.h](../../client/include/mtcpcfg.h): ARP/TCP, four Packet buffers, one
socket, four transmit buffers. The adapter reads external mTCP configuration via
`MTCPCFG`; Packet Driver loading and IP configuration belong to the host system.
Gateway addresses are numeric IPv4: the adapter does not resolve DNS.

Network waits pump Packet/ARP/TCP work and UI controls cooperatively. The adapter
uses a 768-byte receive buffer and a 10-second connection deadline. The line
transport has a separate `180 * 18` tick wait bound; successful read/write progress
restarts that wait clock. These are implementation limits, not measured throughput.

`LANGUAGE=en/de` selects UI strings independently of provider reply language.
`CODEPAGE=AUTO` asks DOS with INT 21h/6601h; explicit 437/850 select those maps.
Unsupported/undetected codepages use ASCII glyphs and fallbacks. No font is loaded
to make a requested codepage match the installed display font. UTF-8 crosses the
wire; incoming text is converted to the selected DOS codepage, with punctuation
fallbacks and `?` for unavailable characters. Outgoing text is converted back to
UTF-8. The editor allows 1000 DOS bytes, but the encoded message must also fit the
1000-byte UTF-8 payload bound, so non-ASCII input can reach the limit sooner.

## Scrollback and transcript are independent

The visual ring holds **128 wrapped lines**, including labels/separators; old
screen lines are discarded as it fills. Saving uses a separate transcript, not
this ring. Transcript constants in [transcr.h](../../client/include/transcr.h)
are **61,440 bytes (60 KiB)** capacity and **51,200 bytes (50 KiB)** warning
threshold. Capacity includes three-byte role/length record headers, labels,
normalized CRLF and separators; it is not 60 KiB of user text alone.

The warning fires once after reaching the threshold. A full record buffer stops
further transcript appends; an oversized answer can be retained only up to the
accepted prefix. When a recorded message/answer exceeds the remaining transcript
capacity, only the accepted prefix is both stored and displayed. After successful
completion, the gateway can still retain the full answer in its model history.
The UI refuses new user messages that cannot fit and advises F5
Save/F2 New chat. System notices can still be shown when recording is unavailable;
they then cannot be included in a save. Saving does not reset the capacity or
remove the warning; a successful new chat resets both buffers.

`ROLE_USER`, `ROLE_AI` and `ROLE_SYSTEM` are internal identities. Provider labels
are separate and retained per response. `ROLE_SYSTEM` connection/error notices
are visible, scrollable and saved when space permits, and connection events bring
the viewport to the tail. They are never serialized as `MSG`, replayed from saved
files or added to model history. Gateway `wire_messages()` can represent a system
role for server-side callers; that is not transmission of DOS notices.

## Save and session behavior

F5 opens a filename dialog. Filenames accept ASCII letters, digits, `_` and `-`,
with a 1–8 character base and optional 1–3 character extension. Paths, spaces,
multiple dots and DOS device bases (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`,
`LPT1`–`LPT9`) are rejected. A missing extension gets `.TXT`; an explicit extension
is retained. Files live under `CHATS` relative to the working directory.

Exports contain readable labels/text in the active DOS encoding with CRLF and
blank message separators, not internal role headers. Overwriting requires F5
confirmation. `chat_save()` writes `A4SAVE.$$$`, moves an existing destination to
`A4SAVE.$BK`, then renames the staged file. Leftover recovery files cause refusal;
this is a single-process recovery strategy, not a general crash-proof transaction.
Saved chats are exports: there is no import or persistent session restore.

F2 or `/new` sends `NEW` when online; offline it connects/authenticates and requests
a new session. Only success clears the local chat. `/reconnect` deliberately opens
a new connection, authenticates and attempts `RESUME` if a session ID is retained,
otherwise `NEW`. It preserves the local transcript. Missing/expired sessions or
sessions owned by another connection report an error; the client does not silently
start a replacement chat. Interrupted output remains locally visible but is not
replayed by resume. See [gateway lifetime rules](gateway.md).

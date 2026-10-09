# Setting up AI4DOS on DOS

This guide covers networking, `AI4DOS.CFG` configuration and operation of the DOS client. Extract the DOS package as described in the [Quick Start](quick-start.md#4-set-up-ai4dos-on-the-dos-pc); your DOS PC needs a working network connection to communicate with your gateway.

Download the DOS package from the [AI4DOS GitHub Releases](https://github.com/MarcoR-DOS/AI4DOS/releases) page.

Start with [networking that already works](#a-networking-already-works) or [set up networking from scratch](#b-set-up-networking-from-scratch). Then continue with [client configuration](#c-configure-the-dos-client-ai4doscfg) and [operation](#use-the-dos-client).

AI4DOS supports the following DOS networking solutions:

- PicoMEM
- NE2000-compatible networking solutions
- each in combination with mTCP

Other packet-driver-compatible networking solutions may also work. However, we cannot guarantee full compatibility with them.

## A. Networking already works

If your DOS PC already reaches other computers on the network with mTCP, you do not need to set up anything else here.

Just check:

- your packet driver is loaded
- mTCP works
- your DOS PC can reach the computer running AI4DOS Gateway

If that is all in place, follow the [DOS client configuration](#c-configure-the-dos-client-ai4doscfg) and run:

```dos
AI4DOS
```

If your DOS PC does not yet have a working network connection, continue here.

---

## B. Set up networking from scratch

We will proceed step by step:

1. prepare the network card or PicoMEM
2. load the packet driver
3. set up mTCP
4. obtain an IP address
5. test the connection
6. connect AI4DOS

We change only one thing at a time. This makes it easier to identify where something goes wrong.

### 1. What is a packet driver?

DOS normally has no central networking service like modern operating systems.

Instead, programs such as mTCP or AI4DOS communicate with the network card through a **packet driver**.

Simplified:

```text
AI4DOS / mTCP
      |
Packet driver
      |
Network card / PicoMEM
      |
   Network
```

The packet driver must therefore be loaded before mTCP or AI4DOS can use the network.

### 2. Prepare the network hardware

#### PicoMEM

If you use PicoMEM, enable its NE2000 network emulation.

AI4DOS works with PicoMEM and its NE2000 emulation.

The exact I/O address and IRQ depend on your PicoMEM configuration.

A typical configuration might be:

```text
I/O 300h
IRQ 3
```

What matters is not using these exact values, but ensuring that:

- PicoMEM and the packet driver use the same I/O address
- the IRQ does not conflict with other hardware

#### NE2000-compatible network card

For a real NE2000-compatible ISA card, you also need to know:

- the I/O address
- the IRQ

Typical values include:

```text
I/O 300h
IRQ 3
```

or other combinations, depending on the card and computer.

If the card has jumpers or its own setup program, those settings must match the packet driver.

### 3. Load the packet driver

The packet driver provides the interface between the network card and DOS programs.

Many packet drivers start with a command similar to:

```dos
PACKET.COM 0x60
```

or, for an NE2000-compatible card, with additional I/O and IRQ parameters as appropriate.

With PicoMEM, you can use the supplied packet driver, for example.

The important number is:

```text
0x60
```

This is the **software interrupt** that DOS programs use to reach the packet driver.

For AI4DOS and mTCP, `0x60` is a reasonable and common value.

If the packet driver loads successfully, it should normally display a short status message.

If an error appears here, resolve it first. mTCP cannot work without a functioning packet driver.

### 4. Provide mTCP

AI4DOS uses mTCP for network communication.

Put the mTCP programs in a separate folder, for example:

```text
C:\MTCP
```

Depending on your mTCP package, it contains programs such as:

```text
DHCP.EXE
PING.EXE
FTP.EXE
```

For setup, we initially need mainly:

- `DHCP`
- `PING`

Change to this folder for the following DHCP and PING commands:

```dos
CD \MTCP
```

### 5. Set MTCPCFG

mTCP stores its network settings in a configuration file.

It uses this environment variable:

```text
MTCPCFG
```

For example:

```dos
SET MTCPCFG=C:\MTCP\MTCP.CFG
```

This tells mTCP where to store the network configuration.

You can add this line to your `AUTOEXEC.BAT` later. For the first test, entering it manually is sufficient.

You can check the variable with:

```dos
SET
```

You should then see something like:

```text
MTCPCFG=C:\MTCP\MTCP.CFG
```

Create the `MTCP.CFG` file specified by `MTCPCFG` if it does not exist yet.

The software interrupt of your packet driver must also be specified in `MTCP.CFG`. If your packet driver was loaded with `0x60`, for example, add this entry to `MTCP.CFG`:

```text
PACKETINT 0x60
```

If you use a different software interrupt, enter that value there instead.

### 6. Obtain an IP address automatically

If your network uses a normal router with DHCP, this is the easiest method.

Run:

```dos
DHCP
```

mTCP now tries to obtain these automatically from your router:

- an IP address
- a subnet mask
- a gateway
- a DNS server

If everything works, the configuration is saved in the file specified by `MTCPCFG`.

A successful result looks roughly like this:

```text
IP address received
Gateway received
DNS server received
```

The exact output may vary depending on the mTCP version.

### 7. If DHCP does not work

If `DHCP` cannot find a server or ends with an error, check these points first:

#### Is the packet driver loaded?

The packet driver must have been started before `DHCP`.

#### Correct software interrupt?

If your packet driver uses `0x60`, mTCP must be able to reach it there.

#### Do the I/O address and IRQ match?

For NE2000/PicoMEM, the values must match the actual hardware configuration.

#### Network cable / connection

For real Ethernet hardware:

- is the cable plugged in?
- is there a link LED?
- is the switch/router port active?

With PicoMEM, check that the network function is enabled.

#### Hardware conflicts

IRQ or I/O conflicts can occur, especially on old PCs.

For example, if two cards use the same IRQ, one may appear to work but still behave unreliably.

### 8. Test the local network

Once DHCP works, we first test the local network.

Find your router's IP address.

Typical examples:

```text
192.168.0.1
192.168.1.1
```

Then:

```dos
PING 192.168.0.1
```

If replies arrive, these are already working:

- network card
- packet driver
- mTCP
- local IP configuration
- connection to the router

This is the most important first test.

### 9. Ping the gateway computer

Now test the computer running AI4DOS Gateway.

If its IP address is:

```text
192.168.0.42
```

for example, run:

```dos
PING 192.168.0.42
```

If this ping also works, your DOS PC can reach the gateway computer at the network level.

This is the exact IP address you will later put in `AI4DOS.CFG`.

### 10. Test Internet access

This step is not strictly required for AI4DOS itself, but it can help with troubleshooting.

For example:

```dos
PING google.com
```

If a hostname works, you also know that DNS is configured correctly.

If:

```dos
PING 8.8.8.8
```

works but:

```dos
PING google.com
```

does not, the problem is probably DNS rather than the network card.

For AI4DOS, however, it is sufficient for your DOS PC to reach the gateway by IP address.

### 11. Make the settings permanent

Once everything works, add the necessary startup commands to `AUTOEXEC.BAT`: first the packet driver, then `MTCPCFG`, and finally DHCP if you use a dynamic IP address.

For example, commands along these lines:

```dos
C:\MTCP\PACKET.COM 0x60
SET MTCPCFG=C:\MTCP\MTCP.CFG
C:\MTCP\DHCP.EXE
```

Replace the packet driver line with the command for your network card, using its actual path and required parameters. DHCP must successfully obtain an IP configuration after every DOS startup before you start AI4DOS.

With an intentionally configured static IP address, the appropriate IP address, netmask, gateway and DNS values are already in `MTCP.CFG`. In that case, omit the DHCP command; the packet driver and `MTCPCFG` are still required.

### 12. Configure AI4DOS

Fill in `AI4DOS.CFG` as described in the [DOS client configuration](#c-configure-the-dos-client-ai4doscfg).

Then:

```dos
AI4DOS
```

If everything works, the top right corner shows:

```text
ONLINE
```

Your DOS PC is now fully connected to AI4DOS Gateway.

---

## C. Configure the DOS client (AI4DOS.CFG)

The commented `AI4DOS.CFG` template is supplied beside `AI4DOS.EXE` in the DOS package. Edit it with a plain text editor, save it as `AI4DOS.CFG` and change to this directory before starting. The normal `AI4DOS` command automatically loads the file from the **current directory**; no configuration filename is required.

You can also load another configuration file as the first argument, for example for a second gateway or a test environment:

```dos
AI4DOS TEST.CFG
```

Use DOS 8.3 filenames without spaces. A path such as `C:\AI4DOS\TEST.CFG` is also possible; relative paths refer to the current directory. Provider selection remains on the respective gateway.

Example for a gateway at `192.168.0.42` with the default port:

```ini
SERVER=192.168.0.42
PORT=1983
DEVICE=dos-pc
SECRET=<your device key>
LANGUAGE=en
```

Replace the address and key with your own values:

| Entry | Meaning |
| --- | --- |
| `SERVER` | IP address of the gateway computer or Docker host reachable by the DOS PC. Not the DOS IP, container IP or bind address `0.0.0.0`; `127.0.0.1` would refer to the DOS PC itself. |
| `PORT` | Native: listener port from the gateway configuration. Docker / Portainer: published host port. Default `1983`; the internal Docker port stays `1983`. The firewall must also allow the selected port. |
| `DEVICE` | Device ID from the gateway's `devices` section, normally `dos-pc` for a single DOS PC. |
| `SECRET` | Device key of the matching `devices` entry, identical character for character on both sides. Use at least 12–16 random letters and digits, or more, and do not reuse a key used elsewhere. |
| `LANGUAGE` | `de` or `en` for the DOS client's menus, notices and error messages. |

The device key authenticates the DOS PC using HMAC; it does not encrypt chat traffic between the DOS PC and gateway. The provider API key stays exclusively on the gateway and never belongs in `AI4DOS.CFG`.

`LANGUAGE` selects only the interface. The gateway instructs the model to reply in the language of your message unless you explicitly request another language. Write in your preferred reply language. The client is text-based and cannot display or upload images or files; the gateway explains these limitations to the model.

Restart AI4DOS after changing `AI4DOS.CFG`. This does not modify previously saved chat files. When getting started, leave advanced network, buffer, session and authentication settings at their defaults.

### Multiple DOS devices

One gateway can serve several DOS computers. Add a device ID with its own device key for each one to the existing `devices` object: in `server/gateway.local.json` for native installations, or `config.local/gateway.json` for Docker / Portainer.

```json
"devices": {
  "ibm-xt": "<Key for the XT>",
  "486dx2": "<Key for the 486>"
}
```

Replace both key placeholders with your own random values without spaces. On each DOS PC, enter the corresponding ID at `DEVICE=` and its key at `SECRET=`. Save the files and restart the gateway and DOS clients. For a single DOS PC, the existing `dos-pc` entry is sufficient.

## Narrow down errors step by step

If it does not work, always test in this order:

```text
1. Does the packet driver load?
        |
2. Does DHCP work?
        |
3. Does pinging the router work?
        |
4. Does pinging the gateway work?
        |
5. Does AI4DOS connect?
```

This quickly tells you where the error is.

### Packet driver does not load

The problem is probably with:

- network card
- I/O address
- IRQ
- packet driver

### DHCP does not work

The problem is probably with:

- packet driver
- network connection
- router/DHCP
- hardware conflict

### Router ping works, gateway ping does not

The problem is probably between the DOS PC and gateway computer, for example:

- wrong gateway IP
- firewall
- wrong network/VLAN

### Gateway ping works, AI4DOS stays offline

The DOS network is working at a basic level.

Now check:

- is AI4DOS Gateway running?
- is its port correct?
- is the device key the same on both sides?
- is the gateway IP in `AI4DOS.CFG` correct?
- is a firewall blocking TCP port 1983?

→ [AI4DOS troubleshooting](troubleshooting.md)

## Use the DOS client

Start only `AI4DOS`. System messages appear in the chat area; the connection status is at the top right.

| Key / command | Action |
| --- | --- |
| Enter | Send a message |
| F1 / `/info` | Show product version, wire version and session |
| F2 / `/new` | Start a new chat |
| F4 / `/help` | Show help |
| F5 / `/save` | Save under `CHATS\` (DOS 8.3 filename) |
| F10 / `/quit` | Exit; confirm with F10 or cancel with Esc |
| PgUp / PgDn | Scroll by page |
| Up / down arrow | Scroll by line |
| Esc | Return to chat |
| `/reconnect` | Reconnect and resume the existing session |

Visible scrollback holds 128 lines. The saved transcript can be longer; a new session clears the current chat. Sessions live in gateway memory: after a gateway restart, the previous session cannot be restored. Set `LANGUAGE=en` or `LANGUAGE=de` in `AI4DOS.CFG` and restart the client to change its language.

Packet drivers and mTCP utilities are separate networking prerequisites and are not supplied in the DOS ZIP. This guide does not replace driver or hardware documentation.

# AI4DOS troubleshooting

If AI4DOS does not work, it is best to proceed **from the simplest check to the most likely error**.

The most important rule is:

> First check **where** the connection fails: DOS PC, network, gateway or AI provider.

## 1. AI4DOS does not start

### `AI4DOS.CFG` was not found

If `AI4DOS.EXE` cannot find its configuration file, an English error message appears.

Check:

- is `AI4DOS.CFG` in the same directory as `AI4DOS.EXE`?
- is the file named exactly `AI4DOS.CFG`?
- was it accidentally saved as `AI4DOS.CFG.TXT`?
- is the file readable?

The normal startup command is simply:

```dos
AI4DOS
```

You do not need to specify a configuration filename. Change to the directory containing `AI4DOS.EXE` and `AI4DOS.CFG` before starting: the file is loaded from the current directory. See the [DOS client configuration](dos-setup.md#c-configure-the-dos-client-ai4doscfg) for the entries.

### `AI4DOS.CFG` is invalid

Check the file for:

- typing errors
- missing values
- invalid IP address
- invalid port
- invalid device key
- unsupported language setting

Compare your file with the [complete CFG example](dos-setup.md#c-configure-the-dos-client-ai4doscfg).

## 2. AI4DOS starts but stays OFFLINE

If the program runs but cannot connect to the gateway, check these first:

1. Is the gateway running?
2. Is the IP address in `AI4DOS.CFG` correct?
3. Is the port correct?
4. Can your DOS PC reach the gateway computer at all?
5. Is a firewall blocking the connection?

For native packages, also check `host` in `server/gateway.local.json`: the value determines the local interfaces the gateway listens on. `127.0.0.1` is reachable only locally. For a normal home network, use `0.0.0.0` for all IPv4 interfaces. In `AI4DOS.CFG`, enter the gateway computer’s LAN IP that the DOS PC uses to reach it.

If your gateway runs on your home network at:

```text
192.168.0.42
```

for example, test this under DOS:

```dos
PING 192.168.0.42
```

If this ping does not work, the problem is **before AI4DOS**.

→ [Setting up AI4DOS on DOS](dos-setup.md)

## 3. The DOS PC cannot reach the gateway computer

Test step by step:

```text
1. Packet driver loaded?
        |
2. DHCP works?
        |
3. Router reachable?
        |
4. Gateway computer reachable?
```

### Check the packet driver

The packet driver must be loaded before mTCP and AI4DOS.

If the driver already reports an error at startup, check:

- I/O address
- IRQ
- software interrupt
- hardware conflicts

With PicoMEM or an NE2000-compatible card, the hardware settings and packet driver must match.

### Check DHCP

Run:

```dos
DHCP
```

If no IP address is obtained, the problem is probably with:

- packet driver
- network card
- cable/connection
- router/DHCP
- IRQ/I/O conflict

### Ping the router

For example:

```dos
PING 192.168.0.1
```

If this works, your local DOS network is working at a basic level.

### Ping the gateway computer

For example:

```dos
PING 192.168.0.42
```

If the router is reachable but the gateway computer is not, check:

- correct IP address?
- same network range?
- firewall?
- VLAN or guest network?
- is the target computer actually running?

## 4. Gateway runs, but AI4DOS cannot authenticate

If the network and gateway are reachable but login fails, the usual cause is:

- incorrect device ID
- incorrect device key

On the DOS side, the key is in:

```text
SECRET=...
```

On the gateway side, for example:

```json
"devices": {
  "dos-pc": "..."
}
```

Both values must be **exactly identical character for character**.

Case matters too.

Also check that the device ID matches on both sides.

For a normal installation, we use:

```text
dos-pc
```

### Set the device key again

If you are unsure, choose a new device key and enter it again on both sides.

Prefer at least **12–16 random letters and digits**.

Then restart the gateway and AI4DOS.

## 5. Gateway does not start

`Python environment is missing` means the project-local `.venv` is missing. `Gateway dependencies are missing` means the required dependencies are missing from it. Follow the setup commands in the installation guide for [Windows](install-windows.md), [macOS](install-macos.md) or [Linux](install-linux.md): create `.venv`, then install `server/requirements-lock.txt` in it. **This is required even if Python is already installed.** `START.BAT` and `start.sh` do not perform these steps automatically. Docker / Portainer requires no host Python.

If the gateway itself does not start, check these first:

- is the gateway configuration valid?
- for native packages, has `.venv` been created and `server/requirements-lock.txt` installed in it?
- has `<KEY>` been replaced in the device configuration?
- is a provider selected?
- has the API key been entered?
- was the file saved correctly?

A typical device entry looks like this, for example:

```json
"devices": {
  "dos-pc": "XTChat84K7M29Q"
}
```

If the `devices` list is missing, empty or contains an invalid key, the gateway deliberately refuses to start.

## 6. API key does not work

If the gateway starts but the AI provider rejects access, check the API key.

Important:

> Your normal ChatGPT, Claude or other user account is **not** API access.

You need a separate API key from the respective provider.

Typical causes:

- API key copied incorrectly
- API key revoked
- API access not yet enabled by the provider
- credit used up
- billing not configured
- wrong provider selected
- API key belongs to another service or project

If possible, create a new API key with the provider and enter it again.

## 7. Gateway connects to the provider, but the model does not work

AI4DOS does not use a fixed list of allowed model names.

Enter the model ID at `MODEL=` exactly as specified by the respective API provider. Get the exact model name from that provider’s API/developer documentation.

If you enter a model name, it is generally passed to the respective provider.

Errors can therefore mean:

- model name misspelled
- model no longer exists
- model is not enabled for your API access
- model is not available in your region or plan
- selected reasoning/thinking option is not supported by the model

→ [Configure providers and models](providers.md)

## 8. `REASONING` or `THINKING` causes errors

AI4DOS uses this by default:

```text
REASONING=none
```

This is the safest setting for getting started.

Additional reasoning/thinking modes may:

- have different names depending on the provider
- not be supported by every model
- use considerably more tokens and therefore incur higher costs

If errors occur after a change, restore:

```text
REASONING=none
```

Also remove any explicit overrides `REASONING_EFFORT`, `THINKING_LEVEL`, `THINKING_BUDGET`, `ENABLE_THINKING` and `CLEAR_THINKING` from your active provider configuration: they can remain effective independently of `REASONING=none`. Then restart the gateway.

If it then works, the error was probably caused by the selected model/reasoning combination.

## 9. AI4DOS does not reply or stays on TX/RX for a long time

`TX/RX` means AI4DOS is waiting for a reply from the gateway or provider.

Possible causes:

- provider is responding slowly
- free model is overloaded
- provider currently has an outage
- very long reasoning has been enabled
- network connection to the gateway is unstable

Wait briefly first.

If this state occurs regularly:

- try another model
- try another provider
- use `REASONING=none`
- check the gateway logs

AI4DOS and the gateway have timeouts and do not remain stuck in a single request indefinitely.

## 10. Reply is cut off

AI4DOS deliberately limits replies to keep memory and network usage manageable on DOS hardware.

When “Transcript full” appears, the DOS client cannot send another message. Save the current conversation with F5 if needed and start a new chat with F2. See [reply limits and transcript memory](providers.md#reply-length-and-transport) for the distinction between gateway limits and a full DOS transcript. A cut-off reply does not always mean that the transcript is full.

If a very long reply is cut off and there is still room in the transcript:

- ask for a shorter reply
- split a large task into several questions
- check the configured reply length on the gateway

This is not necessarily a network error.

## 11. Umlauts or special characters look wrong

AI4DOS supports DOS character sets such as CP437 and CP850.

Check:

- which code page is active under DOS
- whether AI4DOS is configured accordingly
- whether the characters used exist in that code page at all

German ä, ö, ü, Ä, Ö, Ü and ß are supported.

For unusual Unicode characters or emoji, AI4DOS uses text-based replacements where possible.

## 12. The model asks me to upload a file or image

The AI4DOS DOS client **cannot upload or provide files, images or other content at all**.

The gateway normally tells the models this.

If a model still asks you to do so, ignore the request and describe the content as text instead.

If this happens regularly with a particular provider or model, please report it as a bug.

## 13. Saving does not work

AI4DOS saves chats as text files.

If you do not specify a file extension when saving, AI4DOS automatically adds:

```text
.TXT
```

If an error occurs, check:

- does the filename contain at most **8 characters before the dot** and at most **3 characters for the extension**?
- does the destination directory exist?
- is there enough space on the drive?
- is the medium writable?

Example:

```text
CHAT1
```

becomes:

```text
CHAT1.TXT
```

## 14. Docker container is not running

With Docker Compose:

```bash
sudo docker compose ps
```

shows the status.

Show logs:

```bash
sudo docker compose logs --tail=100 gateway
```

or follow them continuously:

```bash
sudo docker compose logs -f gateway
```

In particular, check:

- API key set?
- `gateway.json` valid?
- device key entered?
- `provider.cfg` valid?
- published host port already occupied? Choose a free host port and set `AI4DOS_PORT` and `PORT` in `AI4DOS.CFG` accordingly.
- Docker/Compose up to date and working?

## 15. Docker runs, but DOS cannot reach the gateway

Check:

- is the configured host port published (selected host port → container `1983`)?
- is the IP address of the **Docker host** correct?
- are you accidentally using the container's internal IP?
- is the host firewall blocking the published host port?
- is the container actually running?

The DOS PC normally connects to:

```text
<SERVER-IP>:<HOST-PORT>
```

Replace the placeholders with the server address reachable by the DOS PC and the selected host port (default `1983`). The container's internal Docker address is not a destination address for the DOS PC.

## 16. Portainer stack does not start

Open **Environment → Stacks → your AI4DOS stack → Containers → gateway container** for **State**, **Health**, **Logs** and **Restart**. For a restart loop check logs and config read permissions first.

Check in Portainer:

- stack status
- container status
- container logs
- environment values
- absolute paths to `gateway.json` and `provider.cfg`
- volumes/bind mounts
- port publication
- whether the local AI4DOS image was built on this Docker host beforehand

If the stack file was modified outside AI4DOS, compare it with the supplied original version.

### Check config read permissions in detail

The permission commands in the [installation guide](install-docker.md) normally suffice. If the container reports that it cannot read the config files, optionally check in more detail. Replace `/path/to/ai4dos` with your absolute package path:

```bash
sudo setpriv --reuid=10001 --regid=10001 --clear-groups test -r /path/to/ai4dos/config.local/gateway.json
echo $?
sudo setpriv --reuid=10001 --regid=10001 --clear-groups test -r /path/to/ai4dos/config.local/provider.cfg
echo $?
namei -l /path/to/ai4dos/config.local/gateway.json
```

`setpriv` checks access using the container's user and group numbers. Run each `test` command separately; `echo $?` immediately afterwards must show `0`. `namei -l` also shows parent directory permissions. If the tools are missing on Debian/Ubuntu, install `util-linux` with `sudo apt-get install util-linux`.

Config files should have owner/group `root:10001`, mode `640`; the config directory should be `root:10001`, mode `750`. Parent directories must be searchable; mode `755` normally suffices for the package folder. Do not copy config contents or keys into diagnostic reports.

### Port values for Compose and Portainer

The Compose commands in this section use defaults: host port `1983`, host address `0.0.0.0`. If you selected other values, repeat them on every invocation as described in the [installation guide](install-docker.md). Without these values, defaults apply. Depending on the installation, status and logs also require `sudo`.

Portainer needs absolute host paths in `AI4DOS_GATEWAY_CONFIG` and `AI4DOS_PROVIDER_CONFIG`; for another host port also set `AI4DOS_PORT`. The local image `ai4dos-gateway:beta` must exist on the same Docker environment. Paste the complete supplied `portainer-stack.yml` into the web editor.

The internal container listener remains `0.0.0.0:1983`. `AI4DOS_BIND_ADDRESS` applies only to the host address. For port changes use Compose `up -d` or Portainer **Update the stack**; `restart` alone does not change mappings.

## 17. Gateway reports `AUTH_FAILED`

This means:

> The DOS PC could not authenticate with the configured device key.

Check:

```text
DEVICE
SECRET
```

in `AI4DOS.CFG` and the matching entry under:

```json
"devices"
```

in the gateway.

The gateway deliberately closes the connection after failed authentication.

## 18. Many `AUTH_FAILED` messages in the server log

The gateway logs failed authentication attempts like this, for example:

```text
AUTH_FAILED peer=203.0.113.10 device=dos-pc
```

If you use a publicly accessible VPS or dedicated server, automated scanners may cause these attempts.

AI4DOS deliberately has no built-in ban system.

Server administrators can evaluate these log entries with Fail2Ban, for example.

General server security remains the host administrator's responsibility.

## 19. Gateway port is reachable from the Internet

If you run AI4DOS on a VPS or dedicated server and your DOS PC needs to reach the gateway directly over the Internet, the selected TCP port must be publicly accessible (Docker: published host port, e.g. `1983`; native: listener port, default `1983`).

In this case, as with any other network service, make sure your environment is properly administered:

- up-to-date software
- firewall
- only necessary ports
- strong device keys
- Fail2Ban if applicable

If you do not want the selected gateway port to be publicly accessible, we recommend using a VPN connection.

## 20. Everything worked, but suddenly it does not

Check what changed recently:

- new IP address for the gateway computer?
- router restarted?
- DHCP assigned a different address?
- API key changed or expired?
- different model configured?
- provider currently experiencing an outage?
- firewall changed?
- device key changed?
- packet driver not loaded after restarting DOS?

For local gateways, a changed IP address after a router/PC restart is a particularly common cause.

## 21. Narrow down the error effectively

If you do not know where to start:

```text
Does AI4DOS.EXE start?
        |
        v
Does DOS networking work?
        |
        v
Can you ping the gateway computer?
        |
        v
Is the gateway running?
        |
        v
Does the device key match?
        |
        v
Does the provider/API key work?
        |
        v
Is the model available?
```

Always test **one layer at a time**.

## Still stuck?

If our instructions are unclear at any point, please let us know.

**If you get stuck there, the next user will probably stumble over it too. We should improve the instructions in that case.**

For a support request, these details are particularly helpful:

- which DOS version and hardware you use
- which networking solution you use
- whether mTCP/ping works
- which gateway platform you use
- exact error message
- what worked immediately beforehand

**Please never post API keys or device keys publicly.**

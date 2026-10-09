# Set up AI4DOS Gateway on Windows

This guide sets up AI4DOS Gateway on a Windows PC or notebook.

At the end, the gateway will be running on your Windows computer and your DOS PC will be able to connect to it.

## What you need

Before you begin, you need:

- the **AI4DOS server package for Windows**
- **Python 3.9 or newer**, available from the command line
- an API key for a supported AI provider
- your DOS PC on the same network
- a device key you choose yourself

If you have not set up API access yet, read this first:

→ [Set up an AI provider and API access](providers.md)

## 1. Extract the server package

Extract the Windows server package into a folder of your choice.

For example:

```text
C:\AI4DOS
```

AI4DOS does not need to be installed. The gateway runs directly from this folder.

## 2. Prepare Python and dependencies

Each freshly extracted native AI4DOS package needs **two separate prerequisites**:

- **A: Python 3.9 or newer** must be installed on the computer.
- **B: A project-local Python environment `.venv`** must be created once in the extracted package folder and populated with the AI4DOS dependencies from `server/requirements-lock.txt`.

### A. Check the Python version

Check in a command prompt:

```bat
py -3 --version
```

If Python 3.9 or newer is not available yet, install a suitable version with the Python launcher `py`.

### B. Always set up the AI4DOS environment

**You must complete this step even if Python is already installed and the version check succeeded.** Checking the version does not replace setup.

Change to the extracted AI4DOS package folder and run these commands once:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r server\requirements-lock.txt
```

This creates `.venv` in the package folder and installs the required dependencies in it. `START.BAT` **does not create this environment automatically** and **does not install dependencies automatically**. Complete both steps before starting the gateway.

## 3. Enter the AI provider settings

Open `server/provider.local.cfg` with a plain text editor. Enter your API key at `API_KEY=`.

Here you specify:

- which AI provider to use
- which API key AI4DOS should use
- which model to use

For your first test, you can use the default values supplied in the package and just enter your API key.

AI4DOS does not maintain a fixed model list. Enter the model ID at `MODEL=` exactly as specified by the respective API provider. Get the exact model name from that provider’s API/developer documentation.

For an easy free start with OpenRouter, you can initially leave the prepared default `MODEL=openrouter/free` unchanged. OpenRouter can then select a currently available free model. If you later want to use a specific model, enter its model ID at `MODEL=`.

You can change providers and models at any time later.

Valid values for `PROVIDER=`: `openai`, `anthropic`, `gemini`, `mistral`, `nvidia`, `openrouter`, `openai-compatible`.

→ [Configure providers and models](providers.md)

## 4. Enter the device key

Next, open `server/gateway.local.json`.

`host` in the gateway configuration determines which local interfaces the gateway listens on. The template contains `"host": "127.0.0.1"`, which makes it accessible only on the gateway computer itself. For a normal home network, set `"host": "0.0.0.0"` so the gateway listens on all IPv4 interfaces. Then find the gateway computer’s LAN IP and enter that exact address in `AI4DOS.CFG` later: this is the address your DOS PC uses to reach the gateway. `0.0.0.0` is not a destination address for the DOS PC; the DOS PC’s LAN IP does not belong in `host`. The default port remains `1983`; it must be accessible through the firewall.

Find this section:

```json
"devices": {
  "dos-pc": "<KEY>"
}
```

Replace `<KEY>` with a device key you choose yourself.

Prefer at least **12–16 random letters and digits**, or more.

For example:

```json
"devices": {
  "dos-pc": "XTChat84K7M29Q"
}
```

You will need this key again shortly on your DOS PC.

Important: The value must be **exactly the same** on both sides.

## 5. Start the gateway

Run `START.BAT`.

The gateway should now load its configuration and wait for connections.

If an error appears at startup, first check:

- have you entered the API key?
- have you entered a valid device key?
- was the configuration file saved correctly?

If the gateway starts successfully, leave it open for now.

## 6. Windows firewall

At the first start, Windows may ask whether to allow network access for the gateway.

Allow access for your **private network**.

For a normal computer at home, you do not need to forward the AI4DOS port to the Internet on your router.

Your DOS PC only needs to reach the Windows computer within your local network.

## 7. Find the Windows computer's IP address

Your DOS PC needs to know the address at which it can reach the gateway.

Open a command prompt in Windows and enter:

```bat
ipconfig
```

Find the **IPv4 address** of your active network connection.

For example:

```text
192.168.0.42
```

You will need this address shortly for `AI4DOS.CFG`.

Note: `127.0.0.1` does not work here. This address always means “this computer itself”. On your DOS PC, it would point to the DOS PC rather than the Windows computer.

## 8. Enter the DOS configuration

Open the supplied:

```text
AI4DOS.CFG
```

and enter:

- the IP address of your Windows computer
- the same device key as in the gateway
- your preferred language

in the file.

The file already contains the appropriate entries and notes.

Then copy `AI4DOS.EXE` and `AI4DOS.CFG` to your DOS PC.

## 9. Test the connection

Make sure your DOS PC already has a working network connection.

If your DOS PC can already reach other computers on your network with mTCP, that is normally sufficient.

If not:

→ [Setting up AI4DOS on DOS](dos-setup.md)

## 10. Start AI4DOS

On the DOS PC:

```dos
AI4DOS
```

AI4DOS automatically loads `AI4DOS.CFG` and tries to reach the gateway.

If everything works, the top right corner shows:

```text
ONLINE
```

You can now type your first message and press **Enter** to send it.

## If the connection fails

Check these points first:

- Is AI4DOS Gateway running on the Windows computer?
- Is the IP address in `AI4DOS.CFG` correct?
- Is the device key exactly the same on both sides?
- Has Windows allowed network access for the gateway?
- Can your DOS PC reach the Windows computer on the network at all?

More help:

→ [Troubleshooting](troubleshooting.md)

## Change settings later

Once AI4DOS is running, you can easily:

- use a different AI provider
- select a different model
- set a different device key
- move the gateway to another computer

Save changes to `server/gateway.local.json` or `server/provider.local.cfg`, stop the running gateway with **Ctrl+C** and start it again as in section 5. If the listener port changed, also update `PORT` in `AI4DOS.CFG` and restart the DOS client. Previously saved chat files are preserved.

→ [DOS client configuration](dos-setup.md#c-configure-the-dos-client-ai4doscfg) · [Providers and models](providers.md)

For a test without API access, see [Offline function test](providers.md#offline-function-test-without-api-access). If you change the listener port, use that same port in the firewall rule.

# Set up AI4DOS Gateway with Docker / Portainer

This guide sets up AI4DOS Gateway in a Docker environment.

This can be a NAS, Raspberry Pi, home server, Linux server or VPS, for example. You can run AI4DOS either directly with **Docker Compose** or through **Portainer**.

At the end, the gateway will be running in a container and your DOS PC will be able to connect to it.

## 1. What you need

Before you begin, you need:

- the **AI4DOS server package for Docker**
- a working Docker environment with Docker Compose
- shell/SSH access to the Docker host, including when using Portainer
- an API key for a supported AI provider
- your DOS PC with a network connection to the Docker host
- a device key you choose yourself

**The Portainer web interface alone is not enough.** You also need shell access to the Docker host: this is where you extract the ZIP, prepare the config files and build the local image once.

Docker and Portainer require **no Python on the host**. Python and the required dependencies are included in the container/image.

If you have not set up API access yet, read this first:

→ [Set up an AI provider and API access](providers.md)

## 2. Extract the Docker package

Download the appropriate package from the [AI4DOS GitHub Releases](https://github.com/MarcoR-DOS/AI4DOS/releases) page.

Extract the Docker server package on the computer or server where the gateway will run.

The DOS files **do not belong** in this folder. They are used separately on your DOS PC.

The Docker package contains the files needed for the gateway and container.

Replace `/path/to/ai4dos` in the following commands with the absolute path to your extracted package folder. The Linux host needs `unzip` to extract the package. If it is missing on Debian/Ubuntu, install it first:

```bash
sudo apt-get update
sudo apt-get install unzip
```

For example, on a Linux host:

```bash
sudo mkdir -p /path/to/ai4dos
sudo unzip AI4DOS-Server-Docker.zip -d /path/to/ai4dos
cd /path/to/ai4dos
```

## 3. Set up the AI provider

Open `config.local/provider.cfg` on the Docker host, for example with:

```bash
sudoedit config.local/provider.cfg
```

Here you specify:

- which AI provider to use
- which model to use
- which additional provider options to use

Enter the API key at `API_KEY=` in the same file. Provider, API key, model and optional provider values all belong in `config.local/provider.cfg`.

For your first test, you can use the default values supplied and just add your API key.

AI4DOS does not maintain a fixed model list. Enter the model ID at `MODEL=` exactly as specified by the respective API provider. Get the exact model name from that provider’s API/developer documentation.

For an easy free start with OpenRouter, you can initially leave the prepared default `MODEL=openrouter/free` unchanged. OpenRouter can then select a currently available free model. If you later want to use a specific model, enter its model ID at `MODEL=`.

Valid values for `PROVIDER=`: `openai`, `anthropic`, `gemini`, `mistral`, `nvidia`, `openrouter`, `openai-compatible`.

→ [Configure providers and models](providers.md)

## 4. Enter the device key

Open on the Docker host:

```bash
sudoedit config.local/gateway.json
```

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

You will need this key again later in `AI4DOS.CFG` on your DOS PC.

The value must be **exactly the same** on both sides.

### Protect the config files

The container reads the configs as user and group `10001:10001`. After editing, run in the package folder:

```bash
sudo chown root:10001 config.local config.local/gateway.json config.local/provider.cfg
sudo chmod 750 config.local
sudo chmod 640 config.local/gateway.json config.local/provider.cfg
```

This keeps the files protected and readable by the container. Do not use `chmod 777`. Continue using `sudoedit` for later edits.

## 5. Choose your installation method

**Choose exactly one method: Docker Compose or Portainer. You do not need to complete both.** Then continue with section 6.

Both methods use host port `1983` by default. The container listener is already fixed at `0.0.0.0:1983`; do not change `host` or `port` in `gateway.json` for this.

Shell commands use `sudo` because some Docker installations require elevated permissions. This also applies to status and logs. Omit `sudo` if your user already has Docker access.

### Option A: Docker Compose

Run in the extracted package folder:

```bash
sudo docker compose build
sudo docker compose up -d
sudo docker compose ps
```

The first command builds the local image; Docker may download the base image and dependencies. The second starts the gateway in the background. The third shows whether the container is running and `healthy`. If it still shows `starting`, wait briefly and check again.

#### Only for a different host port or host address

If host port `1983` is occupied, choose a free port. Replace `<HOST-PORT>` with its number:

```bash
sudo env AI4DOS_PORT=<HOST-PORT> docker compose up -d
sudo env AI4DOS_PORT=<HOST-PORT> docker compose ps
```

The internal container port remains `1983`. Also use the selected host port in `AI4DOS.CFG` and the host firewall.

By default Docker publishes on all IPv4 host interfaces (`0.0.0.0`). To make the port available only on one host address, add `AI4DOS_BIND_ADDRESS=<HOST-IP>` immediately after `env` when starting. This variable applies to the host, not the container.

**Repeat your chosen overrides on every later Compose invocation**, including a new SSH session: `sudo env AI4DOS_PORT=<HOST-PORT> docker compose ...`; for a different host address also include `AI4DOS_BIND_ADDRESS=<HOST-IP>`. Without these values, defaults apply again. No `.env` is required. These variables are not needed for `build` alone.

### Option B: Portainer

Select a **Docker Standalone** environment in Portainer on the same host where you extracted the package and prepared the configs.

First build the local image in that host's shell, in the package folder:

```bash
sudo docker compose build
cat portainer-stack.yml
```

The build creates `ai4dos-gateway:beta` without starting a container. `cat` displays the supplied stack contents for copying.

In Portainer:

1. Open the appropriate **Environment → Stacks → Add stack** and enter a name, for example `ai4dos`.
2. Select **Web editor** and paste the complete contents of **`portainer-stack.yml`**. Alternatively use **Upload** with that exact file. **`docker-compose.yml` is not the Portainer stack file.**
3. Below the editor, under **Environment variables → Add an environment variable**, enter the following values. Replace `/path/to/ai4dos` with the absolute package path on the Docker host:

| Name | Value | Required? |
| --- | --- | --- |
| `AI4DOS_GATEWAY_CONFIG` | `/path/to/ai4dos/config.local/gateway.json` | yes |
| `AI4DOS_PROVIDER_CONFIG` | `/path/to/ai4dos/config.local/provider.cfg` | yes |
| `AI4DOS_PORT` | `<HOST-PORT>` | only for a host port other than `1983` |
| `AI4DOS_BIND_ADDRESS` | `<HOST-IP>` | only for a host address other than `0.0.0.0` |

4. Paths refer to the **Docker host**, not your browser computer. Both files must already exist there. **Do not enter API keys or device keys as Portainer variables**; they stay in the config files.
5. Click **Deploy the stack**. The stack uses the locally built image; do not enable another image pull from a registry.
6. Open **Stacks → your stack → Containers → gateway container**. Under **State** and **Health** it should be running and `healthy`. Open **Logs** for gateway output.

## 6. Network and DOS configuration

The DOS PC connects to the **host IP and published host port**. Replace the placeholders with your server address and selected host port (default `1983`):

```ini
SERVER=<SERVER-IP>
PORT=<HOST-PORT>
DEVICE=dos-pc
SECRET=<your device key>
```

These values belong in `AI4DOS.CFG` from the separate DOS package. The device key must exactly match `gateway.json`. Neither the internal container IP nor `0.0.0.0` is a DOS destination address; `127.0.0.1` would refer to the DOS PC itself.

The host firewall or VPN must make the **published host port** reachable from the DOS PC, TCP `1983` by default. A home network normally needs no Internet router port forwarding. Maintain the OS and Docker as usual. HMAC authentication does not encrypt DOS traffic; use a suitable protected network/VPN for confidential connections.

## 7. Test the connection / start AI4DOS

Make sure your DOS PC already has a working network connection.

If your DOS PC can reach the Docker host or server with mTCP, that is normally sufficient.

If not:

→ [Setting up AI4DOS on DOS](dos-setup.md)

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

## 8. If the connection fails

Check first:

- Is the container running?
- Has the gateway started successfully inside the container?
- Is the address in `AI4DOS.CFG` correct?
- Is the device key exactly the same on both sides?
- Can the DOS PC reach the published host port (TCP `1983` by default)?
- Is the API key entered correctly?
- Is a firewall on the server blocking the port?

For Docker Compose, run in the extracted package folder:

```bash
sudo docker compose ps
```

This shows whether the gateway container is running and `healthy`.

```bash
sudo docker compose logs --tail=100 gateway
```

This shows the last 100 gateway log lines. These usually contain the actual startup or configuration error.

If you use another host port or host address, set those values again on these invocations as described in Option A.

In Portainer, open the gateway container in the stack and inspect **State**, **Health** and **Logs**. For a restart loop first check the error message, config paths and read permissions. See [Troubleshooting](troubleshooting.md#check-config-read-permissions-in-detail) for a more detailed permission check.

More help:

→ [Troubleshooting](troubleshooting.md)

## 9. Change settings later

Once AI4DOS is running, you can easily:

- use a different AI provider
- select a different model
- set a different device key
- move the container to another Docker host
- switch between Docker Compose and Portainer

For Docker Compose, edit the config files with `sudoedit` and restart the gateway:

```bash
sudo docker compose restart gateway
```

Use `sudo docker compose logs -f gateway` to follow ongoing gateway output. For a different host port or host address, repeat the values described in Option A each time. Port mapping changes require `up -d`; `restart` alone does not change mappings.

In Portainer, **Restart** in the gateway container reloads edited configs. For port changes use **Update the stack**.

To switch from Compose to Portainer or stop Compose:

```bash
sudo docker compose down
```

Include your host overrides here too, if applicable. Both methods must not use the same host port at the same time. Remove your own Portainer stack using **Delete this stack / Remove** in its stack details.

→ [DOS client configuration](dos-setup.md#c-configure-the-dos-client-ai4doscfg) · [Providers and models](providers.md)

# AI4DOS Quick Start

**AI4DOS is a chat client for MS-DOS that lets you use ChatGPT, Claude, Google Gemini, Mistral and other AI services directly on your DOS PC.**

AI4DOS has been tested on a real IBM PC XT with a 4.77 MHz CPU and 512 KB RAM, among other systems. The program requires at least **256 KB of free conventional memory** to run.

## What you need

AI4DOS consists of two parts:

- the **DOS client** on your DOS PC
- the **AI4DOS Gateway** on a modern computer

The gateway acts as a technical intermediary between your DOS PC and the AI service.

Modern AI services use current HTTPS/TLS connections, certificates and web APIs that a classic DOS PC cannot readily communicate with directly. The gateway handles this modern part and translates between the two sides.

```text
DOS PC  <-->  AI4DOS Gateway  <-->  AI service
```

Think of it as an interpreter between two very different computer languages.

The gateway can run on a Windows PC, Mac, Linux computer, Raspberry Pi, NAS, home server or VPS, for example.

## 1. Download the appropriate packages

You always need the **DOS package**.

In addition, download exactly the **server package** that matches your modern computer or server environment:

- Windows
- macOS
- Linux
- Docker

The packages are offered separately. You do not need to download one large package containing files for every platform.

## 2. Choose your AI provider

AI4DOS requires access to a supported AI service, for example:

- OpenAI / ChatGPT
- Anthropic / Claude
- Google Gemini
- Mistral
- NVIDIA
- OpenRouter

Important: You **cannot** use your normal ChatGPT, Claude or other subscription login here. Those credentials only work through the provider's official access methods, such as its website or mobile/desktop apps.

AI4DOS therefore connects to the AI service through **API access**. These interfaces are specifically designed to let third-party software communicate with the service. You receive a separate API key for this purpose.

For the easiest start, we recommend **OpenRouter**.

OpenRouter is not a network router. It is a service that lets you access different AI models through a single API account.

This lets you try AI4DOS with a free model first. Alternatively, you can use API access directly from another supported provider of your choice.

Valid values for `PROVIDER=`: `openai`, `anthropic`, `gemini`, `mistral`, `nvidia`, `openrouter`, `openai-compatible`.

AI4DOS does not maintain a fixed model list. Enter the model ID at `MODEL=` exactly as specified by the respective API provider. Get the exact model name from that provider’s API/developer documentation.

For an easy free start with OpenRouter, you can initially leave the prepared default `MODEL=openrouter/free` unchanged. OpenRouter can then select a currently available free model. If you later want to use a specific model, enter its model ID at `MODEL=`.

→ [Configure providers and models](providers.md)

## 3. Set up the gateway

Extract the appropriate server package and follow the installation guide for your platform:

- [Set up Windows](install-windows.md)
- [Set up macOS](install-macos.md)
- [Set up Linux](install-linux.md)
- [Set up Docker / Portainer](install-docker.md)

**Windows, macOS and Linux:** The gateway requires Python 3.9 or newer. The installation guide for your platform explains the setup step by step: [Windows](install-windows.md), [macOS](install-macos.md), [Linux](install-linux.md).

**Docker / Portainer:** You do not need to install Python on the host.

During setup, enter your API key.

AI4DOS also needs a **device key**. It authenticates your DOS PC to your AI4DOS Gateway. It does not encrypt chat data.

Choose the device key yourself. Prefer at least **12–16 random letters and digits**, or more, and do not reuse a key you already use elsewhere.

Later, enter the same device key in both the gateway configuration and `AI4DOS.CFG` on your DOS PC.

For getting started, this is all you need to know:

- the **API key** belongs to the AI provider
- the **device key** belongs to your own AI4DOS Gateway

## 4. Set up AI4DOS on the DOS PC

Extract the DOS package.

It contains these files, among others:

```text
AI4DOS.EXE
AI4DOS.CFG
```

Open `AI4DOS.CFG` with a plain text editor.

This configuration file holds:

- the IP address of your gateway computer
- the device key
- the language you want to use in AI4DOS

You do not have to memorize these settings. The file is supplied as a template and explains each entry.

Then copy `AI4DOS.EXE` and `AI4DOS.CFG` to your DOS PC.

## 5. Check the DOS network

Your DOS PC needs a working network connection to communicate with the gateway.

If your DOS PC already connects to the network with mTCP, you can continue straight away.

If networking under DOS is new to you:

→ [Setting up AI4DOS on DOS](dos-setup.md)

That guide explains what you need, step by step.

## 6. Start AI4DOS

On your DOS PC, change to the directory containing AI4DOS and run:

```dos
AI4DOS
```

Nothing else is required.

`AI4DOS.EXE` automatically loads the adjacent:

```text
AI4DOS.CFG
```

If the connection works, the top right corner shows:

```text
ONLINE
```

You can now type your first message and press **Enter** to send it.

## Done

You are now chatting with a modern AI service from your DOS PC.

## If something does not work

Network cards, packet drivers and existing network configurations can vary considerably, especially on real DOS computers.

The most common problems are covered here:

→ [Troubleshooting](troubleshooting.md)

If you get stuck because our instructions are unclear, please let us know.

**If you get stuck there, the next user will probably stumble over it too. We should improve the instructions in that case.**

## What you can change later

Once your first test works, you can:

- use a different AI provider
- select a specific model
- adjust the language and other options
- move the gateway to another computer or server

See the [DOS client configuration](dos-setup.md#c-configure-the-dos-client-ai4doscfg), [Providers and models](providers.md) and the platform guide linked in section 3 for details.

Package files:

| Platform | ZIP |
| --- | --- |
| DOS | `AI4DOS-DOS.zip` |
| Windows | `AI4DOS-Server-Windows.zip` |
| macOS | `AI4DOS-Server-macOS.zip` |
| Linux | `AI4DOS-Server-Linux.zip` |
| Docker / Portainer | `AI4DOS-Server-Docker.zip` |

# AI4DOS Gateway

Der Gateway verwendet Python ab 3.9 und die fixierten Runtime-Abhängigkeiten aus
`requirements-lock.txt`. Pythonstart und Docker benutzen denselben Servercode.

Die Nutzerdokumentation liegt zentral unter [`docs/de/` und `docs/en/`](../docs/README.md):

- [Schnell zum ersten Chat](../docs/de/quick-start.md)
- Installation: [Windows](../docs/de/install-windows.md), [Docker](../docs/de/install-docker.md), [macOS](../docs/de/install-macos.md), [Linux](../docs/de/install-linux.md)
- [Provider](../docs/de/providers.md), [DOS-Client-Konfiguration](../docs/de/dos-setup.md#c-dos-client-konfigurieren-ai4doscfg), [Fehlerbehebung](../docs/de/troubleshooting.md)

`requirements.txt` beschreibt zulässige direkte Abhängigkeiten;
`requirements-lock.txt` den getesteten Installationsstand. Kein automatisches
Installieren beim Start. Lokale Configs und API-/Device-Keys bleiben privat.

## Lokale Runtimepakete bauen

Vom Sourcecheckout aus, nach dem DOS-Build:

```sh
python3 tools/package-release.py all --output dist
```

Einzelziele: `dos`, `windows`, `macos`, `linux`, `docker`. Identische Eingaben
und dieselbe Python/zlib-Toolchain erzeugen bytegleiche ZIPs; Reihenfolge,
Zeitstempel und Dateimodi sind fest. DOS enthält EXE/CFG und Lizenz-/Notice-Dateien.
Serverpakete enthalten den gleichen Python-Gateway, Vorlagen und nur den jeweiligen
Starter bzw. Docker-Dateien. Keine Runtime/venv und keine private Konfiguration
werden gebündelt. README, START-HERE, Quickstart und öffentliche Doku bleiben
zentral auf GitHub. Dies baut lokale Artefakte und veröffentlicht kein Release.

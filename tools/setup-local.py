#!/usr/bin/env python3
"""Prepare gateway templates; the user sets the same device key on gateway and DOS."""
import argparse
import ipaddress
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Create gateway configs and show values to enter in AI4DOS.CFG.")
    parser.add_argument("--server-address", required=True, help="numeric LAN IPv4 address of the gateway computer")
    parser.add_argument("--docker", action="store_true", help="prepare persistent container configs")
    parser.add_argument("--root", type=Path, help="project directory (for a bind-mounted setup folder)")
    args = parser.parse_args()
    try:
        address = ipaddress.IPv4Address(args.server_address)
        if address.is_unspecified or address.is_multicast or str(address) == "255.255.255.255":
            raise ValueError()
    except ValueError:
        parser.error("Use the gateway computer's numeric IPv4 address.")
    root = args.root or Path(__file__).resolve().parents[1]
    config_dir = root / "config.local"
    gateway = root / "server/gateway.local.json"
    provider = root / "server/provider.local.cfg"
    if args.docker:
        gateway = config_dir / "gateway.json"
        provider = config_dir / "provider.cfg"
    paths = (gateway, provider)
    if any(p.exists() or p.is_symlink() for p in paths):
        parser.exit(1, "Local config already exists. Nothing overwritten; keep your existing device key.\n")
    created = []
    made_dir = False
    try:
        template = (root / "server/provider.example.cfg").read_bytes()
        if args.docker:
            if not config_dir.exists():
                config_dir.mkdir(mode=0o700)
                made_dir = True
            # The private host directory contains individually read-only mounted files.
            if config_dir.is_symlink() or config_dir.stat().st_mode & 0o077:
                parser.exit(1, "config.local must be a private directory (chmod 700), not a symlink.\n")
        config = {"host": "0.0.0.0" if args.docker else str(address), "port": 1983, "devices": {"dos-pc": "<KEY>"},
                  "provider_config": "provider.cfg" if args.docker else "provider.local.cfg"}
        for path, content in ((gateway, (json.dumps(config, indent=2) + "\n").encode("ascii")),
                              (provider, template)):
            mode = 0o444 if args.docker else 0o600
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
            created.append(path)
            with os.fdopen(fd, "wb") as output:
                output.write(content)
            if args.docker and path in (gateway, provider):
                path.chmod(mode)
    except OSError:
        for path in created:
            path.unlink()
        if made_dir:
            config_dir.rmdir()
        parser.exit(1, "Cannot create local configs. Check directory permissions; newly created files removed.\n")
    print("Gateway configs created. Edit the supplied AI4DOS.CFG yourself; it is not managed by this helper.")
    print("Set API_KEY in config.local/provider.cfg." if args.docker else "Set API_KEY in server/provider.local.cfg.")
    print("Keep all local configs private.")
    print("Enter these values in AI4DOS.CFG:")
    print("SERVER=" + str(address))
    print("PORT=1983\nDEVICE=dos-pc")
    print("Choose your own device key (recommend at least 12-16 letters/digits).")
    print("Set the same key in " + str(gateway.relative_to(root)) + " devices[dos-pc] and SECRET in AI4DOS.CFG.")
    print("Keep AI4DOS.CFG beside AI4DOS.EXE; start AI4DOS from that directory.")
    print("Allow TCP port 1983 in your LAN firewall.")


if __name__ == "__main__":
    main()

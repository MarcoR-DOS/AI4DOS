#!/usr/bin/env python3
"""Check the fixed container listener greeting; no auth/API."""
import socket
import sys
from ai4dos.protocol import GREETING


def main():
    try:
        with socket.create_connection(('127.0.0.1', 1983), timeout=2) as connection:
            with connection.makefile('rb') as stream:
                greeting = stream.readline(128)
        return 0 if greeting.rstrip(b'\r\n') == GREETING.encode('ascii') else 1
    except (OSError, ValueError, TypeError, AttributeError):
        return 1


if __name__ == '__main__':
    sys.exit(main())

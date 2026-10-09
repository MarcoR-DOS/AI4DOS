import re

VERSION = "0.3"
GREETING = "OK AI4DOS/" + VERSION + " UTF-8"
MAX_LINE = 1024
MAX_MESSAGE = 1000
DATA_BYTES = 512
DEVICE_RE = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")
SESSION_RE = re.compile(r"[0-9a-f]{12}\Z")
HMAC_RE = re.compile(r"[0-9a-fA-F]{64}\Z")


class ProtocolError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def parse_command(line):
    if any(ord(c) < 32 or ord(c) == 127 for c in line):
        raise ProtocolError("BAD_COMMAND", "control character in command")
    verb, sep, arg = line.partition(" ")
    if verb == "HELLO" and sep and DEVICE_RE.fullmatch(arg):
        return verb, arg
    if verb == "AUTH" and sep and HMAC_RE.fullmatch(arg):
        return verb, arg.lower()
    if verb == "RESUME" and sep and SESSION_RE.fullmatch(arg):
        return verb, arg
    if verb == "MSG" and sep and arg.strip():
        if len(arg.encode("utf-8")) > MAX_MESSAGE:
            raise ProtocolError("TOO_LONG", "message exceeds byte limit")
        return verb, arg
    if verb in {"NEW", "QUIT"} and not sep:
        return verb, None
    raise ProtocolError("BAD_COMMAND", "invalid command")


def escape_data(text):
    return text.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")


def unescape_data(text):
    out, i = [], 0
    mapping = {"\\": "\\", "r": "\r", "n": "\n", "t": "\t"}
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 1
            if i >= len(text) or text[i] not in mapping:
                raise ProtocolError("BAD_DATA", "invalid escape")
            c = mapping[text[i]]
        out.append(c)
        i += 1
    return "".join(out)


def data_frames(text, limit=DATA_BYTES):
    if not 4 <= limit <= DATA_BYTES:
        raise ValueError("DATA limit must be between 4 and 512")
    chunk, size = [], 0
    for char in text:
        part = escape_data(char)
        n = len(part.encode("utf-8"))
        if size + n > limit:
            yield "DATA " + "".join(chunk)
            chunk, size = [], 0
        chunk.append(part)
        size += n
    if chunk:
        yield "DATA " + "".join(chunk)


def error_frame(code, message):
    code = re.sub(r"[^A-Z0-9_]", "_", code.upper())[:32]
    message = "".join(c if 32 <= ord(c) < 127 else " " for c in message)[:200]
    return "ERROR " + code + " " + message

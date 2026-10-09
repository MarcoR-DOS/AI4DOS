"""Presentation only: turn a complete model reply into XT-friendly text."""

from typing import Optional

import re
import textwrap
import unicodedata


ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
TABLE_RULE = re.compile(r"^:?-{3,}:?$")
EMOJIS = {
    "😀": ":-D", "😃": ":-D", "😄": ":-D", "😁": ":-D",
    "🙂": ":-)", "😊": ":-)", "☺": ":-)", "😉": ";-)",
    "😢": ":-(", "☹": ":-(", "🙁": ":-(", "😞": ":-(",
    "😛": ":-P", "😜": ";-P", "😕": ":-/",
}
PUNCTUATION = str.maketrans({
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
    "‘": "'", "’": "'", "‚": "'", "–": "-", "—": "-", "−": "-",
    "…": "...", "•": "-", "·": "-", "\u00a0": " ",
})


REPLACEMENTS = {"€": "EUR", "™": "(TM)", "©": "(C)", "®": "(R)"}


def _dos_representable(char):
    for codepage in ("cp437", "cp850"):
        try:
            char.encode(codepage)
            return True
        except UnicodeEncodeError:
            pass
    return False


def _plain_line(line: str, *, markdown: bool = True) -> str:
    line = ANSI.sub("", line).translate(PUNCTUATION).translate(str.maketrans(REPLACEMENTS))
    for emoji, replacement in EMOJIS.items():
        line = line.replace(emoji, replacement)
    line = re.sub(r"[\ufe0e\ufe0f\u200d]", "", line)
    line = "".join(
        char for char in line
        if not ((unicodedata.category(char) == "Cc" and char != "\t") or
                (unicodedata.category(char) in {"So", "Sk", "Cs"} and not _dos_representable(char)))
    )
    if markdown:
        line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
        line = re.sub(r"^(\s*)[-*+]\s+", r"\1- ", line)
        line = re.sub(r"^(\s*)>\s?", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", line)
        line = re.sub(r"(`+)([^`]+)\1", r"\2", line)
        line = re.sub(r"(\*\*|__)(.+?)\1", r"\2", line)
    return line


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _table_at(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines) or "|" not in lines[index]:
        return False
    header, rule = _cells(lines[index]), _cells(lines[index + 1])
    return len(header) == len(rule) and all(TABLE_RULE.fullmatch(cell) for cell in rule)


def _table_blocks(lines: list[str]) -> list[str]:
    result: list[str] = []
    index = 0
    code = False
    while index < len(lines):
        if re.match(r"^\s*```", lines[index]):
            code = not code
            result.append(lines[index])
            index += 1
            continue
        if code or not _table_at(lines, index):
            result.append(lines[index])
            index += 1
            continue
        headers = [_plain_line(cell) for cell in _cells(lines[index])]
        index += 2
        while index < len(lines) and "|" in lines[index] and lines[index].strip():
            values = _cells(lines[index])
            if len(values) != len(headers):
                break
            result.extend(f"{label}: {_plain_line(value)}" for label, value in zip(headers, values))
            result.append("")
            index += 1
        if result and result[-1] == "":
            result.pop()
    return result


def _dos_safe(text: str) -> str:
    result: list[str] = []
    for char in text:
        if _dos_representable(char):
            result.append(char)
        else:
            result.append(REPLACEMENTS.get(char, unicodedata.normalize("NFKD", char).encode("ascii", "ignore").decode("ascii") or "?"))
    return "".join(result)


def render_dos(text: str, width: Optional[int] = None) -> str:
    if width is not None and width < 20:
        raise ValueError("DOS output width must be at least 20")
    lines = _table_blocks(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    output: list[str] = []
    code = False
    for line in lines:
        if re.match(r"^\s*```", line):
            code = not code
            continue
        line = _dos_safe(_plain_line(line, markdown=not code))
        if code:
            line = "  " + line
        if not line.strip():
            output.append("")
            continue
        # The client knows the actual screen width and speaker prefix. Wire
        # newlines must remain semantic, otherwise wrapping twice leaves orphans.
        if width is None:
            output.append(line.rstrip())
            continue
        indent = len(line) - len(line.lstrip(" "))
        output.extend(textwrap.wrap(line, width=width, subsequent_indent=" " * indent,
                                    break_long_words=True, break_on_hyphens=False,
                                    replace_whitespace=False, drop_whitespace=True))
    return "\n".join(output).strip("\n")

import html
import os

import requests
from dotenv import load_dotenv

# Configuration
load_dotenv()
# Look for .env next to the script, or next to the .exe when built with PyInstaller.

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OWNER_ID = os.getenv("OWNER_ID", "")

TRAFFIC_SOURCE = "FB"        # shown in every offer title, e.g. "Name | UK [FB] Slot"
DEFAULT_APPROACH = "Slot"    # used when the Approach field is empty

def geo_flag(geo: str) -> str:
    """Convert a two-letter country code to a flag emoji ("UK" is treated as GB)."""
    code = geo.strip().upper()
    if code == "UK":
        code = "GB"
    if len(code) != 2 or not code.isascii() or not code.isalpha():
        return "🌍"
    # A flag emoji is two "regional indicator" characters, one per letter.
    return "".join(chr(0x1F1E6 + ord(letter) - ord("A")) for letter in code)


def _conditions(mindep: str, baseline: str, wager: str) -> str:
    """Build the text inside the brackets: mindep, baseline and wager."""
    if baseline and wager:
        if mindep == baseline == wager:
            return f"mindep = <b>baseline = wager {wager}</b>"
        if mindep == baseline:
            return f"mindep = <b>baseline {baseline} + wager {wager}</b>"
        if mindep == wager:
            return f"mindep = <b>wager {wager} + baseline {baseline}</b>"
        return f"mindep {mindep} + <b>baseline {baseline} + wager {wager}</b>"
    if baseline:
        if mindep == baseline:
            return f"mindep = <b>baseline {baseline}</b>"
        return f"mindep {mindep} + <b>baseline {baseline}</b>"
    if wager:
        if mindep == wager:
            return f"mindep = <b>wager {wager}</b>"
        return f"mindep {mindep} + <b>wager {wager}</b>"
    return f"mindep {mindep}"


def build_offer_text(name_input, geo, cpa, source, mindep, cap, baseline, wager,
                     kpi, i2r, r2d, platform, approach, comment) -> str:
    """Return the Telegram-HTML text. Several names separated by commas give several lines."""
    # Telegram HTML needs <, > and & escaped, otherwise the message is rejected.
    esc = lambda value: html.escape(str(value or ""), quote=False)

    names = [n.strip() for n in name_input.split(",") if n.strip()]
    flag = geo_flag(geo)
    cap_str = "?ftd" if cap == "" or cap is None else f"<b>{esc(cap)}ftd</b>"
    conditions = _conditions(esc(mindep), esc(baseline), esc(wager))

    # Quote block: comment first, then KPI, then platform (only the filled ones).
    quote_lines = []
    if comment:
        quote_lines.append(esc(comment))
    if kpi:
        quote_lines.append(f"KPI: {esc(kpi)}")
    if platform:
        quote_lines.append(f"{esc(platform)} platform")

    # Conversion rates line: invite-to-registration and registration-to-deposit.
    rates = []
    if i2r:
        rates.append(f"I2R — <b>{esc(i2r)}%</b>")
    if r2d:
        rates.append(f"R2D — <b>{esc(r2d)}%</b>")

    results = []
    for name in names:
        title = f"{flag} <b>{esc(name)} | {esc(geo)} [{esc(source or TRAFFIC_SOURCE)}] {esc(approach or DEFAULT_APPROACH)} — CPA {esc(cpa)}</b>"
        line = f"{title} ({conditions}, {cap_str})"
        if quote_lines:
            line += "\n<blockquote><b>" + "\n".join(quote_lines) + "</b></blockquote>"
        if rates:
            line += "\n" + ", ".join(rates)
        results.append(line)

    return "\n".join(results)

def send_to_bot(text: str) -> None:
    """Send the text to my Telegram chat. Raises RuntimeError if it fails."""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": OWNER_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except requests.RequestException:
        # текст исходной ошибки содержит токен, поэтому не пробрасываем его
        raise RuntimeError("Could not reach Telegram") from None

    if not response.ok:
        raise RuntimeError(f"Telegram returned HTTP {response.status_code}")
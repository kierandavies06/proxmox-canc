"""Wake-on-LAN helpers."""
from __future__ import annotations

from wakeonlan import send_magic_packet


def wake(mac_address: str) -> None:
    """Dispatch a WOL magic packet to the provided MAC address."""
    send_magic_packet(mac_address)

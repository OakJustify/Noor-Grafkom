"""Unattended wick stations and optional ribbon deposits; no NPCs or dialogue."""

from dataclasses import dataclass, field

INWARD = (
    "Jejak di depan masih jelas. Ikuti cahaya, bukan suara di belakang.",
    "Aku sudah melewati tanda ini. Mengapa arahnya berubah?",
    "Bunyi besi itu makin dekat. Aku tidak ingin menoleh.",
    "Ada langkah ketika aku berhenti. Jangan tinggalkan lentera.",
)


@dataclass
class RefugeBook:
    visited: set = field(default_factory=set)
    threads: set = field(default_factory=set)
    delivered: set = field(default_factory=set)

    def snapshot(self):
        return {"visited": sorted(self.visited), "threads": sorted(self.threads),
                "delivered": sorted(self.delivered)}

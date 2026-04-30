from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone


def normalize_title(title: str) -> str:
    lowered = title.lower()
    lowered = re.sub(r"[^\w\s]", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str = ""

    def published_utc(self) -> datetime:
        if self.published_at.tzinfo is None:
            return self.published_at.replace(tzinfo=timezone.utc)
        return self.published_at.astimezone(timezone.utc)

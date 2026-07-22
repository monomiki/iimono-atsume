from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict


class Notifier(ABC):
    @abstractmethod
    def send_daily(self, payload: Dict) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def send_favorite(self, payload: Dict) -> Dict:
        raise NotImplementedError


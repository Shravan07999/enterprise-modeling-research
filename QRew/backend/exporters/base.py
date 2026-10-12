"""Abstract base exporter."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseExporter(ABC):
    @abstractmethod
    def export(self, model: Dict[str, Any]) -> bytes:
        """Export canonical model to target format."""
        pass
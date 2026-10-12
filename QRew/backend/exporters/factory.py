"""Exporter factory."""

from exporters.base import BaseExporter
from exporters.adl import ADLExporter
from exporters.archimate import ArchiMateExporter


def get_exporter(format: str) -> BaseExporter:
    if format == "adl":
        return ADLExporter()
    elif format == "archimate":
        return ArchiMateExporter()
    else:
        raise ValueError(f"Unknown export format: {format}")
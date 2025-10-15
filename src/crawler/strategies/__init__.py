"""Registro de estratégias de descoberta por origem."""

from __future__ import annotations

from typing import Dict, Iterable

from .fd64e393_159f_4484_9ea4_e9437753791d import GoiasApiDiscovery


STRATEGY_CLASSES = [GoiasApiDiscovery]


def build_strategy_registry(origens: Iterable[dict]):
    """Retorna um dicionário {fonte_origem_id: estrategia} para as origens suportadas."""
    registry: Dict[str, GoiasApiDiscovery] = {}
    for origem in origens:
        for strategy_cls in STRATEGY_CLASSES:
            if strategy_cls.supports(origem):
                registry[str(origem["id"])] = strategy_cls(origem)
                break
    return registry

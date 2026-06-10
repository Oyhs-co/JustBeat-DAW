"""Persistence Ports - Interfaces para persistencia de proyectos.

Define los contratos que AppCore espera de la capa de infraestructura
de persistencia.
"""

from typing import Protocol, Optional, Any
from pathlib import Path


class ProjectManagerProtocol(Protocol):
    """Contrato para el gestor de proyectos."""

    def load(self, path: str) -> Optional[Any]:
        ...

    def save(self, project: Any, path: str) -> bool:
        ...

    def save_project(
        self, data: dict, filepath: Path,
        create_backup: bool = True
    ) -> bool:
        ...


class RecoverySystemProtocol(Protocol):
    """Contrato para el sistema de recuperación."""

    def check_for_recovery(self, project_path: Path) -> Optional[Any]:
        ...

    def save_recovery_point(self, project_path: Path) -> bool:
        ...

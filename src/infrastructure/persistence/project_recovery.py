"""Project Recovery System - Sistema de recuperación de proyectos.

Sistema de recuperación automática de proyectos ante crashes,
incluyendo backups automáticos y versióning.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import logging
import time
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class BackupInfo:
    """Información de backup.
    
    Attributes:
        path: Ruta del archivo de backup
        timestamp: Timestamp de creación
        size_bytes: Tamaño en bytes
        is_automatic: Si es backup automático
        description: Descripción opcional
    """
    path: Path
    timestamp: float
    size_bytes: int
    is_automatic: bool
    description: str = ""


class ProjectRecoverySystem:
    """Sistema de recuperación de proyectos.
    
    Gestiona backups automáticos, recuperación ante crashes
    y versionado de proyectos.
    """
    
    def __init__(
        self,
        backup_dir: Optional[Path] = None,
        max_backups: int = 10,
        auto_backup_interval: int = 300  # 5 minutos
    ):
        """Inicializar sistema de recuperación.
        
        Args:
            backup_dir: Directorio de backups
            max_backups: Máximo de backups a mantener
            auto_backup_interval: Intervalo de backup automático (segundos)
        """
        self._backup_dir = backup_dir or Path("backups")
        self._max_backups = max_backups
        self._auto_backup_interval = auto_backup_interval
        
        # Estado
        self._is_backup_running = False
        self._last_backup_time = 0.0
        
        # Callbacks
        self._on_backup_complete: Optional[Callable[[BackupInfo], None]] = None
        self._on_recovery_complete: Optional[Callable[[bool], None]] = None
        
        # Crear directorio si no existe
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"RecoverySystem inicializado: {self._backup_dir}")
    
    @property
    def backup_dir(self) -> Path:
        """Obtener directorio de backups."""
        return self._backup_dir
    
    @property
    def max_backups(self) -> int:
        """Obtener máximo de backups."""
        return self._max_backups
    
    # === Backups ===
    
    def create_backup(
        self,
        project_path: Path,
        description: str = "",
        is_automatic: bool = False
    ) -> Optional[BackupInfo]:
        """Crear un backup del proyecto.
        
        Args:
            project_path: Ruta del proyecto
            description: Descripción opcional
            is_automatic: Si es backup automático
            
        Returns:
            Información del backup o None
        """
        if not project_path.exists():
            logger.warning(f"Proyecto no existe: {project_path}")
            return None
        
        # Generar nombre de backup
        timestamp = time.time()
        date_str = datetime.fromtimestamp(timestamp).strftime("%Y%m%d_%H%M%S")
        
        if is_automatic:
            backup_name = f"auto_{date_str}.jbak"
        else:
            backup_name = f"manual_{date_str}.jbak"
        
        backup_path = self._backup_dir / backup_name
        
        try:
            # Copiar archivo
            shutil.copy2(project_path, backup_path)
            
            # Obtener tamaño
            size_bytes = backup_path.stat().st_size
            
            # Crear info
            info = BackupInfo(
                path=backup_path,
                timestamp=timestamp,
                size_bytes=size_bytes,
                is_automatic=is_automatic,
                description=description
            )
            
            # Limpiar backups antiguos
            self._cleanup_old_backups()
            
            # Notificar
            if self._on_backup_complete:
                self._on_backup_complete(info)
            
            logger.info(f"Backup creado: {backup_path}")
            return info
            
        except Exception as e:
            logger.error(f"Error creando backup: {e}")
            return None
    
    def restore_from_backup(
        self,
        backup_path: Path,
        destination_path: Optional[Path] = None
    ) -> bool:
        """Restaurar proyecto desde backup.
        
        Args:
            backup_path: Ruta del backup
            destination_path: Destino (mismo que origen si es None)
            
        Returns:
            True si fue exitoso
        """
        if not backup_path.exists():
            logger.error(f"Backup no existe: {backup_path}")
            return False
        
        if destination_path is None:
            # Asumir mismo directorio que el backup
            destination_path = backup_path.with_suffix("")
        
        try:
            # Crear backup del estado actual antes de restaurar
            if destination_path.exists():
                self.create_backup(
                    destination_path,
                    description="Pre-restauración",
                    is_automatic=True
                )
            
            # Copiar backup
            shutil.copy2(backup_path, destination_path)
            
            logger.info(f"Proyecto restaurado: {destination_path}")
            
            if self._on_recovery_complete:
                self._on_recovery_complete(True)
            
            return True
            
        except Exception as e:
            logger.error(f"Error restaurando proyecto: {e}")
            
            if self._on_recovery_complete:
                self._on_recovery_complete(False)
            
            return False
    
    def get_backups(self) -> List[BackupInfo]:
        """Obtener lista de backups disponibles.
        
        Returns:
            Lista de backups
        """
        backups = []
        
        for file_path in self._backup_dir.glob("*.jbak"):
            try:
                stat = file_path.stat()
                is_auto = file_path.name.startswith("auto_")
                
                info = BackupInfo(
                    path=file_path,
                    timestamp=stat.st_mtime,
                    size_bytes=stat.st_size,
                    is_automatic=is_auto
                )
                backups.append(info)
                
            except Exception as e:
                logger.warning(f"Error leyendo backup {file_path}: {e}")
        
        # Ordenar por timestamp descendente
        backups.sort(key=lambda b: b.timestamp, reverse=True)
        
        return backups
    
    def get_latest_backup(self) -> Optional[BackupInfo]:
        """Obtener el backup más reciente.
        
        Returns:
            Backup más reciente o None
        """
        backups = self.get_backups()
        return backups[0] if backups else None
    
    def get_automatic_backups(self) -> List[BackupInfo]:
        """Obtener solo backups automáticos.
        
        Returns:
            Lista de backups automáticos
        """
        return [b for b in self.get_backups() if b.is_automatic]
    
    def delete_backup(self, backup_path: Path) -> bool:
        """Eliminar un backup.
        
        Args:
            backup_path: Ruta del backup
            
        Returns:
            True si fue exitoso
        """
        try:
            backup_path.unlink()
            logger.info(f"Backup eliminado: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error eliminando backup: {e}")
            return False
    
    def _cleanup_old_backups(self) -> int:
        """Limpiar backups antiguos.
        
        Returns:
            Número de backups eliminados
        """
        backups = self.get_backups()
        
        if len(backups) <= self._max_backups:
            return 0
        
        # Eliminar los más antiguos
        deleted = 0
        for backup in backups[self._max_backups:]:
            if self.delete_backup(backup.path):
                deleted += 1
        
        return deleted
    
    # === Recuperación automática ===
    
    def check_for_recovery(
        self,
        project_path: Path
    ) -> Optional[BackupInfo]:
        """Verificar si hay recuperación pendiente.
        
        Args:
            project_path: Ruta del proyecto
            
        Returns:
            Backup más reciente o None
        """
        # Buscar recovery.lock
        recovery_lock = self._backup_dir / "recovery.lock"
        
        if not recovery_lock.exists():
            return None
        
        try:
            # Leer info de recuperación
            with open(recovery_lock, 'r') as f:
                data = json.load(f)
            
            last_backup_path = Path(data.get("last_backup", ""))
            
            if last_backup_path.exists():
                # Verificar si es más reciente que el proyecto
                project_mtime = project_path.stat().st_mtime if project_path.exists() else 0
                backup_mtime = last_backup_path.stat().st_mtime
                
                if backup_mtime > project_mtime:
                    logger.info(f"Recuperación disponible: {last_backup_path}")
                    return BackupInfo(
                        path=last_backup_path,
                        timestamp=backup_mtime,
                        size_bytes=last_backup_path.stat().st_size,
                        is_automatic=True,
                        description="Recuperación automática"
                    )
            
            # Limpiar lock
            recovery_lock.unlink()
            
        except Exception as e:
            logger.warning(f"Error verificando recuperación: {e}")
        
        return None
    
    def save_recovery_point(
        self,
        project_path: Path
    ) -> None:
        """Guardar punto de recuperación.
        
        Args:
            project_path: Ruta del proyecto
        """
        recovery_lock = self._backup_dir / "recovery.lock"
        
        try:
            # Crear backup rápido
            backup_info = self.create_backup(
                project_path,
                description="Punto de recuperación",
                is_automatic=True
            )
            
            if backup_info:
                # Escribir lock
                with open(recovery_lock, 'w') as f:
                    json.dump({
                        "last_backup": str(backup_info.path),
                        "timestamp": backup_info.timestamp
                    })
                
                logger.debug(f"Punto de recuperación guardado: {project_path}")
            
        except Exception as e:
            logger.error(f"Error guardando punto de recuperación: {e}")
    
    def clear_recovery_point(self) -> None:
        """Limpiar punto de recuperación."""
        recovery_lock = self._backup_dir / "recovery.lock"
        
        if recovery_lock.exists():
            recovery_lock.unlink()
            logger.info("Punto de recuperación limpiado")
    
    # === Utilidades ===
    
    def get_backup_size_mb(self) -> float:
        """Obtener tamaño total de backups en MB."""
        total = 0
        for backup in self.get_backups():
            total += backup.size_bytes
        return total / (1024 * 1024)
    
    def export_backups_info(self) -> List[Dict]:
        """Exportar información de backups.
        
        Returns:
            Lista de diccionarios con información
        """
        return [
            {
                "path": str(b.path.name),
                "timestamp": datetime.fromtimestamp(b.timestamp).isoformat(),
                "size_mb": b.size_bytes / (1024 * 1024),
                "type": "automatic" if b.is_automatic else "manual",
                "description": b.description
            }
            for b in self.get_backups()
        ]
    
    # === Callbacks ===
    
    def set_backup_complete_callback(
        self,
        callback: Callable[[BackupInfo], None]
    ) -> None:
        """Establecer callback de completado de backup."""
        self._on_backup_complete = callback
    
    def set_recovery_complete_callback(
        self,
        callback: Callable[[bool], None]
    ) -> None:
        """Establecer callback de completado de recuperación."""
        self._on_recovery_complete = callback

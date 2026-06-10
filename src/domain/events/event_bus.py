"""Event Bus - Sistema de eventos para el dominio.

Implementa el patrón Event Bus para comunicación desacoplada
entre componentes del dominio.
"""

from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
import uuid


logger = logging.getLogger(__name__)


@dataclass
class DomainEvent:
    """Evento base del dominio."""
    event_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    
    def __post_init__(self):
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EventBus:
    """Bus de eventos para comunicación desacoplada.
    
    Permite que diferentes componentes del sistema se comuniquen
    sin conocimiento directo entre sí.
    """
    
    def __init__(self):
        """Inicializar el bus de eventos."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[DomainEvent] = []
        self._max_history = 1000
        self._is_enabled = True
        
        logger.info("EventBus inicializado")
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable[[DomainEvent], None]
    ) -> None:
        """Suscribirse a un tipo de evento.
        
        Args:
            event_type: Tipo de evento (ej: "project.created")
            handler: Función que maneja el evento
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            logger.debug(f"Suscrito a evento: {event_type}")
    
    def unsubscribe(
        self,
        event_type: str,
        handler: Callable[[DomainEvent], None]
    ) -> bool:
        """Cancelar suscripción a un evento.
        
        Args:
            event_type: Tipo de evento
            handler: Handler a remover
            
        Returns:
            True si se removió correctamente
        """
        if event_type in self._subscribers:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"Desuscrito de evento: {event_type}")
                return True
        return False
    
    def publish(self, event: DomainEvent) -> None:
        """Publicar un evento.
        
        Args:
            event: Evento a publicar
        """
        if not self._is_enabled:
            return
        
        # Agregar a historial
        self._add_to_history(event)
        
        # Notificar suscriptores
        event_type = event.event_type
        
        # Suscriptores específicos
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error en handler de {event_type}: {e}")
        
        # Suscriptores wildcard (*)
        if "*" in self._subscribers:
            for handler in self._subscribers["*"]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error en handler wildcard: {e}")
    
    def publish_simple(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Publicar un evento simple.
        
        Args:
            event_type: Tipo de evento
            data: Datos del evento
        """
        event = DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            data=data or {}
        )
        self.publish(event)
    
    def _add_to_history(self, event: DomainEvent) -> None:
        """Agregar evento al historial."""
        self._event_history.append(event)
        
        # Limpiar historial si excede el máximo
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
    
    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[DomainEvent]:
        """Obtener historial de eventos.
        
        Args:
            event_type: Filtrar por tipo de evento
            limit: Número máximo de eventos
            
        Returns:
            Lista de eventos
        """
        if event_type:
            events = [
                e for e in self._event_history
                if e.event_type == event_type
            ]
        else:
            events = self._event_history
        
        return events[-limit:]
    
    def clear_history(self) -> None:
        """Limpiar historial de eventos."""
        self._event_history.clear()
        logger.debug("Historial de eventos limpiado")
    
    def enable(self) -> None:
        """Habilitar el bus de eventos."""
        self._is_enabled = True
        logger.debug("EventBus habilitado")
    
    def disable(self) -> None:
        """Deshabilitar el bus de eventos."""
        self._is_enabled = False
        logger.debug("EventBus deshabilitado")
    
    @property
    def is_enabled(self) -> bool:
        """Verificar si el bus está habilitado."""
        return self._is_enabled
    
    def get_subscriber_count(self, event_type: str) -> int:
        """Obtener número de suscriptores para un tipo de evento."""
        return len(self._subscribers.get(event_type, []))


# Instancia global del EventBus
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Obtener la instancia global del EventBus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def set_event_bus(bus: EventBus) -> None:
    """Establecer una instancia específica del EventBus."""
    global _event_bus
    _event_bus = bus


# Clases helper para crear eventos específicos


class ProjectEvents:
    """Eventos relacionados con proyectos."""
    
    @staticmethod
    def created(project_name: str, project_id: str) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="project.created",
            timestamp=datetime.now(),
            data={"name": project_name, "id": project_id}
        )
    
    @staticmethod
    def loaded(project_name: str, project_id: str) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="project.loaded",
            timestamp=datetime.now(),
            data={"name": project_name, "id": project_id}
        )
    
    @staticmethod
    def saved(project_id: str, path: str) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="project.saved",
            timestamp=datetime.now(),
            data={"id": project_id, "path": path}
        )
    
    @staticmethod
    def modified(project_id: str) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="project.modified",
            timestamp=datetime.now(),
            data={"id": project_id}
        )


class TransportEvents:
    """Eventos relacionados con el transporte."""
    
    @staticmethod
    def started() -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="transport.started",
            timestamp=datetime.now(),
            data={}
        )
    
    @staticmethod
    def stopped() -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="transport.stopped",
            timestamp=datetime.now(),
            data={}
        )
    
    @staticmethod
    def paused() -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="transport.paused",
            timestamp=datetime.now(),
            data={}
        )
    
    @staticmethod
    def position_changed(position: int) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="transport.position_changed",
            timestamp=datetime.now(),
            data={"position": position}
        )
    
    @staticmethod
    def bpm_changed(bpm: int) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="transport.bpm_changed",
            timestamp=datetime.now(),
            data={"bpm": bpm}
        )


class TrackEvents:
    """Eventos relacionados con pistas."""
    
    @staticmethod
    def added(track_id: str, track_name: str) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="track.added",
            timestamp=datetime.now(),
            data={"id": track_id, "name": track_name}
        )
    
    @staticmethod
    def removed(track_id: str) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="track.removed",
            timestamp=datetime.now(),
            data={"id": track_id}
        )
    
    @staticmethod
    def modified(track_id: str, changes: dict) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="track.modified",
            timestamp=datetime.now(),
            data={"id": track_id, "changes": changes}
        )


class NoteEvents:
    """Eventos relacionados con notas."""
    
    @staticmethod
    def added(note_id: str, track_id: str, pitch: int) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="note.added",
            timestamp=datetime.now(),
            data={"id": note_id, "track_id": track_id, "pitch": pitch}
        )
    
    @staticmethod
    def removed(note_id: str, track_id: str) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="note.removed",
            timestamp=datetime.now(),
            data={"id": note_id, "track_id": track_id}
        )
    
    @staticmethod
    def modified(note_id: str, changes: dict) -> DomainEvent:
        return DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type="note.modified",
            timestamp=datetime.now(),
            data={"id": note_id, "changes": changes}
        )

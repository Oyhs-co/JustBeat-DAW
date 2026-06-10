"""Command History - Sistema de Undo/Redo.

Implementa el patrón Command con historial para deshacer
y rehacer operaciones.
"""

from typing import Callable, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
import logging
import copy


logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Tipos de comando."""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    MOVE = "move"
    GROUP = "group"


@dataclass
class Command:
    """Comando ejecutable.
    
    Attributes:
        command_type: Tipo de comando
        execute: Función de ejecución
        undo: Función de deshacer
        description: Descripción legible
        data: Datos adicionales
    """
    command_type: CommandType
    execute: Callable[[], Any]
    undo: Callable[[], None]
    description: str
    data: Optional[dict] = None


class CommandHistory:
    """Historial de comandos para undo/redo.
    
    Mantiene dos pilas: una para deshacer y otra para rehacer.
    """
    
    MAX_HISTORY = 100
    
    def __init__(self, max_history: int = MAX_HISTORY):
        """Inicializar historial.
        
        Args:
            max_history: Máximo de comandos en historial
        """
        self._max_history = max_history
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._is_executing = False
        
        logger.info(f"CommandHistory inicializado: max={max_history}")
    
    @property
    def can_undo(self) -> bool:
        """Verificar si hay comandos para deshacer."""
        return len(self._undo_stack) > 0
    
    @property
    def can_redo(self) -> bool:
        """Verificar si hay comandos para rehacer."""
        return len(self._redo_stack) > 0
    
    @property
    def undo_description(self) -> Optional[str]:
        """Obtener descripción del próximo undo."""
        if self._undo_stack:
            return self._undo_stack[-1].description
        return None
    
    @property
    def redo_description(self) -> Optional[str]:
        """Obtener descripción del próximo redo."""
        if self._redo_stack:
            return self._redo_stack[-1].description
        return None
    
    @property
    def undo_count(self) -> int:
        """Obtener número de comandos para deshacer."""
        return len(self._undo_stack)
    
    @property
    def redo_count(self) -> int:
        """Obtener número de comandos para rehacer."""
        return len(self._redo_stack)
    
    def execute(self, command: Command) -> Any:
        """Ejecutar un comando.
        
        Args:
            command: Comando a ejecutar
            
        Returns:
            Resultado de la ejecución
        """
        if self._is_executing:
            logger.warning("Ya hay una ejecución en progreso")
            return None
        
        self._is_executing = True
        
        try:
            # Ejecutar comando
            result = command.execute()
            
            # Añadir a historial de undo
            self._undo_stack.append(command)
            
            # Limpiar redo stack
            self._redo_stack.clear()
            
            # Limitar tamaño del historial
            if len(self._undo_stack) > self._max_history:
                self._undo_stack.pop(0)
            
            logger.debug(f"Comando ejecutado: {command.description}")
            return result
            
        except Exception as e:
            logger.error(f"Error ejecutando comando: {e}")
            raise
            
        finally:
            self._is_executing = False
    
    def undo(self) -> bool:
        """Deshacer último comando.
        
        Returns:
            True si fue exitoso
        """
        if not self.can_undo:
            logger.debug("No hay comandos para deshacer")
            return False
        
        if self._is_executing:
            logger.warning("Ya hay una ejecución en progreso")
            return False
        
        self._is_executing = True
        
        try:
            # Pop del comando
            command = self._undo_stack.pop()
            
            # Ejecutar undo
            command.undo()
            
            # Añadir a redo stack
            self._redo_stack.append(command)
            
            logger.debug(f"Deshacer: {command.description}")
            return True
            
        except Exception as e:
            logger.error(f"Error en undo: {e}")
            return False
            
        finally:
            self._is_executing = False
    
    def redo(self) -> bool:
        """Rehacer último comando deshecho.
        
        Returns:
            True si fue exitoso
        """
        if not self.can_redo:
            logger.debug("No hay comandos para rehacer")
            return False
        
        if self._is_executing:
            logger.warning("Ya hay una ejecución en progreso")
            return False
        
        self._is_executing = True
        
        try:
            # Pop del comando
            command = self._redo_stack.pop()
            
            # Ejecutar comando de nuevo
            command.execute()
            
            # Añadir de vuelta al undo stack
            self._undo_stack.append(command)
            
            logger.debug(f"Rehacer: {command.description}")
            return True
            
        except Exception as e:
            logger.error(f"Error en redo: {e}")
            return False
            
        finally:
            self._is_executing = False
    
    def clear(self) -> None:
        """Limpiar todo el historial."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        logger.debug("Historial limpiado")
    
    def get_history(self) -> List[str]:
        """Obtener lista de comandos en historial.
        
        Returns:
            Lista de descripciones
        """
        return [cmd.description for cmd in self._undo_stack]


# === Comandos predefinidos ===

def make_add_command(
    collection: list,
    item: Any,
    description: str = "Añadir elemento"
) -> Command:
    """Crear comando para añadir elemento.
    
    Args:
        collection: Colección destino
        item: Elemento a añadir
        description: Descripción
        
    Returns:
        Comando
    """
    def execute():
        collection.append(item)
    
    def undo():
        if item in collection:
            collection.remove(item)
    
    return Command(
        command_type=CommandType.CREATE,
        execute=execute,
        undo=undo,
        description=description,
        data={"item": item}
    )


def make_remove_command(
    collection: list,
    item: Any,
    description: str = "Remover elemento"
) -> Command:
    """Crear comando para remover elemento.
    
    Args:
        collection: Colección origen
        item: Elemento a remover
        description: Descripción
        
    Returns:
        Comando
    """
    index = collection.index(item) if item in collection else -1
    
    def execute():
        if item in collection:
            collection.remove(item)
    
    def undo():
        if index >= 0:
            collection.insert(index, item)
    
    return Command(
        command_type=CommandType.DELETE,
        execute=execute,
        undo=undo,
        description=description,
        data={"item": item, "index": index}
    )


def make_modify_command(
    target: Any,
    attribute: str,
    new_value: Any,
    old_value: Optional[Any] = None,
    description: str = "Modificar atributo"
) -> Command:
    """Crear comando para modificar atributo.
    
    Args:
        target: Objeto destino
        attribute: Nombre del atributo
        new_value: Nuevo valor
        old_value: Valor anterior (opcional)
        description: Descripción
        
    Returns:
        Comando
    """
    # Obtener valor actual si no se proporciona
    if old_value is None:
        old_value = getattr(target, attribute)
    
    def execute():
        setattr(target, attribute, new_value)
    
    def undo():
        setattr(target, attribute, old_value)
    
    return Command(
        command_type=CommandType.MODIFY,
        execute=execute,
        undo=undo,
        description=description,
        data={"attribute": attribute, "old": old_value, "new": new_value}
    )


def make_move_command(
    collection: list,
    from_index: int,
    to_index: int,
    description: str = "Mover elemento"
) -> Command:
    """Crear comando para mover elemento.
    
    Args:
        collection: Colección
        from_index: Índice origen
        to_index: Índice destino
        description: Descripción
        
    Returns:
        Comando
    """
    def execute():
        item = collection.pop(from_index)
        collection.insert(to_index, item)
    
    def undo():
        item = collection.pop(to_index)
        collection.insert(from_index, item)
    
    return Command(
        command_type=CommandType.MOVE,
        execute=execute,
        undo=undo,
        description=description,
        data={"from": from_index, "to": to_index}
    )


# === Grupo de comandos ===

class CommandGroup:
    """Grupo de comandos para operaciones atómicas.
    
    Permite ejecutar múltiples comandos como una sola operación.
    """
    
    def __init__(self, description: str = "Grupo de comandos"):
        """Inicializar grupo.
        
        Args:
            description: Descripción del grupo
        """
        self._description = description
        self._commands: List[Command] = []
    
    def add(self, command: Command) -> None:
        """Añadir comando al grupo.
        
        Args:
            command: Comando a añadir
        """
        self._commands.append(command)
    
    def execute(self) -> List[Any]:
        """Ejecutar todos los comandos.
        
        Returns:
            Lista de resultados
        """
        results = []
        for cmd in self._commands:
            results.append(cmd.execute())
        return results
    
    def undo(self) -> None:
        """Deshacer todos los comandos en orden inverso."""
        for cmd in reversed(self._commands):
            cmd.undo()
    
    @property
    def description(self) -> str:
        """Obtener descripción."""
        return self._description
    
    @property
    def command_count(self) -> int:
        """Obtener número de comandos."""
        return len(self._commands)


def make_group_command(
    commands: List[Command],
    description: str = "Grupo de comandos"
) -> Command:
    """Crear comando de grupo.
    
    Args:
        commands: Lista de comandos
        description: Descripción
        
    Returns:
        Comando grupo
    """
    group = CommandGroup(description)
    for cmd in commands:
        group.add(cmd)
    
    def execute():
        group.execute()
    
    def undo():
        group.undo()
    
    return Command(
        command_type=CommandType.GROUP,
        execute=execute,
        undo=undo,
        description=description,
        data={"command_count": len(commands)}
    )

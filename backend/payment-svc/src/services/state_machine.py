"""
Реализация конечного автомата для управления состояниями транзакций
"""

import logging
import asyncio
from enum import Enum
from typing import Dict, List, Callable, Any, Set, Optional, TypeVar, Generic, Type
from datetime import datetime
import json

from ..models.transaction import TransactionStatus, Transaction
from .event_service import EventType, EventPayload, get_event_service

logger = logging.getLogger(__name__)

# Определяем типы для состояний и событий
S = TypeVar('S', bound=Enum)  # Тип для состояний
E = TypeVar('E', bound=Enum)  # Тип для событий

class InvalidTransitionError(Exception):
    """Ошибка при недопустимом переходе состояния"""
    pass

class StateMachine(Generic[S, E]):
    """
    Обобщенный конечный автомат для управления состояниями
    """
    
    def __init__(self, 
                 initial_state: S,
                 state_class: Type[S],
                 event_class: Type[E]):
        """
        Инициализация конечного автомата
        
        Args:
            initial_state: Начальное состояние
            state_class: Класс перечисления состояний
            event_class: Класс перечисления событий
        """
        self.current_state = initial_state
        self.state_class = state_class
        self.event_class = event_class
        
        # Определение допустимых переходов: {состояние: {событие: новое_состояние}}
        self.transitions: Dict[S, Dict[E, S]] = {state: {} for state in state_class}
        
        # Обработчики переходов: {состояние: {событие: [обработчики]}}
        self.handlers: Dict[S, Dict[E, List[Callable[[S, S, Any], None]]]] = {
            state: {event: [] for event in event_class} for state in state_class
        }
        
        # История переходов
        self.history: List[Dict[str, Any]] = []
        
        # Максимальный размер истории
        self.max_history_size = 100
    
    def add_transition(self, from_state: S, event: E, to_state: S) -> None:
        """
        Добавление допустимого перехода в конечный автомат
        
        Args:
            from_state: Исходное состояние
            event: Событие, вызывающее переход
            to_state: Целевое состояние
        """
        if from_state not in self.transitions:
            self.transitions[from_state] = {}
        
        self.transitions[from_state][event] = to_state
        
        logger.debug(f"Добавлен переход: {from_state} --({event})--> {to_state}")
    
    def add_handler(self, state: S, event: E, handler: Callable[[S, S, Any], None]) -> None:
        """
        Добавление обработчика перехода
        
        Args:
            state: Состояние
            event: Событие
            handler: Функция-обработчик, принимающая (from_state, to_state, data)
        """
        if state not in self.handlers:
            self.handlers[state] = {}
        
        if event not in self.handlers[state]:
            self.handlers[state][event] = []
        
        self.handlers[state][event].append(handler)
        
        logger.debug(f"Добавлен обработчик для перехода {state} --({event})-->")
    
    def trigger(self, event: E, data: Any = None) -> S:
        """
        Выполнение перехода по событию
        
        Args:
            event: Событие, вызывающее переход
            data: Дополнительные данные для передачи обработчикам
            
        Returns:
            Новое состояние
            
        Raises:
            InvalidTransitionError: Если переход недопустим
        """
        if event not in self.transitions.get(self.current_state, {}):
            raise InvalidTransitionError(
                f"Недопустимый переход: {self.current_state} --({event})-->"
            )
        
        previous_state = self.current_state
        new_state = self.transitions[previous_state][event]
        
        # Обновляем текущее состояние
        self.current_state = new_state
        
        # Записываем в историю
        transition_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "from_state": str(previous_state),
            "event": str(event),
            "to_state": str(new_state),
            "data": json.dumps(data) if data else None
        }
        self.history.append(transition_record)
        
        # Ограничиваем размер истории
        if len(self.history) > self.max_history_size:
            self.history.pop(0)
        
        # Вызываем обработчики
        if previous_state in self.handlers and event in self.handlers[previous_state]:
            for handler in self.handlers[previous_state][event]:
                try:
                    handler(previous_state, new_state, data)
                except Exception as e:
                    logger.error(f"Ошибка в обработчике перехода {previous_state} --({event})--> {new_state}: {str(e)}")
        
        logger.info(f"Выполнен переход: {previous_state} --({event})--> {new_state}")
        
        return new_state
    
    def can_trigger(self, event: E) -> bool:
        """
        Проверка возможности перехода по событию
        
        Args:
            event: Событие для проверки
            
        Returns:
            True, если переход возможен, иначе False
        """
        return event in self.transitions.get(self.current_state, {})
    
    def get_available_events(self) -> List[E]:
        """
        Получение списка доступных событий в текущем состоянии
        
        Returns:
            Список доступных событий
        """
        return list(self.transitions.get(self.current_state, {}).keys())
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        Получение истории переходов
        
        Returns:
            Список записей о переходах
        """
        return self.history

class TransactionEvent(str, Enum):
    """События для управления транзакциями"""
    CREATE = "create"
    PROCESS_PAYMENT = "process_payment"
    HOLD_IN_ESCROW = "hold_in_escrow"
    RELEASE_FROM_ESCROW = "release_from_escrow"
    REFUND = "refund"
    DISPUTE = "dispute"
    RESOLVE_DISPUTE = "resolve_dispute"
    CANCEL = "cancel"
    FAIL = "fail"

class TransactionStateMachine:
    """
    Конечный автомат для управления состояниями транзакций
    """
    
    def __init__(self, transaction_id: int, current_state: TransactionStatus):
        """
        Инициализация конечного автомата для конкретной транзакции
        
        Args:
            transaction_id: ID транзакции
            current_state: Текущее состояние транзакции
        """
        self.transaction_id = transaction_id
        self.state_machine = StateMachine(
            initial_state=current_state,
            state_class=TransactionStatus,
            event_class=TransactionEvent
        )
        
        # Настраиваем допустимые переходы
        self._configure_transitions()
        
        # Настраиваем обработчики событий
        self._configure_handlers()
        
        # Сервис для работы с событиями
        self.event_service = get_event_service()
        
        logger.info(f"Инициализирован конечный автомат для транзакции {transaction_id}")
    
    def _configure_transitions(self) -> None:
        """Настройка допустимых переходов между состояниями"""
        sm = self.state_machine
        
        # Из состояния PENDING
        sm.add_transition(TransactionStatus.PENDING, TransactionEvent.PROCESS_PAYMENT, TransactionStatus.ESCROW_HELD)
        sm.add_transition(TransactionStatus.PENDING, TransactionEvent.CANCEL, TransactionStatus.CANCELED)
        sm.add_transition(TransactionStatus.PENDING, TransactionEvent.FAIL, TransactionStatus.FAILED)
        
        # Из состояния ESCROW_HELD
        sm.add_transition(TransactionStatus.ESCROW_HELD, TransactionEvent.RELEASE_FROM_ESCROW, TransactionStatus.COMPLETED)
        sm.add_transition(TransactionStatus.ESCROW_HELD, TransactionEvent.REFUND, TransactionStatus.REFUNDED)
        sm.add_transition(TransactionStatus.ESCROW_HELD, TransactionEvent.DISPUTE, TransactionStatus.DISPUTED)
        sm.add_transition(TransactionStatus.ESCROW_HELD, TransactionEvent.CANCEL, TransactionStatus.CANCELED)
        
        # Из состояния DISPUTED
        sm.add_transition(TransactionStatus.DISPUTED, TransactionEvent.RESOLVE_DISPUTE, TransactionStatus.COMPLETED)
        sm.add_transition(TransactionStatus.DISPUTED, TransactionEvent.REFUND, TransactionStatus.REFUNDED)
        
        logger.debug("Настроены переходы между состояниями транзакции")
    
    def _configure_handlers(self) -> None:
        """Настройка обработчиков событий"""
        sm = self.state_machine
        
        # Обработчики для события PROCESS_PAYMENT
        sm.add_handler(
            TransactionStatus.PENDING, 
            TransactionEvent.PROCESS_PAYMENT, 
            self._handle_process_payment
        )
        
        # Обработчики для события RELEASE_FROM_ESCROW
        sm.add_handler(
            TransactionStatus.ESCROW_HELD,
            TransactionEvent.RELEASE_FROM_ESCROW,
            self._handle_release_from_escrow
        )
        
        # Обработчики для события REFUND
        sm.add_handler(
            TransactionStatus.ESCROW_HELD,
            TransactionEvent.REFUND,
            self._handle_refund
        )
        
        # Обработчики для события DISPUTE
        sm.add_handler(
            TransactionStatus.ESCROW_HELD,
            TransactionEvent.DISPUTE,
            self._handle_dispute
        )
        
        # Обработчики для события RESOLVE_DISPUTE
        sm.add_handler(
            TransactionStatus.DISPUTED,
            TransactionEvent.RESOLVE_DISPUTE,
            self._handle_resolve_dispute
        )
        
        # Обработчики для события CANCEL
        sm.add_handler(
            TransactionStatus.PENDING,
            TransactionEvent.CANCEL,
            self._handle_cancel
        )
        
        sm.add_handler(
            TransactionStatus.ESCROW_HELD,
            TransactionEvent.CANCEL,
            self._handle_cancel
        )
        
        # Обработчики для события FAIL
        sm.add_handler(
            TransactionStatus.PENDING,
            TransactionEvent.FAIL,
            self._handle_fail
        )
        
        logger.debug("Настроены обработчики событий транзакции")
    
    def _handle_process_payment(self, from_state: TransactionStatus, 
                              to_state: TransactionStatus, data: Any) -> None:
        """
        Обработчик события обработки платежа
        
        Args:
            from_state: Предыдущее состояние
            to_state: Новое состояние
            data: Дополнительные данные
        """
        logger.info(f"Транзакция {self.transaction_id} переведена в Escrow")
        
        # Публикуем событие
        event_data = {
            "transaction_id": self.transaction_id,
            "from_state": str(from_state),
            "to_state": str(to_state),
            "data": data
        }
        
        event_payload = EventPayload(
            event_type=EventType.ESCROW_FUNDS_HELD,
            data=event_data
        )
        
        asyncio.create_task(self.event_service.publish(event_payload))
    
    def _handle_release_from_escrow(self, from_state: TransactionStatus, 
                                  to_state: TransactionStatus, data: Any) -> None:
        """
        Обработчик события освобождения средств из Escrow
        
        Args:
            from_state: Предыдущее состояние
            to_state: Новое состояние
            data: Дополнительные данные
        """
        logger.info(f"Средства из Escrow для транзакции {self.transaction_id} переведены продавцу")
        
        # Публикуем событие
        event_data = {
            "transaction_id": self.transaction_id,
            "from_state": str(from_state),
            "to_state": str(to_state),
            "data": data
        }
        
        event_payload = EventPayload(
            event_type=EventType.ESCROW_FUNDS_RELEASED,
            data=event_data
        )
        
        asyncio.create_task(self.event_service.publish(event_payload))
    
    def _handle_refund(self, from_state: TransactionStatus, 
                     to_state: TransactionStatus, data: Any) -> None:
        """
        Обработчик события возврата средств
        
        Args:
            from_state: Предыдущее состояние
            to_state: Новое состояние
            data: Дополнительные данные
        """
        logger.info(f"Возврат средств для транзакции {self.transaction_id}")
        
        # Публикуем событие
        event_data = {
            "transaction_id": self.transaction_id,
            "from_state": str(from_state),
            "to_state": str(to_state),
            "data": data
        }
        
        event_payload = EventPayload(
            event_type=EventType.ESCROW_FUNDS_REFUNDED,
            data=event_data
        )
        
        asyncio.create_task(self.event_service.publish(event_payload))
    
    def _handle_dispute(self, from_state: TransactionStatus, 
                      to_state: TransactionStatus, data: Any) -> None:
        """
        Обработчик события открытия спора
        
        Args:
            from_state: Предыдущее состояние
            to_state: Новое состояние
            data: Дополнительные данные
        """
        logger.info(f"Открыт спор для транзакции {self.transaction_id}")
        
        # Публикуем событие
        event_data = {
            "transaction_id": self.transaction_id,
            "from_state": str(from_state),
            "to_state": str(to_state),
            "data": data
        }
        
        event_payload = EventPayload(
            event_type=EventType.TRANSACTION_DISPUTED,
            data=event_data
        )
        
        asyncio.create_task(self.event_service.publish(event_payload))
    
    def _handle_resolve_dispute(self, from_state: TransactionStatus, 
                              to_state: TransactionStatus, data: Any) -> None:
        """
        Обработчик события разрешения спора
        
        Args:
            from_state: Предыдущее состояние
            to_state: Новое состояние
            data: Дополнительные данные
        """
        logger.info(f"Спор для транзакции {self.transaction_id} разрешен")
        
        # Публикуем событие
        event_data = {
            "transaction_id": self.transaction_id,
            "from_state": str(from_state),
            "to_state": str(to_state),
            "resolution": data.get("resolution") if data else "unknown",
            "data": data
        }
        
        event_payload = EventPayload(
            event_type=EventType.TRANSACTION_COMPLETED,
            data=event_data
        )
        
        asyncio.create_task(self.event_service.publish(event_payload))
    
    def _handle_cancel(self, from_state: TransactionStatus, 
                     to_state: TransactionStatus, data: Any) -> None:
        """
        Обработчик события отмены транзакции
        
        Args:
            from_state: Предыдущее состояние
            to_state: Новое состояние
            data: Дополнительные данные
        """
        logger.info(f"Отмена транзакции {self.transaction_id}")
        
        # Публикуем событие
        event_data = {
            "transaction_id": self.transaction_id,
            "from_state": str(from_state),
            "to_state": str(to_state),
            "reason": data.get("reason") if data else "unknown",
            "data": data
        }
        
        event_payload = EventPayload(
            event_type=EventType.TRANSACTION_CANCELED,
            data=event_data
        )
        
        asyncio.create_task(self.event_service.publish(event_payload))
    
    def _handle_fail(self, from_state: TransactionStatus, 
                   to_state: TransactionStatus, data: Any) -> None:
        """
        Обработчик события неудачной транзакции
        
        Args:
            from_state: Предыдущее состояние
            to_state: Новое состояние
            data: Дополнительные данные
        """
        logger.info(f"Ошибка транзакции {self.transaction_id}")
        
        # Публикуем событие
        event_data = {
            "transaction_id": self.transaction_id,
            "from_state": str(from_state),
            "to_state": str(to_state),
            "error": data.get("error") if data else "unknown",
            "data": data
        }
        
        event_payload = EventPayload(
            event_type=EventType.TRANSACTION_FAILED,
            data=event_data
        )
        
        asyncio.create_task(self.event_service.publish(event_payload))
    
    def trigger(self, event: TransactionEvent, data: Any = None) -> TransactionStatus:
        """
        Выполнение перехода по событию
        
        Args:
            event: Событие для выполнения перехода
            data: Дополнительные данные
            
        Returns:
            Новое состояние транзакции
            
        Raises:
            InvalidTransitionError: Если переход недопустим
        """
        return self.state_machine.trigger(event, data)
    
    def get_current_state(self) -> TransactionStatus:
        """
        Получение текущего состояния транзакции
        
        Returns:
            Текущее состояние
        """
        return self.state_machine.current_state
    
    def get_available_events(self) -> List[TransactionEvent]:
        """
        Получение списка доступных событий в текущем состоянии
        
        Returns:
            Список доступных событий
        """
        return self.state_machine.get_available_events()
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        Получение истории переходов
        
        Returns:
            Список записей о переходах
        """
        return self.state_machine.get_history()
    
    def get_states(self) -> List[TransactionStatus]:
        """
        Получение списка всех возможных состояний транзакции
        
        Returns:
            Список всех состояний
        """
        return list(TransactionStatus)
    
    def update_state(self, new_state: TransactionStatus) -> None:
        """
        Принудительное обновление состояния конечного автомата
        
        Args:
            new_state: Новое состояние
        """
        self.state_machine.current_state = new_state
        logger.info(f"Состояние транзакции {self.transaction_id} принудительно обновлено до {new_state}")

# Фабрика для создания конечных автоматов транзакций
class TransactionStateMachineFactory:
    """
    Фабрика для создания конечных автоматов транзакций
    """
    
    _instances: Dict[int, TransactionStateMachine] = {}
    
    @classmethod
    def get_state_machine(cls, transaction_id: int, current_state: TransactionStatus) -> TransactionStateMachine:
        """
        Получение экземпляра конечного автомата для транзакции
        
        Args:
            transaction_id: ID транзакции
            current_state: Текущее состояние транзакции
        Returns:
            Экземпляр конечного автомата
        """
        if transaction_id not in cls._instances:
            cls._instances[transaction_id] = TransactionStateMachine(transaction_id, current_state)
        
        return cls._instances[transaction_id] 
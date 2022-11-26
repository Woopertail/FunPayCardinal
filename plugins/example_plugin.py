"""
Данный плагин является шаблоном для других плагинов.
Учтите, что хэндлеры выполняются в основном потоке. Если выполнение вашего хэндлера занимает много времени,
рекомендуется выполнять его в отдельном потоке.

Хэндлеры вызываются в том порядке, в котором были добавлены. Так же учитывается порядок самих плагинов.
"""


# Дабы не импортировать лишний раз просто так, импортируем только для тайп-хинтинга.
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cardinal import Cardinal
    from FunPayAPI.runner import MessageEvent, OrderEvent
    from FunPayAPI.orders import Order

import logging


# Создаем логгер.
# Данную строку не нужно менять, т.к. иначе на этот логгер не будет действовать глобальные настройки, что может
# привести к ошибкам.
logger = logging.getLogger(f"Cardinal.{__name__}")

# Далее вы можете использовать этот логгер для вывода и сохранения логов.
# Уровень логов для вывода в консоль - logging.INFO
# Уровень логов для записи в файл - logging.DEBUG
# Цвета для каждого уровня логов уже предустановлены.
# Вы можете использовать другие цвета. Для этого используйте в тексте следующие строки:
# $YELLOW - для желтого цвета
# $MAGENTA - для фиолетового цвета.
# $CYAN - для светло-голубого цвета.
# $BLUE - для синего цвета.
# $color - для возвращения к цвету, привязанного к уровню лога.


# Создаем хэндлеры.
# Названия параметров не имеют значения. Однако порядок - имеет.
# Если вы не используете какие-то параметры, вы можете не указывать их, просто заменив с помощью *args
# Однако, помните про порядок.
def some_handler_1(message_event: MessageEvent, cardinal: Cardinal, *args):
    """
    Выполняется после того, как обнаружено новое сообщение. Не реагирует на сообщения, которые отправил Кардинал.

    :param message_event: экземпляр сообщения.
    :param cardinal: экземпляр Кардинала.
    """
    pass


def some_handler_2(order_event: OrderEvent, cardinal: Cardinal, *args):
    """
    Выполняется после того, как FunPay сообщил об изменениях в ордерах.

    :param order_event: экземпляр данных об изменениях.
    :param cardinal: экземпляр Кардинала.
    """
    pass


def some_handler_3(order: Order, cardinal: Cardinal, *args):
    """
    Выполняется после того, как обнаружен новый ордер.

    :param order: экземпляр ордера.
    :param cardinal: экземпляр Кардинала.
    """
    pass


def some_handler_4(order: Order, text: str, cardinal: Cardinal, errored: bool, *args):
    """
    Выполняется после отправления товара покупателю (вне зависимости от результата)

    :param order: экземпляр ордера.
    :param text: текст отправленного товара / текст ошибки.
    :param cardinal: экземпляр Кардинала.
    :param errored: результат отправления товара. (Если отправка не удалась - errored = True)
    """
    pass


def some_handler_5(game_id: int, category_names: list[str], cardinal: Cardinal, *args):
    """
    Выполняется после поднятия лотов одной игры.

    :param game_id: ID игры, к которой относится категории.
    :param category_names: название категорий, лоты которых были подняты.
    :param cardinal: экземпляр Кардинала.
    """
    pass


def some_handler_6(cardinal: Cardinal, *args):
    """
    Выполняется после инициализации кардинала (в данный момент не работает).

    :param cardinal: экземпляр Кардинала.
    """
    pass


def some_handler_7(cardinal: Cardinal, *args):
    """
    Выполняется после запуска Кардинала.

    :param cardinal: экземпляр Кардинала.
    """
    pass


def some_handler_8(cardinal: Cardinal, *args):
    """
    Выполняется после остановки Кардинала. (в данный момент не работает).

    :param cardinal: экземпляр Кардинала.
    """
    pass


# Регистрируем хэндлеры

# Название переменных ниже ИМЕЕТ ЗНАЧЕНИЕ!
# Проверяйте названия переменных, что бы правильно привязать хэндлер к нужному эвенту!

# В данный список необходимо добавить все хэндлеры, которые должны вызываться после обнаружения нового сообщения.
REGISTER_TO_NEW_MESSAGE_EVENT = [
    some_handler_1
]

# В данный список необходимо добавить все хэндлеры, которые должны вызываться после того как FunPay сообщит об
# изменениях в ордерах.
REGISTER_TO_ORDERS_UPDATE_EVENT = [
    some_handler_2
]

# В данный список необходимо добавить все хэндлеры, которые должны вызываться после обнаружения нового ордера.
REGISTER_TO_NEW_ORDER_EVENT = [
    some_handler_3
]

# В данный список необходимо добавить все хэндлеры, которы должны вызываться после отправления товара покупателю.
# Хэндлеры вызываются вне зависимости от результата отправления.
REGISTER_TO_DELIVERY_EVENT = [
    some_handler_4
]

# В данный список необходимо добавить все хэндлеры, которы должны вызываться после поднятия лотов.
REGISTER_TO_RAISE_EVENT = [
    some_handler_5
]

# В данный список необходимо добавить все хэндлеры, которы должны вызываться после инициализации Кардинала.
# В данный момент не работает.
REGISTER_TO_INIT_EVENT = [
    some_handler_6
]

# В данный список необходимо добавить все хэндлеры, которы должны вызываться после запуска Кардинала.
REGISTER_TO_START_EVENT = [
    some_handler_7
]

# В данный список необходимо добавить все хэндлеры, которы должны вызываться после остановки Кардинала.
# В данный момент не работает.
REGISTER_TO_STOP_EVENT = [
    some_handler_8
]
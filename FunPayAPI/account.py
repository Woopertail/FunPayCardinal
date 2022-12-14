"""
В данном модуле написаны функции и классы, позволяющие получать / изменять данные аккаунта FunPay.
Для всех функций и методов требуется golden_key аккаунта FunPay.
"""


from bs4 import BeautifulSoup
import requests
import json
import time

from typing import TypedDict

from .categories import Category
from .enums import Links, OrderStatuses, CategoryTypes
from .orders import Order
from .other import get_wait_time_from_raise_response, gen_rand_tag


class RaiseCategoriesResponse(TypedDict):
    """
    Type-класс, описывающий структуру словаря, возвращаемого методом Account.raise_game_categories.
    """
    complete: bool
    wait: int
    raised_category_names: list[str]
    response: dict


class Account:
    """
    Класс для работы с аккаунтом FunPay.
    """
    def __init__(self, app_data: dict, id_: int, username: str, balance: float, currency: str | None,
                 active_orders: int, golden_key: str, csrf_token: str, session_id: str, last_update: int):
        """
        :param app_data: словарь с данными из <body data-app-data=>.
        :param id_: id пользователя.
        :param username: имя пользователя.
        :param balance: баланс пользователя.
        :param currency: знак валюты на аккаунте.
        :param active_orders: активные ордеры пользователя.
        :param golden_key: golden_key (токен) аккаунта.
        :param csrf_token: csrf токен.
        :param session_id: PHPSESSID.
        :param last_update: время последнего обновления.
        """
        self.app_data = app_data
        self.id = id_
        self.username = username
        self.balance = balance
        self.currency = currency
        self.active_orders = active_orders
        self.golden_key = golden_key
        self.csrf_token = csrf_token
        self.session_id = session_id
        self.last_update = last_update
        # Сохраненные переписки. Для того, что бы при новом ордере заново не отправлять запрос на получение чатов.
        self.chats_html: str | None = None

    def send_message(self, node_id: int, text: str, timeout: float = 10.0) -> dict:
        """
        Отправляет сообщение в переписку с ID node_id.

        :param node_id: ID переписки.
        :param text: текст сообщения.
        :param timeout: тайм-аут ожидания ответа.
        :return: ответ FunPay.
        """
        if not text.strip():
            raise Exception  # todo: создать и добавить кастомное исключение: пустое сообщение.

        headers = {
            "accept": "*/*",
            "cookie": f"golden_key={self.golden_key}; PHPSESSID={self.session_id}",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest"
        }
        request = {
            "action": "chat_message",
            "data": {
                "node": node_id,
                "last_message": -1,
                "content": text
            }
        }
        payload = {
            "objects": "",
            "request": json.dumps(request),
            "csrf_token": self.csrf_token
        }
        response = requests.post(Links.RUNNER, headers=headers, data=payload, timeout=timeout)
        json_response = response.json()
        return json_response

    def get_node_id_by_username(self, username: str, force_request: bool = False) -> int | None:
        """
        Парсит self.chats_html и ищет node_id чата по username'у.
        Если self.chats_html is None -> делает запрос к FunPay (будет сделано в будущем).

        :param username: никнейм пользователя (искомого чата).
        :param force_request: пропустить ли поиск в self.chats_html и отправить ли сразу запрос к FunPay.
        :return: node_id чата или None, если чат не найден.
        """
        if not force_request and self.chats_html is not None:
            parser = BeautifulSoup(self.chats_html, "lxml")
            user_box = parser.find("div", {"class": "media-user-name"}, text=username)
            if user_box is not None:
                node_id = user_box.parent["data-id"]
                return int(node_id)
        return None

    def get_account_orders(self,
                           include_outstanding: bool = True,
                           include_completed: bool = False,
                           include_refund: bool = False,
                           exclude: list[str] | None = None,
                           timeout: float = 10.0) -> list[Order]:
        """
        Получает список ордеров на аккаунте.

        :param include_outstanding: включить в список оплаченные (но не завершенные) заказы.
        :param include_completed: включить в список завершенные заказы.
        :param include_refund: включить в список заказы, за которые оформлен возврат.
        :param exclude: список ID заказов, которые нужно исключить из итогового списка.
        :param timeout: тайм-аут ожидания ответа.
        :return: Список с ордерами.
        """
        exclude = exclude if exclude else []
        headers = {"cookie": f"golden_key={self.golden_key};"}
        if self.session_id:
            headers["cookie"] += f" PHPSESSID={self.session_id};"

        response = requests.get(Links.ORDERS, headers=headers, timeout=timeout)
        if response.status_code != 200:
            raise Exception  # todo: создать и добавить кастомное исключение: не удалось получить данные с сайта.

        html_response = response.content.decode()
        parser = BeautifulSoup(html_response, "lxml")

        check_user = parser.find("div", {"class": "user-link-name"})
        if check_user is None:
            raise Exception  # todo: создать и добавить кастомное исключение: невалидный токен.

        order_divs = parser.find_all("a", {"class": "tc-item"})
        if order_divs is None:
            return []
        parsed_orders = []

        for div in order_divs:
            order_div_classname = div.get("class")
            if "warning" in order_div_classname:
                if not include_refund:
                    continue
                status = OrderStatuses.REFUND
            elif "info" in order_div_classname:
                if not include_outstanding:
                    continue
                status = OrderStatuses.OUTSTANDING
            else:
                if not include_completed:
                    continue
                status = OrderStatuses.COMPLETED

            order_id = div.find("div", {"class": "tc-order"}).text
            if order_id in exclude:
                continue
            title = div.find("div", {"class": "order-desc"}).find("div").text
            price = float(div.find("div", {"class": "tc-price"}).text.split(" ")[0])

            buyer = div.find("div", {"class": "media-user-name"}).find("span")
            buyer_name = buyer.text
            buyer_id = int(buyer.get("data-href")[:-1].split("https://funpay.com/users/")[1])

            order_object = Order(id_=order_id, title=title, price=price, buyer_username=buyer_name, buyer_id=buyer_id,
                                 status=status)

            parsed_orders.append(order_object)

        return parsed_orders

    def get_category_game_id(self, category: Category, timeout: float = 10.0) -> int:
        """
        Получает ID игры, к которой относится категория.

        :param category: экземпляр класса Category.
        :param timeout: тайм-аут получения ответа.
        :return: ID игры, к которой относится категория.
        """
        if category.type == CategoryTypes.LOT:
            link = f"{Links.BASE_URL}/lots/{category.id}/trade"
        else:
            link = f"{Links.BASE_URL}/chips/{category.id}/trade"

        headers = {"cookie": f"golden_key={self.golden_key}"}
        response = requests.get(link, headers=headers, timeout=timeout)
        if response.status_code == 404:
            raise Exception  # todo: создать и добавить кастомное исключение: категория не найдена.
        if response.status_code != 200:
            raise Exception  # todo: создать и добавить кастомное исключение: не удалось получить данные с сайта.

        html_response = response.content.decode()
        parser = BeautifulSoup(html_response, "lxml")

        check_user = parser.find("div", {"class": "user-link-name"})
        if check_user is None:
            raise Exception  # todo: создать и добавить кастомное исключение: невалидный токен.

        if category.type == CategoryTypes.LOT:
            game_id = int(parser.find("div", {"class": "col-sm-6"}).find("button")["data-game"])
        else:
            game_id = int(parser.find("input", {"name": "game"})["value"])

        return game_id

    def request_lots_raise(self, category: Category, timeout: float = 10.0) -> dict:
        """
        Отправляет запрос на получение modal-формы для поднятия лотов категории category.id.
        !ВНИМЕНИЕ! Для отправки запроса необходимо, чтобы category.game_id != None.
        !ВНИМАНИЕ! Если на аккаунте только 1 категория, относящаяся к игре category.game_id,
        то FunPay поднимет данную категорию в списке без отправления modal-формы с выбором других категорий.

        :param category: экземпляр класса Category.
        :param timeout: тайм-аут получения ответа.
        :return: ответ FunPay.
        """
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "cookie": f"locale=ru; golden_key={self.golden_key}",
            "x-requested-with": "XMLHttpRequest"
        }
        payload = {
            "game_id": category.game_id,
            "node_id": category.id
        }

        response = requests.post(Links.RAISE, headers=headers, data=payload, timeout=timeout)
        if response.status_code != 200:
            raise Exception  # todo: создать и добавить кастомное исключение: не удалось получить данные с сайта.
        response_dict = response.json()
        return response_dict

    def raise_game_categories(self, category: Category, exclude: list[str] | None = None,
                              timeout: float = 10.0) -> RaiseCategoriesResponse:
        """
        Поднимает лоты всех категорий игры category.game_id.
        !ВНИМЕНИЕ! Для поднятия лотов необходимо, чтобы category.game_id != None.

        :param category: экземпляр класса Category.
        :param exclude: список из названий категорий, которые не нужно поднимать.
        :param timeout: тайм-аут ожидания ответа.
        :return: ответ FunPay.
        """
        check = self.request_lots_raise(category, timeout)
        if check.get("error") and check.get("msg") and "Подождите" in check.get("msg"):
            wait_time = get_wait_time_from_raise_response(check.get("msg"))
            return {"complete": False, "wait": wait_time, "raised_category_names": [], "response": check}
        elif check.get("error"):
            # Если вернулся ответ с ошибкой и это не "Подождите n времени" - значит творится какая-то дичь.
            return {"complete": False, "wait": 10, "raised_category_names": [], "response": check}
        elif check.get("error") is not None and not check.get("error"):
            # Если была всего 1 категория и FunPay ее поднял без отправки modal-окна
            return {"complete": True, "wait": 3600, "raised_category_names": [category.title], "response": check}
        elif check.get("modal"):
            # Если же появилась модалка, то парсим все чекбоксы и отправляем запрос на поднятие всех категорий, кроме тех,
            # которые в exclude.
            parser = BeautifulSoup(check.get("modal"), "lxml")
            category_ids = []
            category_names = []
            checkboxes = parser.find_all("div", {"class": "checkbox"})
            for cb in checkboxes:
                category_id = cb.find("input")["value"]
                if (exclude is not None and category_id not in exclude) or exclude is None:
                    category_ids.append(category_id)
                    category_name = cb.find("label").text
                    category_names.append(category_name)

            headers = {
                "accept": "*/*",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "cookie": f"locale=ru; golden_key={self.golden_key}",
                "x-requested-with": "XMLHttpRequest"
            }
            payload = {
                "game_id": category.game_id,
                "node_id": category.id,
                "node_ids[]": category_ids
            }
            response = requests.post(Links.RAISE, headers=headers, data=payload, timeout=timeout).json()
            if not response.get("error"):
                return {"complete": True, "wait": 3600, "raised_category_names": category_names, "response": response}
            else:
                return {"complete": False, "wait": 10, "raised_category_names": [], "response": response}

    def get_lot_info(self, lot_id: int, game_id: int) -> list[dict[str, str]]:
        """
        Получает значения всех полей лота (в окне редактирования лота).

        :param lot_id: ID лота.
        :param game_id: ID игры, к которой относится лот.
        :return: словарь {"название поля": "значение поля"}.
        """
        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "x-requested-with": "XMLHttpRequest",
            "cookie": f"golden_key={self.golden_key}; PHPSESSID={self.session_id}"
        }
        tag = gen_rand_tag()
        payload = {
            "tag": tag,
            "offer": lot_id,
            "node": game_id
        }

        query = f"?tag={tag}&offer={lot_id}&node={game_id}"

        response = requests.get(f"{Links.BASE_URL}/lots/offerEdit{query}", headers=headers, data=payload)
        json_response = response.json()
        parser = BeautifulSoup(json_response["html"], "lxml")

        input_fields = parser.find_all("input")
        text_fields = parser.find_all("textarea")
        selection_fields = parser.find_all("select")
        result = []
        for field in input_fields:
            name = field["name"]
            value = field.get("value")
            if value is None:
                value = ""
            result.append({"name": name, "value": value})

        for field in text_fields:
            name = field["name"]
            text = field.text
            if not text:
                text = ""
            result.append({"name": name, "value": text})

        for field in selection_fields:
            name = field["name"]
            value = field.find("option", selected=True)["value"]
            result.append({"name": name, "value": value})

        return result

    def change_lot_state(self, lot_id: int, game_id: int, state: bool = True) -> dict:
        """
        Изменяет состояние лота (активное / неактивное).

        :param lot_id: ID лота.
        :param game_id: ID игры, к которой относится лот.
        :param state: Целевое состояние лота.
        :return: ответ FunPay.
        """
        lot_info = self.get_lot_info(lot_id, game_id)

        payload = {}
        for field in lot_info:
            if field["name"] == "active":
                if state:
                    field["value"] = "on"
                else:
                    continue
            payload[field["name"]] = field["value"]

        payload["location"] = "trade"

        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "cookie": f"golden_key={self.golden_key}; PHPSESSID={self.session_id}"
        }
        response = requests.post(f"{Links.BASE_URL}/lots/offerSave", headers=headers, data=payload)
        return response.json()


def get_account(token: str, timeout: float = 10.0) -> Account:
    """
    Авторизируется с помощью токена и получает общие данные об аккаунте.

    :param token: golden_key (токен) аккаунта.
    :param timeout: тайм-аут получения ответа.
    :return: экземпляр класса Account.
    """
    headers = {"cookie": f"golden_key={token}"}

    response = requests.get(Links.BASE_URL, headers=headers, timeout=timeout)
    if response.status_code != 200:
        raise Exception  # todo: создать и добавить кастомное исключение: не удалось получить данные с сайта.

    html_response = response.content.decode()
    parser = BeautifulSoup(html_response, "lxml")

    username = parser.find("div", {"class": "user-link-name"})
    if username is None:
        raise Exception  # todo: создать и добавить кастомное исключение: невалидный токен.
    username = username.text

    app_data = json.loads(parser.find("body")["data-app-data"])
    userid = app_data["userId"]
    csrf_token = app_data["csrf-token"]

    active_sales = parser.find("span", {"class": "badge badge-trade"})
    active_sales = int(active_sales.text) if active_sales else 0

    balance = parser.find("span", {"class": "badge badge-balance"})
    balance_count = float(balance.text.split(" ")[0]) if balance else 0
    balance_currency = balance.text.split(" ")[1] if balance else None

    cookies = response.cookies.get_dict()
    session_id = cookies["PHPSESSID"]

    return Account(app_data=app_data, id_=userid, username=username, balance=balance_count, currency=balance_currency,
                   active_orders=active_sales, golden_key=token, csrf_token=csrf_token, session_id=session_id,
                   last_update=int(time.time()))

"""
Стратегії розрахунку вартості проживання.

[GoF Pattern: Strategy / Поведінковий патерн]
Інкапсулює взаємозамінні алгоритми розрахунку підсумкової ціни бронювання:
- Стандартний тариф;
- Знижка на довготривале перебування (сезонна/промоційна);
- Персональна знижка програми лояльності клієнта;
- Тариф вихідного дня (підвищений коефіцієнт).
"""

from abc import ABC, abstractmethod

from app.domain.models.entities import User


class PricingStrategy(ABC):
    """
    Інтерфейс стратегії (Strategy).
    Визначає єдиний метод розрахунку фінальної суми на основі базової вартості,
    тривалості та статусу гостя.
    """

    @abstractmethod
    def calculate_price(self, base_amount: float, nights: int, guest: User) -> float:
        """Розраховує підсумкову вартість згідно з алгоритмом даної стратегії."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Повертає опис застосованого правила ціноутворення."""
        pass


class StandardPricingStrategy(PricingStrategy):
    """
    Конкретна стратегія: Стандартний базовий тариф (коефіцієнт 1.0, без знижок чи націнок).
    """

    def calculate_price(self, base_amount: float, nights: int, guest: User) -> float:
        return round(base_amount, 2)

    def get_description(self) -> str:
        return "Стандартний тариф (без додаткових знижок та націнок)"


class LongStayDiscountStrategy(PricingStrategy):
    """
    Конкретна стратегія: Знижка на тривале перебування.
    - від 7 діб: знижка 15%
    - від 4 до 6 діб: знижка 10%
    - менше 4 діб: без знижки
    """

    def calculate_price(self, base_amount: float, nights: int, guest: User) -> float:
        if nights >= 7:
            discount = 0.15
        elif nights >= 4:
            discount = 0.10
        else:
            discount = 0.0

        final_price = base_amount * (1.0 - discount)
        return round(final_price, 2)

    def get_description(self) -> str:
        return "Тариф тривалого перебування (10% від 4 діб, 15% від 7 діб)"


class LoyaltyPricingStrategy(PricingStrategy):
    """
    Конкретна стратегія: Персональний тариф програми лояльності.
    Застосовує відсоток знижки згідно з рівнем клієнта (Silver 5%, Gold 10%, Platinum 15%).
    """

    def calculate_price(self, base_amount: float, nights: int, guest: User) -> float:
        discount_rate = guest.get_discount_rate() if guest else 0.0
        final_price = base_amount * (1.0 - discount_rate)
        return round(final_price, 2)

    def get_description(self) -> str:
        return "Програма лояльності (персональна знижка за рівнем картки клієнта)"


class WeekendSurchargeStrategy(PricingStrategy):
    """
    Конкретна стратегія: Тариф вихідного дня (сезонний попит, +15% надбавка).
    """

    def __init__(self, surcharge_rate: float = 0.15):
        self.surcharge_rate = surcharge_rate

    def calculate_price(self, base_amount: float, nights: int, guest: User) -> float:
        final_price = base_amount * (1.0 + self.surcharge_rate)
        return round(final_price, 2)

    def get_description(self) -> str:
        return f"Тариф підвищеного попиту / вихідного дня (+{int(self.surcharge_rate * 100)}%)"


class PricingCalculatorContext:
    """
    Контекст (Context) у патерні Strategy.
    Зберігає посилання на поточну стратегію та надає клієнтам можливість змінювати її під час виконання.
    """

    def __init__(self, strategy: PricingStrategy = StandardPricingStrategy()):
        self._strategy = strategy

    @property
    def strategy(self) -> PricingStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, strategy: PricingStrategy) -> None:
        """Динамічна зміна стратегії ціноутворення."""
        self._strategy = strategy

    def calculate(self, base_amount: float, nights: int, guest: User) -> float:
        """Делегує виконання розрахунку активній стратегії."""
        return self._strategy.calculate_price(base_amount, nights, guest)

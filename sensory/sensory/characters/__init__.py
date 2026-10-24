from .apple import Apple
from .banana import Banana
from .berry import Berry
from .blueberry import Blueberry
from .broccoli import Broccoli
from .carrot import Carrot
from .corn import Corn
from .lemon import Lemon
from .orange import Orange
from .pear import Pear
from .plum import Plum
from .pumpkin import Pumpkin
from .tomato import Tomato

CHARACTERS = {
    # Fruits
    "berry": Berry, "pear": Pear, "plum": Plum, "orange": Orange, "banana": Banana,
    "lemon": Lemon, "apple": Apple, "blueberry": Blueberry,
    # Veggies
    "carrot": Carrot, "tomato": Tomato, "corn": Corn, "broccoli": Broccoli, "pumpkin": Pumpkin,
}
FAMILIES = {
    "fruits":  ["berry", "pear", "plum", "orange", "banana", "lemon", "apple", "blueberry"],
    "veggies": ["carrot", "tomato", "corn", "broccoli", "pumpkin"],
    "all":     list(CHARACTERS),
}

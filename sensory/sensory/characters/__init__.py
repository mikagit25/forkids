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
from .png_character import (
    Bear, Cat, Dog, Elephant, Fox, Frog, Koala, Lion, Monkey,
    Owl, Panda, Penguin, Rabbit, Tiger,
    Octopus, Butterfly, BlueWhale,
)

CHARACTERS = {
    # Fruits
    "berry": Berry, "pear": Pear, "plum": Plum, "orange": Orange, "banana": Banana,
    "lemon": Lemon, "apple": Apple, "blueberry": Blueberry,
    # Veggies
    "carrot": Carrot, "tomato": Tomato, "corn": Corn, "broccoli": Broccoli, "pumpkin": Pumpkin,
    # Animals
    "bear": Bear, "cat": Cat, "dog": Dog, "elephant": Elephant, "fox": Fox,
    "frog": Frog, "koala": Koala, "lion": Lion, "monkey": Monkey,
    "owl": Owl, "panda": Panda, "penguin": Penguin, "rabbit": Rabbit, "tiger": Tiger,
    # Ocean
    "octopus": Octopus, "butterfly": Butterfly, "blue_whale": BlueWhale,
}
FAMILIES = {
    "fruits":  ["berry", "pear", "plum", "orange", "banana", "lemon", "apple", "blueberry"],
    "veggies": ["carrot", "tomato", "corn", "broccoli", "pumpkin"],
    "animals": ["bear", "cat", "dog", "elephant", "fox", "frog", "koala", "lion",
                "monkey", "owl", "panda", "penguin", "rabbit", "tiger"],
    "ocean":   ["octopus", "butterfly", "blue_whale"],
    "all":     list(CHARACTERS),
}

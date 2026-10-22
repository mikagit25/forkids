from .apple import Apple
from .banana import Banana
from .berry import Berry
from .blueberry import Blueberry
from .lemon import Lemon
from .orange import Orange
from .pear import Pear
from .plum import Plum

CHARACTERS = {"berry": Berry, "pear": Pear, "plum": Plum, "orange": Orange, "banana": Banana,
              "lemon": Lemon, "apple": Apple, "blueberry": Blueberry}
FAMILIES = {"fruits": list(CHARACTERS)}

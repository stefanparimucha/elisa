import numpy as np

from elisa.conf import config
from elisa import (
    logger,
)
from elisa.base.container import (
    StarContainer,
    PositionContainer
)
from elisa.single_system.surface import (
    mesh,
)

config.set_up_logging()
__logger__ = logger.getLogger("single-system-container-module")


class SystemContainer(PositionContainer):
    def __init__(self, star: StarContainer, **properties):
        self.star = star

        # placeholder (set in loop below)
        self.inclination = np.nan

        for key, val in properties.items():
            setattr(self, key, val)

    def build(self, *args, **kwargs):
        pass

    def build_mesh(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        return mesh.build_mesh()

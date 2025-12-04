from abc import ABC, abstractmethod
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class Rule(ABC):  # TODO: structure order of execution of layers, to avoid conflicts
    @abstractmethod
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:  # pragma: no cover
        pass  # pragma: no cover

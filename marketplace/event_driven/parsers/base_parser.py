from abc import ABC, abstractmethod, abstractstaticmethod


class BaseParser(ABC):
    @abstractstaticmethod
    def parse(stream, encoding=None):
        pass

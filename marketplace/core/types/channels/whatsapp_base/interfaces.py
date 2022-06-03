import abc


class ProfileHandlerInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_profile(self):
        pass

    @abc.abstractmethod
    def set_profile(self):
        pass

    @abc.abstractmethod
    def delete_profile(self):
        pass


class BusinessProfileHandlerInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_profile(self):
        pass

    @abc.abstractmethod
    def set_profile(self):
        pass

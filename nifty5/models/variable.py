import nifty5 as ift

from .model import Model


class Variable(Model):
    """
    Returns the MultiField.
    """
    def __init__(self, position):
        super(Variable, self).__init__(position)

        self._value = position
        self._gradient = ift.ScalingOperator(1., position.domain)

    def at(self, position):
        return self.__class__(position)
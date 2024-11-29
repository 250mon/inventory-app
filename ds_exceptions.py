

class BaseInvalidIdError(IndexError):
    pass


class NonExistentItemIdError(BaseInvalidIdError):
    pass


class NonExistentSkuIdError(BaseInvalidIdError):
    pass


class InactiveItemIdError(BaseInvalidIdError):
    pass


class InactiveSkuIdError(BaseInvalidIdError):
    pass


class BaseValueError(ValueError):
    pass


class InvalidTrTypeError(BaseValueError):
    pass

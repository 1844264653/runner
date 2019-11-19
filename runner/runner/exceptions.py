

class RemoteServersNotFoundError(Exception):
    pass


class NoneRemoteServerAllocated(Exception):
    pass


class MoreThanOneRemoteServerAllocated(Exception):
    pass


class ReleaseRemoteServerException(Exception):
    pass


class BrowserTypeNotSpecifiedException(Exception):
    pass


class BrowserConcurrencyNotSpecifiedException(Exception):
    pass


class BrowserTypeNotSupportedException(Exception):
    pass


class BrowserConcurrencyNotSupportedException(Exception):
    pass

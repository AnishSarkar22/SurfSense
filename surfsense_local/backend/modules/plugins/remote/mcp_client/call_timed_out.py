"""A call reached its caller's deadline; the server was told to stop."""


class CallTimedOutError(Exception):
    pass

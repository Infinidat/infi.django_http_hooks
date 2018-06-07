class InvalidPayloadError(Exception):
    '''raised when Hook's payload is not a valid json or cannot be imported'''
    pass


class InvalidHeadersError(Exception):
    '''raised when Hook's headers are not a valid json'''
    pass


class InvalidSignalError(Exception):
    '''raised when trying to create a signal which already exists'''
    pass


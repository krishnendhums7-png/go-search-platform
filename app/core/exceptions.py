"""
Custom application exceptions.
"""


class GOSearchException(Exception):
    """
    Base application exception.
    """


class AuthenticationException(GOSearchException):
    """
    Raised when authentication fails.
    """


class AuthorizationException(GOSearchException):
    """
    Raised when authorization fails.
    """

class InvalidTokenException(GOSearchException):
    """
    Raised when a JWT token is invalid.
    """


class ExpiredTokenException(GOSearchException):
    """
    Raised when a JWT token has expired.
    """

class UserNotFoundException(GOSearchException):
    """
    User does not exist.
    """


class InvalidCredentialsException(GOSearchException):
    """
    Invalid username or password.
    """
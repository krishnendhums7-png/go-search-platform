"""
Role definitions for the application.
"""

from enum import Enum


class Role(str, Enum):
    """
    Supported user roles.
    """

    ADMIN = "ADMIN"
    CITIZEN = "CITIZEN"
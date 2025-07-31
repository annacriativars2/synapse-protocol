from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models here to avoid circular imports
from .user import User
from .delivery import Delivery
from .chat import Chat

__all__ = ["db", "User", "Delivery", "Chat"]


"""
Модели базы данных для marketplace-сvc
"""

from .core import User, Profile, Wallet, Listing, Transaction, ListingStatus, TransactionStatus
from .categorization import (
    Game, ItemCategory, CategoryAttribute, ItemTemplate, Item, ItemAttributeValue, AttributeType
) 
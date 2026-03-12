from app.db import Base  # pour que Base.registry soit partagé

from .people_public import PeoplePublic
from .conversation import Conversation
from .conversationMember import ConversationMember
from .message import Message
from .messageAttachment import MessageAttachment
from .messageReaction import MessageReaction
from .conversationLang import ConversationLang

__all__ = [
    "PeoplePublic",
    "Conversation",
    "ConversationMember",
    "ConversationLang",
    "Message",
    "MessageAttachment",
    "MessageReaction",
]

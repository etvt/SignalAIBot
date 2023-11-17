import os
from enum import Enum, StrEnum
from typing import Any, Dict, Set

from pydantic import ValidationError, field_serializer, field_validator, Field, BaseModel

from signalaibot.settings import constants


class NiceStrEnum(StrEnum):
    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


class Env(Enum):
    PROD = 'PROD'
    DEV = 'DEV'
    DEFAULT = PROD

    @staticmethod
    def from_string(value: str) -> 'Env':
        return Env[value]

    @staticmethod
    def from_os_environ() -> 'Env':
        given = os.environ.get(constants.ENV_KEY, None)
        return Env.from_string(given) if given else Env.DEFAULT


class Config(BaseModel, frozen=True):
    bot_number: str
    admin_number: str

    openai_api_key: str

    @staticmethod
    def from_env_dict(source_env_dict: dict[str, Any]) -> 'Config':
        lower_case_dict = {key.lower(): value for key, value in source_env_dict.items()}
        try:
            res = Config(**lower_case_dict)
        except ValidationError as ve:
            # extracting only some error details to hide potentially sensitive input
            raise ValueError(str(ve.errors(include_url=False, include_context=False, include_input=False))) from None
        # noinspection PyTypeChecker
        return res


class ConversationType(NiceStrEnum):
    PRIVATE = 'PRIVATE'
    GROUP = 'GROUP'


class Conversation(BaseModel, frozen=True):
    type: ConversationType
    id: str


class ConversationMeta(BaseModel, frozen=True):
    request_id: int


class State(BaseModel):
    bot_uuid: str = None
    admin_uuid: str = None

    requested_conversations: Dict[Conversation, ConversationMeta] = Field(default_factory=dict)
    request_id_next_value: int = 0

    rejected_conversations: Set[Conversation] = Field(default_factory=set)
    authorized_conversations: Set[Conversation] = Field(default_factory=set)

    def to_json_dict(self):
        return self.model_dump(mode='json')

    @field_serializer('requested_conversations', mode='plain')
    def serialize_req(self, requested_conversations: Dict[Conversation, ConversationMeta], _info):
        return [dict(conversation=conv, meta=meta) for conv, meta in requested_conversations.items()]

    @field_validator('requested_conversations', mode='before')
    @classmethod
    def deserialize_req(cls, data: Any) -> Any:
        if not isinstance(data, list):
            return data
        return {Conversation(**item['conversation']): item['meta'] for item in data}


class Role(Enum):
    def __init__(self, value, access_level):
        self._value_ = value
        self.access_level = access_level

    ADMIN = ('ADMIN', 9)
    USER = ('USER', 5)
    NONE = ('NONE', 0)
    REJECTED = ('REJECTED', -9)


class RequestContext(BaseModel):
    sender: str
    conversation: Conversation
    sender_role_in_conversation: Role = Role.NONE

from signalaibot.settings.model import State, Conversation, ConversationType, ConversationMeta


def test_json_io():
    original = State(
        bot_uuid='bot-uuid',
        admin_uuid='admin-uuid',
        requested_conversations={
            Conversation(type=ConversationType.GROUP, id='IEOikf3229fjlfwkewf312-=r'):
                ConversationMeta(request_id=123)
        })

    js = original.model_dump(mode='json')
    parsed = State.model_validate(js)
    assert original == parsed

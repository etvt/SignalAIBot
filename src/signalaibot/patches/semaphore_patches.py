from semaphore import Bot, Profile


async def get_profile_from_number(self: Bot, user_number: str) -> Profile:
    return await self._sender._send({
        "type": "get_profile",
        "version": "v1",
        "account": self._sender._username,
        "address": {"number": user_number}
    })


def apply():
    Bot.get_profile_from_number = get_profile_from_number

import json
from typing import Dict, Callable, TypeVar

from semaphore import Bot, Socket, MessageSender, Address, GroupV2
from semaphore.exceptions import UnknownError, IDENTIFIABLE_SIGNALD_ERRORS


class ExtendedBot(Bot):

    async def __aenter__(self) -> 'ExtendedBot':
        """Connect to the bot's internal socket."""
        self._send_socket = await Socket(self._username,
                                         self._socket_path,
                                         False).__aenter__()
        self._sender = ExtendedMessageSender(self._username, self._send_socket, self._raise_errors)
        return self

    async def get_address_from_number(self: Bot, user_number: str) -> Address:
        return await self._sender._generic_send({
            "type": "resolve_address",
            "version": "v1",
            "account": self._sender._username,
            "partial": {"number": user_number}
        }, lambda d: Address(uuid=d.get('uuid', None), number=d.get('number', None)))

    async def get_group(self: Bot, group_id: str) -> GroupV2:
        return await self._sender._generic_send({
            "type": "get_group",
            "version": "v1",
            "account": self._sender._username,
            "groupID": group_id
        }, GroupV2.create_from_receive_dict)


T = TypeVar('T')


class ExtendedMessageSender(MessageSender):

    async def _generic_send(self, message: Dict, mapper: Callable[[dict], T]) -> T:
        self.signald_message_id += 1
        message['id'] = str(self.signald_message_id)

        async with self._socket_lock:
            await self._socket.send(message)

            async for line in self._socket.read():
                self.log.debug(f"Socket of sender received: {line.decode()}")

                # Load Signal message wrapper.
                try:
                    response_wrapper = json.loads(line)
                except json.JSONDecodeError as e:
                    self.log.error("Could not decode signald response", exc_info=e)
                    continue

                # Skip everything but response for our message.
                if 'id' not in response_wrapper:
                    continue

                if response_wrapper['id'] != message['id']:
                    self.log.warning("Received message response for another id")
                    continue

                if response_wrapper.get("error") is not None:
                    self.log.warning(f"Could not send message:"
                                     f"{response_wrapper}")

                    if not self._raise_signald_errors:
                        return None

                    # Match error.
                    for error_class in IDENTIFIABLE_SIGNALD_ERRORS:
                        if error_class.IDENTIFIER == response_wrapper.get("error_type"):
                            error_dict = response_wrapper.get("error")
                            if not error_dict:
                                break

                            error = error_class()
                            for k in error_dict.keys():
                                setattr(error, k, error_dict.get(k))

                            raise error

                    raise UnknownError(response_wrapper.get("error_type"),
                                       response_wrapper.get("error"))

                response = response_wrapper.get('data', {})
                return mapper(response) if mapper else response

            return None

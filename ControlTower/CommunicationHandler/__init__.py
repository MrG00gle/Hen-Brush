if __name__ == "__main__":
    from ControlTower.CommunicationHandler import payload
    from ControlTower.CommunicationHandler import test
    from ControlTower.CommunicationHandler.CommunicationHandler import CommunicationHandler
    from ControlTower.CommunicationHandler.CommunicationProtocol import CommunicationProtocol
    from ControlTower.CommunicationHandler.PacketType import PacketType
else:
    import payload
    import test
    from .CommunicationHandler import CommunicationHandler
    from .CommunicationProtocol import CommunicationProtocol
    from .PacketType import PacketType

__all__ = [
    "payload",
    "test",
    "CommunicationHandler",
    "CommunicationProtocol",
    "PacketType"
]
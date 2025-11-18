
if __name__ == "__main__":
    from ControlTower.CommunicationHandler.test.test_PointPayload import TestPointPayload
    from ControlTower.CommunicationHandler.test.test_TelemetryPayload import TestTelemetryPayload
    from ControlTower.CommunicationHandler.test.test_CommandPayload import TestCommandPayload
    from ControlTower.CommunicationHandler.test.test_CommunicationHandler import TestCommunicationHandler
else:
    from .test_PointPayload import TestPointPayload
    from .test_TelemetryPayload import TestTelemetryPayload
    from .test_CommandPayload import TestCommandPayload
    from .test_CommunicationHandler import TestCommunicationHandler

__all__ = [
    "TestPointPayload",
    "TestTelemetryPayload",
    "TestCommandPayload",
    "TestCommunicationHandler"
]
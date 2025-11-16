
if __name__ == "__main__":
    from ControlTower.CommunicationHandler.payload.PointPayload import PointPayload
    from ControlTower.CommunicationHandler.payload.CommandPayload import CommandPayload
    from ControlTower.CommunicationHandler.payload.TelemetryPayload import TelemetryPayload
else:
    from .PointPayload import PointPayload
    from .CommandPayload import CommandPayload
    from .TelemetryPayload import TelemetryPayload
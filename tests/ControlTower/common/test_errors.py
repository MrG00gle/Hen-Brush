import pytest

from ControlTower.common import ConfigFileKeyError, DroneFileNameReadError, SerialConfigLoadFailed, SerialError

ERRORS = [DroneFileNameReadError, ConfigFileKeyError, SerialConfigLoadFailed, SerialError]


@pytest.mark.parametrize("error", ERRORS)
class TestErrors:

    def test_keeps_message(self, error):
        raised = error("something broke")

        assert raised.message == "something broke"
        assert str(raised) == "something broke"
        assert raised.args == ("something broke",)

    def test_is_an_exception(self, error):
        assert issubclass(error, Exception)

    def test_can_be_raised_and_caught(self, error):
        with pytest.raises(error, match="boom"):
            raise error("boom")

    def test_has_a_docstring(self, error):
        assert error.__doc__ and error.__doc__.strip()


def test_errors_are_distinct_types():
    assert len(set(ERRORS)) == 4
    assert not issubclass(SerialError, SerialConfigLoadFailed)

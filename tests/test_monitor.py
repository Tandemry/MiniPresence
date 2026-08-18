from minipresence.monitor import PresenceMonitor, presence_update_due


def test_presence_is_updated_initially_and_then_on_heartbeat():
    assert presence_update_due(False, last_update=100, now=101)
    assert not presence_update_due(True, last_update=100, now=114.9)
    assert presence_update_due(True, last_update=100, now=115)


def test_repeated_status_messages_are_deduplicated():
    events: list[tuple[str, str]] = []
    monitor = PresenceMonitor(lambda status, message: events.append((status, message)))
    monitor._emit("watching", "Waiting for Example")
    monitor._emit("watching", "Waiting for Example")
    monitor._emit("active", "Presence active for Example")
    assert events == [
        ("watching", "Waiting for Example"),
        ("active", "Presence active for Example"),
    ]

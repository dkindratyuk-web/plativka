"""Черга «Грати наступним»."""
from plativka.core import PlayerExtras


class Host(PlayerExtras):
    def __init__(self, pl, cur=0):
        self.playlist, self.current, self.history = list(pl), cur, []


def test_queue_order_and_consume():
    h = Host(["a", "b", "c", "d"], 0)
    assert h.queue_index() is None
    h.queue_play_next(["d"])
    h.queue_play_next(["c"])                 # «грати наступним» стає першим
    assert h.queue == ["c", "d"] and h.queue_pos("d") == 2
    assert h.playlist[h.queue_index()] == "c"
    h.queue_consume("c")
    assert h.playlist[h.queue_index()] == "d"


def test_missing_tracks_go_right_after_current():
    h = Host(["a", "b", "c"], 1)
    h.history = [0, 2]
    h.queue_play_next(["x", "y"])
    assert h.playlist == ["a", "b", "x", "y", "c"]
    assert h.history == [0, 4]               # індекси після вставки зсунулися
    assert h.queue_index() == 2


def test_removed_track_drops_out():
    h = Host(["a", "b"], 0)
    h.queue_play_next(["b"])
    h.playlist = ["a"]
    assert h.queue_index() is None and h.queue == []
    assert h.queue_clear() == 0

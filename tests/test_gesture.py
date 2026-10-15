import os
import queue
import threading

import pytest

from src.config import Config
from src.gesture.link import GestureLink


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class FakeProcess:
    def __init__(self, target, args, daemon):
        self.target, self.args, self.daemon = target, args, daemon
        self.started = self.terminated = False
        self.exitcode = None
        self.alive = False

    def start(self):
        self.started = self.alive = True

    def is_alive(self):
        return self.alive

    def join(self, timeout=None):
        pass

    def terminate(self):
        self.terminated, self.alive = True, False


class FakeContext:
    """Stands in for multiprocessing.get_context("spawn") without a real process."""

    def __init__(self):
        self.processes = []

    def Queue(self):
        return queue.Queue()

    def Event(self):
        return threading.Event()

    def Process(self, target, args, daemon):
        p = FakeProcess(target, args, daemon)
        self.processes.append(p)
        return p


def make_link():
    ctx, clock = FakeContext(), FakeClock()
    link = GestureLink(Config(), ctx=ctx, clock=clock)
    link.start()
    _, out, stop = ctx.processes[-1].args
    return link, ctx, clock, out, stop


def test_starts_worker_and_reports_progress():
    link, ctx, clock, out, _ = make_link()
    assert ctx.processes[0].started and ctx.processes[0].daemon
    assert link.status == "starting" and not link.connected
    out.put(("status", "loading_model", "starting tensorflow"))
    link.poll()
    assert (link.status, link.detail) == ("loading_model", "starting tensorflow")
    assert link.direction() == 0


def test_ready_with_fresh_labels_steers():
    link, _, clock, out, _ = make_link()
    out.put(("status", "ready", ""))
    out.put(("label", "l", 0.97))
    link.poll()
    assert link.connected and link.direction() == -1 and link.letter == "L"
    out.put(("label", "r", 0.9))
    out.put(("label", "n", 0.9))  # newest wins
    link.poll()
    assert link.direction() == 0 and link.letter == "N"


def test_stale_labels_stop_the_ship():
    link, _, clock, out, _ = make_link()
    out.put(("status", "ready", ""))
    out.put(("label", "r", 0.99))
    link.poll()
    assert link.direction() == 1
    clock.t += GestureLink.STALE_AFTER + 0.01
    link.poll()
    assert not link.connected and link.direction() == 0


def test_worker_error_is_reported():
    link, _, _, out, _ = make_link()
    out.put(("status", "error", "camera 0 could not be opened"))
    link.poll()
    assert link.status == "error" and "camera" in link.detail
    assert not link.connected


def test_worker_dying_silently_becomes_an_error():
    link, ctx, _, out, _ = make_link()
    out.put(("status", "ready", ""))
    link.poll()
    ctx.processes[0].alive = False
    ctx.processes[0].exitcode = -11
    link.poll()
    assert link.status == "error" and "-11" in link.detail


def test_retry_restarts_the_worker():
    link, ctx, _, out, stop = make_link()
    out.put(("status", "error", "boom"))
    link.poll()
    link.retry()
    assert stop.is_set()  # old worker told to stop
    assert len(ctx.processes) == 2 and ctx.processes[1].started
    assert link.status == "starting"


def test_stop_terminates_a_stuck_worker():
    link, ctx, _, _, stop = make_link()
    link.stop()
    assert stop.is_set() and ctx.processes[0].terminated
    assert link.status == "stopped"


# ------------------------------------------------------------- the worker
def test_worker_reports_missing_model(tmp_path):
    """Real spawned process: a missing export must come back as an error, fast."""
    link = GestureLink(Config(model_dir=str(tmp_path / "missing")))
    link.start()
    try:
        import time
        deadline = time.monotonic() + 30
        while link.status != "error" and time.monotonic() < deadline:
            link.poll()
            time.sleep(0.05)
        assert link.status == "error"
        assert "keras_model.h5" in link.detail
    finally:
        link.stop()


def test_worker_rejects_bad_labels(tmp_path):
    from src.gesture.worker import WorkerError, read_labels
    (tmp_path / "keras_model.h5").write_bytes(b"")
    (tmp_path / "labels.txt").write_text("0 Up\n1 Down\n")
    with pytest.raises(WorkerError, match="L, R and N"):
        read_labels(str(tmp_path))
    (tmp_path / "labels.txt").write_text("0 L\n1 R\n2 N\n")
    assert read_labels(str(tmp_path)) == ["l", "r", "n"]


def test_preprocess_matches_teachable_machine():
    np = pytest.importorskip("numpy")
    pytest.importorskip("cv2")
    from src.gesture.worker import preprocess
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:, :320] = (255, 0, 0)  # BGR blue on the left half
    x = preprocess(frame, mirror=False, crop="center")
    assert x.shape == (1, 224, 224, 3) and x.dtype == np.float32
    assert x.min() >= -1 and x.max() <= 1
    assert x[0, 112, 5, 2] == pytest.approx(1.0)   # RGB: blue channel last, left side
    assert x[0, 112, 5, 0] == pytest.approx(-1.0)
    mirrored = preprocess(frame, mirror=True, crop="center")
    assert mirrored[0, 112, 5, 2] == pytest.approx(-1.0)  # left half is now black
    squashed = preprocess(frame, mirror=False, crop="squash")
    assert squashed.shape == (1, 224, 224, 3)


MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "keras-model")


@pytest.mark.skipif(not os.path.exists(os.path.join(MODEL_DIR, "keras_model.h5")),
                    reason="no Teachable Machine export in models/keras-model")
def test_real_model_loads_and_predicts():
    np = pytest.importorskip("numpy")
    pytest.importorskip("tensorflow")
    from src.gesture.worker import load_model, read_labels
    labels = read_labels(MODEL_DIR)
    model = load_model(os.path.join(MODEL_DIR, "keras_model.h5"))
    probs = np.asarray(model(np.zeros((1, 224, 224, 3), np.float32), training=False))[0]
    assert len(probs) == len(labels)
    assert probs.sum() == pytest.approx(1.0, abs=1e-3)

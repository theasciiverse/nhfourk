"""Recorder for NetHack Fourk's catalog preview (hub/RECORDING.md), after
NetBSD games' (theasciiverse/netbsd-games, asciiverse/record/rec.py).

The driver beside this file, asciiverse/record/nhfourk.py, plays the game:
it starts a Rec, which runs nhfourk under `asciinema rec` in a 100x30
pseudo-terminal, reads the screen through pyte and sends keys. The cast
goes to asciiverse/casts/nhfourk.cast. Usage, from the repo root after
asciiverse/build.sh (which puts the binary and its data in out/), with
pyte installed:

    python3 asciiverse/record/nhfourk.py

The game runs by name from out/ on PATH, so the cast's header holds no
local path; it finds its data beside the binary. Saves and scores go to a
throwaway home folder under the name "player".

Two environment variables serve testing rather than the preview:
NHF_DIR runs the nhfourk in another folder (an AddressSanitizer build,
say), and NHF_CAST=0 plays without asciinema, so nothing is recorded.
"""
import fcntl, os, pty, select, shutil, struct, sys, tempfile, termios, time

import pyte

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ENTER, ESC = b"\r", b"\x1b"


class Rec:
    def __init__(self, id, title, args=(), cols=100, rows=30):
        self.home = tempfile.mkdtemp(prefix="nhfourk-rec-")
        bindir = os.environ.get("NHF_DIR") or os.path.join(ROOT, "out")
        record = os.environ.get("NHF_CAST", "1") != "0"
        env = {
            "PATH": f"{bindir}:{os.environ['PATH']}",
            "HOME": self.home,
            "USER": "player",
            "LOGNAME": "player",
            "XDG_DATA_HOME": os.path.join(self.home, "data"),
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            "LANG": "C.UTF-8",
        }
        for k in ("ASAN_OPTIONS", "UBSAN_OPTIONS"):
            if k in os.environ:
                env[k] = os.environ[k]
        cmd = " ".join([id, *args])
        self.cast = os.path.join(ROOT, "asciiverse", "casts", f"{id}.cast")
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.ByteStream(self.screen)
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(self.home)
            if record:
                os.execvpe("asciinema", ["asciinema", "rec", "--overwrite", "-q",
                    "--idle-time-limit", "2", "--window-size", f"{cols}x{rows}",
                    "--capture-env", "TERM,COLORTERM,LANG", "--title", title,
                    "--command", cmd, self.cast], env)
            os.execvpe(id, [id, *args], env)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        # Answer the terminal's queries as a real terminal would: libuncursed
        # asks where the cursor is after printing two UTF-8 characters
        # (ESC [ 6n) to learn whether the terminal speaks UTF-8, and with no
        # answer falls back to IBM code page 437 after two seconds.
        self.screen.write_process_input = lambda data: os.write(self.fd, data.encode())
        self.start = time.time()
        self.record = record

    def pump(self, t):
        """Read the game's output for t seconds, keeping the screen current.
        False once the game has gone."""
        end = time.time() + t
        while True:
            left = end - time.time()
            r, _, _ = select.select([self.fd], [], [], max(0.0, min(0.02, left)))
            if r:
                try:
                    self.stream.feed(os.read(self.fd, 65536))
                except OSError:
                    return False
            if left <= 0:
                return True

    def key(self, k, wait=0.15):
        if isinstance(k, str):
            k = k.encode()
        os.write(self.fd, k)
        return self.pump(wait)

    def rows(self):
        return self.screen.display

    def text(self):
        return "\n".join(self.screen.display)

    def wait_for(self, s, timeout=5.0):
        end = time.time() + timeout
        while time.time() < end:
            if s in self.text():
                return True
            self.pump(0.05)
        return False

    def elapsed(self):
        return time.time() - self.start

    def finish(self, quit_keys=b"", grace=5.0):
        """Quit the game so the cast ends with the terminal restored."""
        if quit_keys:
            self.key(quit_keys, 0.5)
        end = time.time() + grace
        while time.time() < end:
            if not self.pump(0.1):
                break
            done, _ = os.waitpid(self.pid, os.WNOHANG)
            if done:
                break
        else:
            print("game did not exit; stopping it", file=sys.stderr)
            os.kill(self.pid, 15)
        try:
            os.waitpid(self.pid, 0)
        except ChildProcessError:
            pass
        shutil.rmtree(self.home, ignore_errors=True)
        if self.record:
            print(f"{self.cast}: {os.path.getsize(self.cast) // 1024} KB, {self.elapsed():.0f} s",
                  file=sys.stderr)

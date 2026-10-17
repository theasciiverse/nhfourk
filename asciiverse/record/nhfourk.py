"""Records NetHack Fourk's catalog preview (hub/RECORDING.md): Ada, a
human Barbarian, sets out, explores with the game's own autoexplore (v),
fights whatever comes next to her, travels to the down staircase when a
level has nothing more to explore and goes down, then saves and quits.
Usage, from the repo root after asciiverse/build.sh, with pyte installed:

    python3 asciiverse/record/nhfourk.py [seconds of play, default 44]

The screen at 100x30: messages at the top, the 80-column map below them,
the status lines at the bottom and the inventory sidebar on the right.
Pets are drawn on a blue background, so a letter next to Ada on the
default background is taken for a foe.
"""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rec import Rec, ENTER, ESC  # noqa: E402

PLAY = float(sys.argv[1]) if len(sys.argv) > 1 else 44.0
MAP_COLS = 79           # the sidebar's border is column 79
MAP_TOP, MAP_BOTTOM = 3, 27

LEVEL_TIME = 14.0       # seconds on a level before heading for known stairs
NOWHERE = "Nowhere else around here can be automatically explored"

DIRS = {(-1, 0): "h", (1, 0): "l", (0, -1): "k", (0, 1): "j",
        (-1, -1): "y", (1, -1): "u", (-1, 1): "b", (1, 1): "n"}


def find_me(r):
    buf = r.screen.buffer
    for y in range(MAP_TOP, MAP_BOTTOM):
        for x in range(MAP_COLS):
            if buf[y][x].data == "@":
                return x, y
    return None


def foe_next_to(r, me, spared):
    """Direction of a monster next to Ada that is not her pet, or None."""
    buf = r.screen.buffer
    for (dx, dy), d in DIRS.items():
        x, y = me[0] + dx, me[1] + dy
        if not (0 <= x < MAP_COLS and MAP_TOP <= y < MAP_BOTTOM):
            continue
        c = buf[y][x]
        if (c.data.isalpha() or c.data in "&;:'") and c.bg != "blue" and (x, y) not in spared:
            return d
    return None


def hp(r):
    for line in r.rows()[-3:]:
        if line.startswith("HP:["):
            try:
                cur, mx = line[4:line.index("]")].split("/")
                return int(cur), int(mx)
            except ValueError:
                pass
    return None


def level(r):
    """The dungeon level from the status line, as its text (Dungeons:3)."""
    for line in r.rows()[-3:]:
        for word in line.split():
            if word.startswith("Dungeons:") or word.startswith("Dlvl:"):
                return word
    return None


def stairs_known(r):
    """A > on the map, not in a message such as <In what direction?: east>."""
    return any(">" in line[:MAP_COLS] and "?" not in line
               for line in r.rows()[MAP_TOP:MAP_BOTTOM])


def messages(r):
    return "\n".join(line[:MAP_COLS] for line in r.rows()[:MAP_TOP + 4])


def main():
    r = Rec("nhfourk", "NetHack Fourk")
    if not r.wait_for("new game", 10):
        sys.exit("no main menu:\n" + r.text())
    r.pump(1.5)
    r.key("n", 0.6)
    r.wait_for("Shall I pick")
    r.key("n", 0.6)
    r.wait_for("Pick a role")
    r.pump(0.6)
    r.key("b", 0.5)
    r.wait_for("gender")
    r.key("f", 0.5)
    r.wait_for("alignment")
    r.key("n", 0.5)
    r.wait_for("What is your name?")
    for ch in "Ada":
        r.key(ch, 0.15)
    r.key(ENTER, 0.3)
    r.wait_for("It is written")
    r.pump(2.0)
    r.key(ENTER, 0.8)

    start = time.time()
    spared = set()
    last_dir = None
    stuck = False
    level_start = time.time()
    trace = os.environ.get("NHF_TRACE")
    shown = 0.0
    while time.time() - start < PLAY:
        if not r.pump(0.05):
            sys.exit("the game ended:\n" + r.text())
        text = r.text()
        if trace and time.time() - shown > float(trace):
            print(f"--- {time.time() - start:.0f} s\n{text}", file=sys.stderr)
            shown = time.time()
        if "--More--" in text:
            r.key(ENTER, 0.3)
            continue
        if "Really attack" in text or "Are you sure" in text:
            r.key(ESC, 0.3)
            me = find_me(r)
            if me and last_dir:
                dx, dy = next(k for k, v in DIRS.items() if v == last_dir)
                spared.add((me[0] + dx, me[1] + dy))
            continue
        if "ESC to abort" in text:
            r.key(ESC, 0.3)
            r.key(ESC, 0.3)
            continue
        if "[yn" in text:
            r.key("n", 0.3)
            continue
        me = find_me(r)
        if not me:
            r.key(ESC, 0.3)
            continue
        last_dir = foe_next_to(r, me, spared)
        if last_dir:
            r.key("F" + last_dir, 0.35)
            continue
        life = hp(r)
        if life and life[0] * 3 < life[1]:
            r.key("20s", 1.5)
            continue
        if stairs_known(r) and (stuck or time.time() - level_start > LEVEL_TIME):
            depth = level(r)
            r.key("_", 0.4)
            r.key(">", 0.4)
            if "Unknown targeting key" in r.text():
                r.key(ESC, 0.3)
                r.key(ESC, 0.3)
                stuck = False
                continue
            r.key(".", 1.5)
            r.key(">", 1.2)
            if level(r) != depth:
                spared.clear()
                level_start = time.time()
            stuck = False
            continue
        if stuck:
            # nothing left to explore and no stairs seen: look for hidden doors
            r.key("10s", 1.0)
            stuck = False
            continue
        before = messages(r).count(NOWHERE)
        r.key("v", 1.2)
        stuck = messages(r).count(NOWHERE) > before

    # Save and quit: S, then "Close the game", back at the main menu.
    # A key pressed while a long action runs only interrupts it, so try a
    # few times.
    for _ in range(5):
        r.key(ESC, 0.5)
        r.key("S", 0.8)
        if r.wait_for("Do you want to stop playing", 2):
            r.pump(1.0)
            r.key("y", 1.0)
            break
    if not r.wait_for("new game", 5) and trace:
        print("--- no main menu after saving\n" + r.text(), file=sys.stderr)
    r.pump(1.5)
    r.finish(b"q")


if __name__ == "__main__":
    main()

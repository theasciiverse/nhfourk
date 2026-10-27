# Changes from upstream

This is the Asciiverse packaging of [NetHack Fourk](https://github.com/tsadok/nhfourk)
by Nathan Eady (jonadab, tsadok on GitHub), the variant of NetHack 4
(Alex Smith and others) that plays on Hardfought. Upstream is the
`upstream` remote, with its full history. The `asciiverse` branch starts
from upstream's `master` at `479383a1` (2026-04-14, "Address several
crash reports from Hardfought.org"), not the last tag, v4.3.0.4
(2017-10-04): `master` is the maintained line, 1,192 commits past that
tag, and calls itself 4.3.0.5. For reference, GitHub's archive of that
commit (`479383a1d05d54b2dfda5cfaab4ca5147aefa7e5.tar.gz`) has sha256
`9afc132c6d293d2b1b7d6a1db940394fed1310e89191f681d285efab2c258ff6` and
is identical to the checkout.

Licence: the NetHack General Public License (`libnethack/dat/license`,
summarised in `COPYING`); libuncursed and some newer files offer
GPL-2.0-or-later as an alternative. `copyright` lists every file. What
the Asciiverse archive holds is all NGPL (the game, libuncursed, the
text tilesets); libjansson (Expat) is not linked in this build, and no
tile images, fonts or icons are shipped, so the CC-BY(-SA), RLTiles,
Geoduck and GFDL items in `copyright` do not apply to the archive. They
stay in the repository as upstream has them. aimake (GPL-3.0-or-later)
is not used to build.

## Build

Only the tty interface is built, through upstream's own GNUmakefile (the
"dumbmake" build): one executable with the game, the interface and
libuncursed's tty plugin linked in, no aimake, no shared libraries, no
SDL. aimake puts every set of `AIMAKE_EXPORT`ed symbols into a shared
library by design (its manual, "SHARED LIBRARIES"), and has no static
mode, so it cannot make the single static musl binary; the GNUmakefile
can.

- `GNUmakefile` builds the current game again: it now compiles
  `achieve.c`, `livelog.c`, `mkaiscav.c` and `spoiler.c`, every level
  description in `libnethack/dat` (`Valkyrie.des` became
  `Shieldmaiden.des`; `advcal`, `garden` and `labyrnth` were missing),
  no longer asks makedefs for the oracles file (there is no `-h` mode
  any more; the oracles are compiled into `rumors.c`), takes `CFLAGS` and
  `CXXFLAGS` from the environment and builds on macOS.
- `asciiverse/build.sh` runs the make in a copy of the tree under
  `out/build` with an empty `DATADIR` and `STATEDIR` (paths decided at run
  time, see below), at `JOBS` parallel jobs (default 2), and with
  `CROSS=x86_64-w64-mingw32` builds the Windows executable: data and
  tools for the build machine first, then the game's objects again with
  MinGW and libuncursed's Windows console plugin. It also makes the man
  page from `doc/nhfourk.pod`.
- `asciiverse/package.sh` packs `release/nhfourk-<target>.tar.gz` (`.zip` on
  Windows) from the list in `asciiverse/archive/nhfourk.txt`: the
  binary, `nhdat`, `license`, the two text tilesets, the man page,
  `COPYING`, `copyright` and `README`.
- `.github/workflows/release.yml` builds static musl Linux in Alpine
  (x86_64, aarch64), macOS (x86_64, arm64) and Windows x86_64 on
  tags; `.gitignore` lets `.github/` in (upstream ignores every dot
  file) and keeps `out/` and `release/` out. The archives go to
  `release/`, not `dist/` as in the other Asciiverse repos, because
  upstream keeps its icons and Debian packaging in `dist/`.

## Files

- Saved games, options, dumplogs, replays and tilesets of the player go
  to `$XDG_DATA_HOME/nhfourk` (else `~/.local/share/nhfourk`) instead of
  `~/.config/NetHackFourk`, with missing parent folders made.
- With an empty `STATEDIR` the score files (`record`, `logfile`,
  `xlogfile`, `livelog`), bones, the panic log and the achievements file
  go to that same folder: nothing is written beside the executable and
  nothing is setgid.
- With an empty `DATADIR` the game reads `nhdat` and the text tilesets
  from the folder its executable is in (`/proc/self/exe` on Linux,
  `_NSGetExecutablePath` on macOS, `argv[0]` otherwise and on Windows), so
  it runs wherever it is unpacked; `NETHACKDIR` still overrides it.
- On Windows the player's folder stays upstream's
  `%APPDATA%\NetHackFourk`.
- aimake builds are unaffected: they get their directories from aimake.

## Bugs fixed

- Character selection offered locked roles and races. The interface
  declared libnethack's `is_unlocked_role()`, `is_unlocked_race()` and
  `is_unlocked_option()` as returning `int`, but they return a `signed
  char`, so the caller read leftover bits of the return register: built
  with glibc and AddressSanitizer every role showed as unlocked, and
  picking a locked one failed with "Invalid character-creation options"
  and "Could not create the save file". The role menu also asked about
  the role at a list position instead of the role listed there.
- `lev_comp` read one byte before its buffer when given no `-o` (as the
  GNUmakefile runs it); found by AddressSanitizer.
- `quest.dat` and the special level files stored some numbers as `long`
  (8 bytes on 64-bit Linux and macOS, 4 on 64-bit Windows), so data
  built on one platform was garbled on the other: the Windows build
  stopped at its first quest text ("com_pager: message 1 not found").
  They are written and read as `int` now.
- Windows with current MinGW-w64: wide paths were formatted with `%s`,
  which C99 printf reads as narrow, so only the drive letter of
  `%APPDATA%` survived and saves went to a folder named `C` beside the
  game; they use `%ls`. `mail.c` calls the C library's `fopen()` for its
  narrow path.

## Not changed

- UBSan reports left shifts of signed ints (`newrng.c`, `dungeon.c`,
  `save.c`): undefined in C, harmless with every compiler in use; left
  as upstream has them. LeakSanitizer reports small leaks of `msgprintf`
  strings when the interface asks about unlocks outside a turn; left as
  well.
- Roles and races beyond human Barbarian and Wizard are locked until
  earned in play, by upstream's design (`doc/changelog-fourk.txt`).
- The network client and the server are not built (no "connect to
  server" entry in the main menu).

## Ours

- **How to play it, at the top of README.** A short note on installing and
  starting it with av, or from a release archive; the original text follows
  unchanged.

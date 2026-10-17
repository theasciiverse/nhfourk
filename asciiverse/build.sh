#!/bin/sh
# Builds NetHack Fourk into out/ with upstream's GNUmakefile (the "dumbmake"
# build): one executable with the game, its interface and libuncursed's tty
# plugin linked in, no aimake, no shared libraries, no SDL or tiles. The
# compiler and flags come from the environment, so one script serves every
# target (see .github/workflows/release.yml):
#
#   asciiverse/build.sh                        # Linux (glibc), macOS
#   LDFLAGS="-static -s" asciiverse/build.sh   # Alpine, static musl
#   CROSS=x86_64-w64-mingw32 asciiverse/build.sh   # Windows, from Linux
#   CFLAGS="-O1 -g -fsanitize=address" CXXFLAGS="$CFLAGS" \
#     LDFLAGS=-fsanitize=address asciiverse/build.sh   # ASan, for testing
#
# JOBS sets make's parallel jobs (default 2, so a build stays gentle on a
# shared machine). The make runs in a copy of the tree under out/build, so the sources stay
# clean. Empty DATADIR and STATEDIR leave the paths to run time: the game
# reads its data from the folder its binary is in and keeps everything it
# writes in the player's data folder ($XDG_DATA_HOME/nhfourk, or
# %APPDATA%\NetHackFourk on Windows).
#
# For Windows the game and the data are first built for the build machine
# (makedefs, the level compiler and the tileset compiler have to run
# there), then the game's objects are compiled again with $CROSS-gcc, with
# libuncursed's Windows console plugin (wincon) in place of tty, and
# linked statically against MinGW's zlib.
#
# Needs a C and C++ compiler, make, flex, bison, zlib (static zlib for
# the static build, MinGW's for Windows) and perl's pod2man for the man
# page.
set -eu
cd "$(dirname "$0")/.."
export CC="${CC:-cc}" CXX="${CXX:-c++}"
export CFLAGS="${CFLAGS:--O2}" CXXFLAGS="${CXXFLAGS:-${CFLAGS:--O2}}"
export LDFLAGS="${LDFLAGS:-}"
B=out/build
rm -rf "$B" && mkdir -p "$B"
tar -cf - --exclude=./out --exclude=./release --exclude=./.git . | tar -xf - -C "$B"
make -C "$B" -j"${JOBS:-2}" DATADIR= STATEDIR= all
if [ -n "${CROSS:-}" ]; then
  objs=$(printf 'print-objs:\n\t@echo $(GAME_O)\n' | make -s -C "$B" -f GNUmakefile -f - print-objs |
         sed 's|plugins/tty\.o|plugins/wincon.o|; s|plugins/wrap_tty\.o|plugins/wrap_wincon.o|')
  cppflags='-DAIMAKE_BUILDOS_MSWin32 -DDUMBMAKE -DGAMESDATADIR="" -DGAMESSTATEDIR=""
    -include dumbmake/dumbmake.h -Ilibnethack/include -Ilibnethack_common/include
    -Inethack/include -Itilesets/include -Ilibuncursed/include'
  W=build-win
  (
    cd "$B" && rm -rf "$W" && mkdir -p "$W"
    list=
    for o in $objs; do
      out="$W/$(echo "$o" | tr / _)"
      case "$o" in
        */wrap_*.o) "$CROSS-g++" -O2 $cppflags -c "$(echo "$o" | sed 's|wrap_\(.*\)\.o$|\1.cxx|')" -o "$out" ;;
        *) "$CROSS-gcc" -O2 --std=c11 -DAIMAKE_NORETURN=_Noreturn $cppflags -c "${o%.o}.c" -o "$out" ;;
      esac
      list="$list $out"
    done
    "$CROSS-g++" -static -s $list -lz -lws2_32 -lshell32 -o "$W/nhfourk.exe"
  )
  cp "$B/$W/nhfourk.exe" out/nhfourk.exe
else
  cp "$B/nethack/src/main" out/nhfourk
fi
cp "$B/libnethack/dat/nhdat" "$B/libnethack/dat/license" \
   "$B/tilesets/dat/textascii.nh4ct" "$B/tilesets/dat/textunicode.nh4ct" out/
chmod 644 out/nhdat out/license out/*.nh4ct
pod2man --section=6 --center="NetHack Fourk" --release="NetHack Fourk 4.3.0.5" \
  --name=NHFOURK doc/nhfourk.pod > out/nhfourk.6
echo "built nhfourk"

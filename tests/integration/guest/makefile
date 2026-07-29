# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
#
# BSD in a GPL repository is deliberate — same reason and same scope
# as SUITE.CPP: nothing GPL may enter the built binary. See AGENTS.md
# "Prior art and external references".
#
# The built SUITE.EXE embeds third-party material, and the notices
# below are part of distributing it:
# - CppUTest, Copyright (c) 2007 Michael Feathers, James Grenning and
#   Bas Vodde, BSD-3-Clause (text in LICENSES/BSD-3-Clause.txt).
# - The Open Watcom C/C++ runtime, Portions Copyright (c) 1983-2002
#   Sybase, Inc., under the Sybase Open Watcom Public License 1.0
#   (text in LICENSES/Watcom-1.0.txt). Source code for that runtime
#   is available under the same licence from the Open Watcom project
#   at https://github.com/open-watcom/open-watcom-v2 — this notice is
#   the licence's section 2.2(d) obligation, so keep it with the
#   binary.
#
# Builds SUITE.EXE, the 16-bit DOS CppUTest program the integration
# tier runs inside a guest. The built binary is checked in beside this
# file, so running this is a maintainer's act when the suite changes —
# not something a test run or a consumer ever does.
#
# Open Watcom is that maintainer's prerequisite and is deliberately
# not a dependency in P11's sense: nothing a consumer installs, and
# nothing importing testaferro touches.
#
#   set WATCOM / PATH per Open Watcom's own setup, then:
#   wmake CPPUTEST=<path to a CppUTest checkout>
#
# Flags follow CppUTest's own platforms/Dos/Makefile, which is where
# its official Open Watcom support lives: large memory model, split
# code segments, and both the leak detector and the standard C++
# library disabled — a 16-bit real-mode DOS target has no business
# with either, and real mode is what lets the result run on a plain
# FreeDOS floppy with no DPMI host staged beside it.

!ifndef CPPUTEST
!error CPPUTEST must name a CppUTest checkout: wmake CPPUTEST=<path>
!endif

CPPU_SRC = $(CPPUTEST)\src\CppUTest
PLAT_SRC = $(CPPUTEST)\src\Platforms\Dos

# W013/W367/W368/W391 fire on CppUTest's own CHECK_EQUAL macros, and
# W472 on its allocator casts; upstream silences exactly these.
WARNOFF = -wcd=13 -wcd=367 -wcd=368 -wcd=391 -wcd=472
DEFS = -dCPPUTEST_MEM_LEAK_DETECTION_DISABLED=1 &
       -dCPPUTEST_STD_CPP_LIB_DISABLED=1
INCS = -i=$(CPPUTEST)\include
CXXFLAGS = -zq -bt=dos -ml -zm -os -oc -d0 -w3 $(WARNOFF) -xds $(DEFS) $(INCS)

all : SUITE.EXE .SYMBOLIC

cpputest.lib : .SYMBOLIC
	-mkdir obj
	wcl $(CXXFLAGS) -c -fo=obj\ $(CPPU_SRC)\*.cpp $(PLAT_SRC)\UtestPlatform.cpp
	-del cpputest.lib
	for %f in (obj\*.obj) do wlib -q cpputest.lib +%f

SUITE.EXE : SUITE.CPP cpputest.lib
	wcl $(CXXFLAGS) -c -fo=obj\ SUITE.CPP
	wlink system dos option quiet, stack=51200 name SUITE.EXE &
	      file obj\SUITE.obj library cpputest.lib

clean : .SYMBOLIC
	-del SUITE.EXE
	-del cpputest.lib
	-if exist obj rmdir /s /q obj

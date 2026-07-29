/* SPDX-FileCopyrightText: 2026 Paul Galbraith
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * BSD in a GPL repository is deliberate: this file is compiled into
 * SUITE.EXE together with CppUTest (BSD-3-Clause) and Open Watcom's
 * runtime (Watcom-1.0, GPL-incompatible, no runtime exception), so
 * any GPL code in the binary would make it undistributable. See
 * AGENTS.md "Prior art and external references".
 *
 * testaferro's own guest suite: the smallest CppUTest program that
 * can prove a guest ran. It tests nothing of testaferro and nothing
 * of DOS — arithmetic and a string compare are enough — because what
 * is under test is the journey, not the assertions.
 *
 * One test fails on purpose. A run where everything passes proves
 * only that output was parsed; the failing one proves testaferro
 * carried a guest's own file, line and message back to the host,
 * which is the half of the contract a green run cannot show.
 */

#include "CppUTest/CommandLineTestRunner.h"
#include "CppUTest/TestHarness.h"

TEST_GROUP(Guest)
{
};

TEST(Guest, Runs)
{
    CHECK_EQUAL(4, 2 + 2);
}

TEST(Guest, Fails)
{
    /* deliberate: this is the failure the host has to replay */
    CHECK_EQUAL(5, 2 + 2);
}

TEST(Guest, RunsToo)
{
    STRCMP_EQUAL("dos", "dos");
}

int main(int argc, char** argv)
{
    return CommandLineTestRunner::RunAllTests(argc, argv);
}

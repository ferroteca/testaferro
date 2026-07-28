# testaferro

[![Python](https://img.shields.io/pypi/pyversions/pytest-testaferro.svg)](https://pypi.org/project/pytest-testaferro/)
[![License](https://img.shields.io/github/license/ferroteca/testaferro.svg)](LICENSE)
![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)
![Tested on Windows](https://img.shields.io/badge/tested%20on-Windows-0078d4.svg)

testaferro is a pytest plugin for DOS-based CppUTest unit testing: a CppUTest suite built for DOS runs inside a guest
provided by reliquary, and its tests surface as pytest tests on the host — running, selecting, and
reporting them feels like an ordinary local pytest run, because it is one. `pytest tests/TESTS.EXE` collects the
executable; the embedding API is the same plugin's programmatic layer. The distribution is named
[pytest-testaferro](https://pypi.org/project/pytest-testaferro/), following the pytest plugin convention; the import —
and everything else — is `testaferro`. (The retired `testaferro` distribution is a tombstone pointing here.)

DOS and CppUTest are what it supports today. Reliquary owns the guest-machine side; testaferro owns the pytest facade and
its test-framework adapters. Other platforms and frameworks are not built; what has been argued for them, and what the
project has decided so far, is in [planning/](planning/).

## Where it fits

Every existing pytest-and-virtual-machine pairing points the same direction: the machine is a fixture, and the tests
are Python functions you write on the host. [pytest-vagrant](https://github.com/steinwurf/pytest-vagrant) hands your
test function a vagrant box to ssh into; [pytest-testinfra](https://github.com/pytest-dev/pytest-testinfra) asserts on
a remote machine's state — packages, services, files — over ssh, ansible, or docker;
[pytest-embedded](https://github.com/espressif/pytest-embedded) (including its QEMU service) drives a device under
test from a host-side function and folds the device's unit-test output into its reports. Useful shapes, all three —
and in all three the pytest items are host-authored Python, with the machine as scenery.

testaferro points the other way: **the items are the guest's own tests.** The suite is a native binary built for the
guest OS, each of its cases surfaces as an ordinary pytest item with its own id and its own failure, and the machine
that ran them is machinery no test names. The nearest neighbour in that direction is
[pytest-cpp](https://github.com/pytest-dev/pytest-cpp), which surfaces *host-runnable* test binaries as pytest items —
its harness options can wrap the binary in qemu or wine, but that is a command prefix. testaferro begins where the
command prefix stops sufficing: when running the suite means booting an operating system, with drives to stage, a boot
to sequence, and state to sweep. (Go has this shape in [vmtest](https://github.com/hugelgupf/vmtest), which runs Go
unit tests inside QEMU guests and collects their results; testaferro is that idea for pytest and native guest
binaries.)

## Status: alpha

The architecture is built and works for its first target pair: a DOS-built CppUTest suite run inside a reliquary guest,
surfacing as ordinary pytest items on the host. It was verified end to end before the move onto reliquary's blueprint
model; since that move the unit suite passes but no guest has actually run, so treat a first run here as unproven
ground and expect to report what you find. testaferro is pre-1.0 and makes no compatibility promise: interfaces change
coherently and completely, without a bridge for the old shape.

## Usage

### Point pytest at the executable

Nothing to write, and nothing to install beyond the distribution — testaferro is a pytest plugin, so pytest's own
command is the whole of it:

```bash
pytest tests/TESTS.EXE
```

Each test in the suite becomes an item under the executable's own node, so everything downstream is pytest as usual:

```
tests/TESTS.EXE::Vring-Wraps PASSED
tests/TESTS.EXE::Vring-Fails FAILED
```

`-k`, `-x`, `--lf`, `--collect-only` and node ids all work, because there is no wrapper for them to work through. A
failure reports what the guest reported — its file, line and assertion — never a traceback into testaferro. Run one
test with `pytest "tests/TESTS.EXE::Vring-Wraps"`, and keep the guest's home for inspection with
`--testaferro-keep-guest-home`.

**The plugin activates on installation, and claims almost nothing.** A file *you name* on the command line is claimed
when it is a DOS program (or when a declaration says a guest runs it). A directory *scan* claims only what you opted
in — a `testaferro-suites` mask in pytest's ini, or a `suites` mask on an environment in `testaferro.ini`:

```ini
# pytest.ini — a tree scan collects these beside your host tests
[pytest]
testaferro-suites = *_TEST.EXE
```

```ini
# testaferro.ini — the same opt-in, saying which environment runs them
[msdos]
boot_image = images/msdos.img
suites = *_TEST.EXE
```

So installing testaferro into an existing venv changes no existing run: with nothing opted in, a scan collects
nothing. A binary this host can run itself (a plain Windows PE) is never claimed by inference — only a declaration
claims one, because nothing about the file can tell testaferro that the situation demands a VM.

Every declaration keyword has a command-line and ini spelling, kebab-cased: `--testaferro-environment`,
`--testaferro-boot-image`, `--testaferro-machine-config` (and `testaferro-environment`, `testaferro-boot-image`, … in
pytest's ini). The command line wins over the ini, and both win over a declaration. Blueprint fields — `memory`,
`drives`, `platform` — have no option of their own: they are reliquary's words in a declaration, not testaferro's.

**Enumerating costs a guest boot**, once per suite — and once per xdist worker, since every worker collects. If you
also build the suite for the host, point testaferro at that twin and collection stops booting anything:

```bash
pytest tests/ --testaferro-enumerator=build/host/{stem}.exe
```

`{stem}` and `{name}` stand for each claimed executable's own, so one setting serves a whole tree, and a suite with no
twin built simply falls back to the guest. That fallback is honest about itself: a list read inside the guest can lose
its head to the screen, so it warns (`GuestEnumerationWarning`) rather than quietly showing you fewer tests than exist.

### Embed it in a test module

Hand the facade a reference to the suite executable in a normal pytest test module:

```python
from pathlib import Path

import testaferro

test_guest_case = testaferro.guest_suite(Path(__file__).parent / "TESTS.EXE")
```

testaferro interrogates the referenced file and selects the matching guest backend: a DOS executable runs inside a
guest provided by reliquary (a dependency of testaferro), while a provably non-DOS binary — say, the host
build of the suite passed by mistake — is rejected with a clear error before any guest boots, naming the format and
architecture it found (Windows PE, Linux/BSD ELF, macOS Mach-O, 16-bit NE/LX/LE; x86 through ARM64). Headerless
images (`.com`-style raw code) carry nothing to prove, so they pass through for the guest itself to judge. The framework adapter
defaults to `testaferro.cpputest`; pass `framework=` to use a different one.

The guest machine's working state is testaferro's business, not the consumer's: each run happens in a fresh, disposable
reliquary home under testaferro's cache (`%LOCALAPPDATA%\testaferro` on Windows, `$XDG_CACHE_HOME/testaferro`
elsewhere), and the machine is created there fresh for each guest session and swept away with it. Zero configuration boots a
FreeDOS image that is downloaded once and cached; pass `boot_image=` to boot a caller-supplied DOS floppy image
instead.

The suite executable reaches the guest on a work drive testaferro adds to the machine: a host directory served into the
guest as a FAT volume, with the executable staged into it before boot. The guest sees it as its first hard disk —
normally `C:` — and testaferro runs it there by name. Nothing is written into your boot image.

### Named test environments

A **test environment** is what a suite runs in, and naming one is the whole of what a suite writes. Declare a named
environment once when several suites share it. A declaration is a reliquary **blueprint** — the machine's own
description, in reliquary's vocabulary. `config()` accepts blueprint machine fields directly (`platform`, `memory`,
`drives`, `boot`, `backend_settings`, …), which pass through untouched for reliquary to validate, or a complete
`machine_config=` template: an `EnvironmentSpec`, a mapping, a whole blueprint document, or a path to a `.rlqb` file.

```python
import testaferro

testaferro.config("msdos", boot_image="images/msdos.img", memory=32)

test_guest_case = testaferro.guest_suite(
    "build/TESTS.EXE", environment="msdos")
```

The same declarations can live in an optional per-project `testaferro.ini` — one section per environment, the
declarative twin of `config()`. `guest_suite()` searches upward from the calling test module and loads the file
automatically, so the suite can name only the executable when a unique environment matches:

```ini
[msdos]
boot_image = images/msdos.img
memory = 32

[custom]
machine_config = machines/custom.rlqb
```

```python
test_guest_case = testaferro.guest_suite("build/TESTS.EXE")
```

Relative `boot_image` / `machine_config` / `template` paths resolve from the ini file's directory. Structured blueprint
fields (`drives`, `boot`, `scripts`, `backend_settings`, `control_planes`, `parameters`) accept JSON values; a bare
integer stays an integer, so `memory = 32` and `memory = 32M` are both accepted. Call `testaferro.load_config(path)` to
load an explicit file, or `load_config()` to search upward from the current directory.

A declaration is a template, never a running machine: every guest session creates a fresh machine from it, so runs do
not share guest state. What that costs per session is the blueprint's own business — reliquary's `materialize` mode on
each drive decides whether media is attached in place, copied, or layered. Name the environment — `environment="msdos"`
— when more than one declared DOS environment would otherwise match. With no declarations, DOS executables retain the
implicit downloaded-FreeDOS guest.

Between declaring nothing and declaring an environment of your own sits a name:

```python
test_guest_case = testaferro.guest_suite("build/TESTS.EXE", environment="freedos")
```

`freedos` is a **standard environment** testaferro curates — the zero-configuration DOS guest, made nameable, so a
suite can say which environment it means without the project declaring one. More arrive as guests grow.

A name resolves against your own declarations first and the standard catalog second, so declaring `freedos` yourself
gets you yours. The catalog is reached by asking for it by name and never by inference: with nothing declared, an
executable's own format still selects an environment exactly as before. Nothing is ever resolved from your reliquary
home — a test run depends only on what testaferro authored or what the project checked in.

With several guest suites — or parallel pytest processes — open a *run*, so the image choice is made once and
every run's state is swept together. From the consuming project's `conftest.py`:

```python
import testaferro

testaferro.start()                  # or testaferro.start(boot_image=...)

def pytest_unconfigure(config):
    testaferro.stop()
```

`start()` costs nothing until a guest actually runs; `stop()` sweeps the run's staged image and every guest home inside
it, keeping the once-downloaded FreeDOS image cached for the next run (`stop(clear_downloads=True)` scrubs that too).
Forgetting `stop()` is not fatal — `start()` registers an `atexit` failsafe that sweeps the run at interpreter
exit — but the explicit call is still preferred: it cleans up at a deterministic point and is where
`clear_downloads=True` can be said.

Because every run gets a private home and a private image copy, suites in separate pytest processes never share
mutable guest state — safe to parallelize. With [pytest-xdist](https://pypi.org/project/pytest-xdist/), run
`pytest -n auto --dist loadfile`: `loadfile` keeps each test file's items on one worker, so a whole guest suite stays
together (preserving the one-boot `run_all()` batching) while *different* suites boot their guests concurrently on
other workers. Plain `--dist load` would scatter a suite's items across workers and degrade it to one boot per test.

Guest lifecycle is automatic. Enumeration runs in a short guest session of its own — skipped entirely when a
host-built twin supplies the list — and the selected tests then share one execution guest, stopped by pytest even when
a test fails.

Every test in the guest suite becomes its own pytest item, so pytest's selection drives what actually runs remotely:

- run everything (`pytest`) and the facade batches the whole suite into a single guest run — one execution boot for the
  session;
- narrow the selection (`pytest -k Wraps`, an explicit node id) and only the selected tests run in the guest,
  individually.

A failing guest test fails its pytest item with the guest side's original file, line, and assertion message — not a
traceback into the facade. IDE test integrations work per item too: the generated test function reports the
`guest_suite()` call site as its source, so run-this-test and jump-to-source in PyCharm-style test trees resolve to
your module.

Under the hood, reliquary owns the guest machine and a framework adapter knows the suite's argv and output grammar.
`testaferro.suite.SuiteBackend` composes reliquary execution with the selected adapter; `guest_suite()` also accepts a
prebuilt backend as the custom escape hatch.

Enumeration can be delegated to a host-built twin of a guest suite through `enumerator=`, and for a suite of any size
it should be. Guest output is captured by reading the guest's screen, so a command whose output scrolls past one
screenful leaves only its tail there — which bites enumeration hardest, since `-ln` lists every test at once. A host
twin built from the same sources both avoids that and keeps the two builds honest against each other: a test the guest
build dropped shows up as one that did not run.

The framework adapter remains usable directly where the facade is more than you need — it is just argv and grammar,
independent of how you obtained the output:

```python
from testaferro import cpputest

results = cpputest.parse(log)  # {"ran", "failed", "summary"}
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, the required checks, and contribution licensing terms.

## License

BSD 3-Clause; see [LICENSE](LICENSE). The project follows REUSE conventions (SPDX headers
plus [REUSE.toml](REUSE.toml)).

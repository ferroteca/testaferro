# testaferro

[![Python](https://img.shields.io/pypi/pyversions/testaferro.svg)](https://pypi.org/project/testaferro/)
[![License](https://img.shields.io/github/license/ferroteca/testaferro.svg)](LICENSE)
![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)
![Tested on Windows](https://img.shields.io/badge/tested%20on-Windows-0078d4.svg)

testaferro is a pytest facade for DOS-based CppUTest unit testing: a CppUTest suite built for DOS runs inside a QEMU
guest via reliquary, and its tests surface as pytest tests on the host — running, selecting, and
reporting them feels like an ordinary local pytest run.

DOS and CppUTest are what it supports today. Reliquary owns the guest-machine side; testaferro owns the pytest facade and
its test-framework adapters. Other platforms and frameworks are not built; what has been argued for them, and what the
project has decided so far, is in [planning/](planning/).

## Status: alpha

The architecture is built and works for its first target pair: a DOS-built CppUTest suite run inside a QEMU guest,
surfacing as ordinary pytest items on the host. It was verified end to end before the move onto reliquary's blueprint
model; since that move the unit suite passes but no guest has actually run, so treat a first run here as unproven
ground and expect to report what you find. testaferro is pre-1.0 and makes no compatibility promise: interfaces change
coherently and completely, without a bridge for the old shape.

## Usage

Hand the facade a reference to the suite executable in a normal pytest test module:

```python
from pathlib import Path

import testaferro

test_guest_case = testaferro.guest_suite(Path(__file__).parent / "TESTS.EXE")
```

testaferro interrogates the referenced file and selects the matching guest backend: a DOS executable runs inside a
QEMU guest through reliquary (a dependency of testaferro), while a provably non-DOS binary — say, the host
build of the suite passed by mistake — is rejected with a clear error before any guest boots, naming the format and
architecture it found (Windows PE, Linux/BSD ELF, macOS Mach-O, 16-bit NE/LX/LE; x86 through ARM64). Headerless
images (`.com`-style raw code) carry nothing to prove, so they pass through for the guest itself to judge. The framework adapter
defaults to `testaferro.cpputest`; pass `framework=` to use a different one.

The guest machine's working state is testaferro's business, not the consumer's: each run happens in a fresh, disposable
reliquary home under testaferro's cache (`%LOCALAPPDATA%\testaferro` on Windows, `$XDG_CACHE_HOME/testaferro`
elsewhere), and the machine is created there fresh for the session and swept away with it. Zero configuration boots a
FreeDOS image that is downloaded once and cached; pass `boot_image=` to boot a caller-supplied DOS floppy image
instead.

The suite executable reaches the guest on a work drive testaferro adds to the machine: a host directory served into the
guest as a FAT volume, with the executable staged into it before boot. The guest sees it as its first hard disk —
normally `C:` — and testaferro runs it there by name. Nothing is written into your boot image.

### Named test machines

Declare a named machine once when several suites share it. A declaration is a reliquary **blueprint** — the machine's
own description, in reliquary's vocabulary. `config()` accepts blueprint machine fields directly (`memory`, `drives`,
`boot`, `backend_settings`, …), or a complete `machine_config=` template: a `MachineSpec`, a mapping, a whole blueprint
document, or a path to a `.rlqb` file. The template supplies its platform when it declares one; `platform=` is optional
and verifies an explicit choice.

```python
import testaferro

testaferro.config("msdos", boot_image="images/msdos.img", memory=32)

test_guest_case = testaferro.guest_suite(
    "build/TESTS.EXE", machine="msdos")
```

The same declarations can live in an optional per-project `testaferro.ini` — one section per machine, the
declarative twin of `config()`. `guest_suite()` searches upward from the calling test module and loads the file
automatically, so the suite can name only the executable when a unique machine matches:

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

A declaration is a template, never a running machine: every backend session creates a fresh machine from it, so runs do
not share guest state. What that costs per session is the blueprint's own business — reliquary's `materialize` mode on
each drive decides whether media is attached in place, copied, or layered. Use `platform="dos"` or `machine="msdos"`
when more than one configured DOS machine would otherwise match. With no declarations, DOS executables retain the
implicit downloaded-FreeDOS machine.

With several guest suites — or parallel pytest processes — open a *session*, so the image choice is made once and
every run's state is swept together. From the consuming project's `conftest.py`:

```python
import testaferro

testaferro.start()                  # or testaferro.start(boot_image=...)

def pytest_unconfigure(config):
    testaferro.stop()
```

`start()` costs nothing until a guest actually runs; `stop()` sweeps the session's staged image and every run home,
keeping the once-downloaded FreeDOS image cached for the next session (`stop(clear_downloads=True)` scrubs that too).
Forgetting `stop()` is not fatal — `start()` registers an `atexit` failsafe that sweeps the session at interpreter
exit — but the explicit call is still preferred: it cleans up at a deterministic point and is where
`clear_downloads=True` can be said.

Because every run gets a private home and a private image copy, suites in separate pytest processes never share
mutable guest state — safe to parallelize. With [pytest-xdist](https://pypi.org/project/pytest-xdist/), run
`pytest -n auto --dist loadfile`: `loadfile` keeps each test file's items on one worker, so a whole guest suite stays
together (preserving the one-boot `run_all()` batching) while *different* suites boot their guests concurrently on
other workers. Plain `--dist load` would scatter a suite's items across workers and degrade it to one boot per test.

Backend lifecycle hooks are automatic. Enumeration runs in a short collection session; selected tests then share one
execution session, which is cleaned up by pytest even when a test fails.

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

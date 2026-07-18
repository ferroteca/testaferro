# testaferro

testaferro is a pytest facade for DOS-based CppUTest unit testing: a CppUTest suite built for DOS runs inside a QEMU
guest via the bundled relict runner, and its tests surface as pytest tests on the host — running, selecting, and
reporting them feels like an ordinary local pytest run.

DOS and CppUTest are what it supports today. Relict owns the guest-machine side; testaferro owns the pytest facade and
its test-framework adapters. Other platforms and frameworks remain planned work (see [ROADMAP.md](ROADMAP.md)).

## Status: milestone 1 working

The architecture is built and verified end to end for its first target pair: a DOS-built CppUTest suite run inside a
QEMU guest, surfacing as ordinary pytest items on the host.

## Usage

Hand the facade a reference to the suite executable in a normal pytest test module:

```python
from pathlib import Path

import testaferro

test_guest_case = testaferro.guest_suite(Path(__file__).parent / "TESTS.EXE")
```

testaferro interrogates the referenced file and selects the matching guest backend: a DOS executable runs inside a
QEMU guest through the relict runner (a dependency of testaferro), while a provably non-DOS binary — say, the host
build of the suite passed by mistake — is rejected with a clear error before any guest boots, naming the format and
architecture it found (Windows PE, Linux/BSD ELF, macOS Mach-O, 16-bit NE/LX/LE; x86 through ARM64). Headerless
images (`.com`-style raw code) carry nothing to prove, so they pass through for the guest itself to judge. The framework adapter
defaults to `testaferro.cpputest`; pass `framework=` to use a different one.

The runner's working state is testaferro's business, not the consumer's: each run happens in a fresh, disposable work
directory under testaferro's cache (`%LOCALAPPDATA%\testaferro` on Windows, `$XDG_CACHE_HOME/testaferro` elsewhere),
seeded with a bootable FreeDOS image that is downloaded once and cached. Pass `boot_image=` to boot a caller-supplied
DOS floppy image instead.

### Named test machines

Declare a named machine once when several suites share it. `config()` accepts relict `MachineConfig` options directly,
or a complete `machine_config=` template (a `MachineConfig`, versioned mapping, or path to relict's machine document).
The template supplies its platform when it declares one; `platform=` is optional and verifies an explicit choice.

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
machine_config = machines/custom.json
```

```python
test_guest_case = testaferro.guest_suite("build/TESTS.EXE")
```

Relative `boot_image` / `machine_config` / `template` paths resolve from the ini file's directory. Structured
relict fields (`drives`, `qemu_args`, `machine`) accept JSON values. Call `testaferro.load_config(path)` to load an
explicit file, or `load_config()` to search upward from the current directory.

Each guest backend session gets its own copy of the template's mutable drive media, so runs do not share guest state.
Use `platform="dos"` or `machine="msdos"` when more than one configured DOS machine would otherwise match. With no
declarations, DOS executables retain the implicit downloaded-FreeDOS machine.

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

Under the hood, relict is the guest-machine runner and a framework adapter knows the suite's argv and output grammar.
`testaferro.suite.SuiteBackend` composes relict execution with the selected adapter; `guest_suite()` also accepts a
prebuilt backend as the custom escape hatch. Enumeration can be delegated to a host-built twin of a guest suite through
`enumerator=`.

The lower layers remain usable directly where the facade is more than you need:

```python
log = relict.run_guest_program("TESTS.EXE",
                               args=cpputest.VERBOSE_ARGS)
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

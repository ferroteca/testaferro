# testaferro

testaferro is a pytest facade for DOS-based CppUTest unit testing: a CppUTest suite built for DOS runs inside a QEMU
guest via the bundled relict runner, and its tests surface as pytest tests on the host — running, selecting, and
reporting them feels like an ordinary local pytest run.

DOS and CppUTest are what it supports; the design keeps both as pluggable aspects — guest OS and guest unit-test
framework — with the intent that other guest OSes and frameworks could potentially be supported in the future (see
[ROADMAP.md](ROADMAP.md)).

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

Under the hood the two aspects — guest-OS *runner* (any callable
`run(exe_path, args) -> output`) and *framework adapter* (a module that knows the suite's argv and output grammar) —
stay orthogonal and swap independently: `testaferro.suite.SuiteBackend` composes any runner with any adapter via its
`run=` parameter, and `guest_suite()` accepts such a prebuilt backend in place of the executable path. A different
runner (a host subprocess, some future guest OS's runner) reuses the CppUTest adapter unchanged, and a different framework
adapter reuses any runner unchanged. Enumeration can also be delegated — a consuming project can enumerate from a
host-built twin of its guest suite so the two builds stay honest against each other (`enumerator=`).

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

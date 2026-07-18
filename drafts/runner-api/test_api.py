# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the spec's protocol, config types, and conventions."""

import dataclasses
import unittest

import testaferro_runner_api as api


class FakeMachine:
    """A minimal conforming machine (runner instance)."""

    platform = "dos"

    def __init__(self, config=None):
        self.config = config or api.DosConfig()

    def provision(self, dist_dir):
        pass

    def run(self, exe_path, args, home):
        return ""


class ConventionTests(unittest.TestCase):
    def test_boot_image_and_dist_names_are_fixed(self):
        # load-bearing constants: callers stage
        # <home>/dist/boot.img and runners boot it
        self.assertEqual(api.BOOT_IMAGE_NAME, "boot.img")
        self.assertEqual(api.DIST_DIR_NAME, "dist")


class PlatformTests(unittest.TestCase):
    def test_dos_is_the_whole_platform_set_today(self):
        # deliberate: adding a platform is a spec release, and this
        # test is updated in the same release
        self.assertEqual(set(api.PLATFORMS), {"dos"})

    def test_each_platform_names_its_config_type(self):
        self.assertIs(api.PLATFORMS["dos"], api.DosConfig)
        for config_type in api.PLATFORMS.values():
            self.assertTrue(issubclass(config_type, api.RunnerConfig))


class ConfigTests(unittest.TestCase):
    def test_generic_config_defaults_to_runner_choices(self):
        config = api.RunnerConfig()

        self.assertIsNone(config.boot_image)
        self.assertIsNone(config.timeout)

    def test_configs_are_immutable(self):
        config = api.RunnerConfig(boot_image="ready.img")

        with self.assertRaises(dataclasses.FrozenInstanceError):
            config.boot_image = "other.img"

    def test_dos_config_extends_the_generic_config(self):
        config = api.DosConfig(timeout=90.0)

        self.assertIsInstance(config, api.RunnerConfig)
        self.assertEqual(config.timeout, 90.0)

    def test_a_runner_config_extension_inherits_fields(self):
        # the third level of the chain: a runner's own config
        @dataclasses.dataclass(frozen=True)
        class FakeRunnerConfig(api.DosConfig):
            emulator_path: str = "emu"

        config = FakeRunnerConfig(boot_image="ready.img")

        self.assertIsInstance(config, api.DosConfig)
        self.assertEqual((config.boot_image, config.emulator_path),
                         ("ready.img", "emu"))


class ProtocolTests(unittest.TestCase):
    def test_conforming_machine_is_a_runner(self):
        self.assertIsInstance(FakeMachine(), api.Runner)

    def test_object_without_run_is_not_a_runner(self):
        class NotARunner:
            platform = "dos"
            config = api.DosConfig()

            def provision(self, dist_dir):
                pass

        self.assertNotIsInstance(NotARunner(), api.Runner)


if __name__ == "__main__":
    unittest.main()

import unittest

from pynput.keyboard import Key

from joycon_mapper import TapCycleShortcut, is_home_app_switcher_combo


class FakeKeyboard:
    def __init__(self):
        self.events = []

    def press(self, key):
        self.events.append(("press", key))

    def release(self, key):
        self.events.append(("release", key))


class TapCycleShortcutTests(unittest.TestCase):
    def setUp(self):
        self.keyboard = FakeKeyboard()
        self.shortcut = TapCycleShortcut(
            self.keyboard,
            [Key.cmd],
            Key.tab,
            confirm_seconds=0.8,
        )

    def test_press_holds_command_and_taps_tab_immediately(self):
        self.assertTrue(self.shortcut.press(now=10.0))
        self.assertEqual(
            self.keyboard.events,
            [
                ("press", Key.cmd),
                ("press", Key.tab),
                ("release", Key.tab),
            ],
        )

    def test_each_physical_press_advances_exactly_once(self):
        self.shortcut.press(now=10.0)
        self.shortcut.release(now=10.1)
        self.shortcut.press(now=10.4)
        self.shortcut.release(now=10.5)

        tab_presses = [
            event for event in self.keyboard.events if event == ("press", Key.tab)
        ]
        command_presses = [
            event for event in self.keyboard.events if event == ("press", Key.cmd)
        ]
        self.assertEqual(len(tab_presses), 2)
        self.assertEqual(len(command_presses), 1)

    def test_release_waits_then_confirms_selection(self):
        self.shortcut.press(now=10.0)
        self.shortcut.release(now=10.1)

        self.assertFalse(self.shortcut.tick(now=10.89))
        self.assertTrue(self.shortcut.tick(now=10.9))
        self.assertEqual(self.keyboard.events[-1], ("release", Key.cmd))

    def test_new_press_cancels_pending_confirmation(self):
        self.shortcut.press(now=10.0)
        self.shortcut.release(now=10.1)

        self.shortcut.press(now=10.7)
        self.assertFalse(self.shortcut.tick(now=10.9))
        self.assertTrue(self.shortcut.active)

    def test_force_release_prevents_stuck_command(self):
        self.shortcut.press(now=10.0)

        self.assertTrue(self.shortcut.force_release())
        self.assertFalse(self.shortcut.active)
        self.assertEqual(self.keyboard.events[-1], ("release", Key.cmd))

    def test_command_tab_combo_detection(self):
        self.assertTrue(is_home_app_switcher_combo(([Key.cmd], Key.tab)))
        self.assertFalse(is_home_app_switcher_combo(([Key.cmd], Key.enter)))
        self.assertFalse(is_home_app_switcher_combo(([Key.cmd, Key.shift], Key.tab)))


if __name__ == "__main__":
    unittest.main()

import unittest
from src.application.commands.command_history import CommandHistory, Command, CommandType


class TestCommandHistory(unittest.TestCase):
    def setUp(self):
        self.history = CommandHistory(max_history=10)

    def test_initial_state(self):
        self.assertFalse(self.history.can_undo)
        self.assertFalse(self.history.can_redo)
        self.assertEqual(self.history.undo_count, 0)
        self.assertEqual(self.history.redo_count, 0)

    def test_execute_and_undo(self):
        executed = []
        undone = []
        cmd = Command(
            command_type=CommandType.MODIFY,
            execute=lambda: executed.append(True),
            undo=lambda: undone.append(True),
            description="Test"
        )
        self.history.execute(cmd)
        self.assertEqual(len(executed), 1)
        self.assertTrue(self.history.can_undo)

        result = self.history.undo()
        self.assertTrue(result)
        self.assertEqual(len(undone), 1)
        self.assertFalse(self.history.can_undo)

    def test_undo_redo_cycle(self):
        executed = []
        cmd = Command(
            command_type=CommandType.MODIFY,
            execute=lambda: executed.append(True),
            undo=lambda: None,
            description="Test"
        )
        self.history.execute(cmd)
        self.history.undo()
        self.assertTrue(self.history.can_redo)
        result = self.history.redo()
        self.assertTrue(result)
        self.assertFalse(self.history.can_redo)

    def test_undo_when_empty(self):
        self.assertFalse(self.history.undo())

    def test_redo_when_empty(self):
        self.assertFalse(self.history.redo())

    def test_multiple_commands(self):
        for i in range(5):
            self.history.execute(Command(
                command_type=CommandType.MODIFY,
                execute=lambda: None,
                undo=lambda: None,
                description=f"Cmd {i}"
            ))
        self.assertEqual(self.history.undo_count, 5)
        self.history.undo()
        self.assertEqual(self.history.undo_count, 4)

    def test_new_execute_clears_redo(self):
        cmd1 = Command(CommandType.MODIFY, lambda: None, lambda: None, "First")
        cmd2 = Command(CommandType.MODIFY, lambda: None, lambda: None, "Second")
        self.history.execute(cmd1)
        self.history.undo()
        self.assertTrue(self.history.can_redo)
        self.history.execute(cmd2)
        self.assertFalse(self.history.can_redo)
        self.assertEqual(self.history.undo_count, 1)

    def test_clear(self):
        self.history.execute(Command(CommandType.MODIFY, lambda: None, lambda: None, "Test"))
        self.history.clear()
        self.assertFalse(self.history.can_undo)
        self.assertFalse(self.history.can_redo)

    def test_max_history(self):
        small = CommandHistory(max_history=3)
        for i in range(5):
            small.execute(Command(CommandType.MODIFY, lambda: None, lambda: None, f"Cmd {i}"))
        self.assertEqual(small.undo_count, 3)



if __name__ == '__main__':
    unittest.main()

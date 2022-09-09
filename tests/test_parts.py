import sys
import itertools
import typing

import pytest

import PySide6.QtWidgets

import modules.parts


class TestParts:
    part_count = 6
    part_numbers = list(range(1, part_count + 1))

    class StepRange:
        def __init__(self, step_count: int):
            self.range = range(1, step_count + 1)

        def __iter__(self):
            return self.range.__iter__()

    @classmethod
    def setup_class(cls) -> None:
        cls.application = PySide6.QtWidgets.QApplication(sys.argv)

    @classmethod
    def teardown_class(cls) -> None:
        cls.application.deleteLater()

    @staticmethod
    def test_default() -> None:
        parts = modules.parts.Parts()
        assert parts.step_count == 16
        assert parts.tempo == 60
        assert parts.bpm == 4
        for part_number, step_number in itertools.product(TestParts.part_numbers, TestParts.StepRange(16)):
            step = parts.step_at(part_number, step_number)
            assert step.isChecked() is False
            assert step.get_overridden_values() is None

    @staticmethod
    @pytest.mark.parametrize('with_overridden_values', [False, True], ids=['without_overridden_values', 'with_overridden_values'])
    def test_restore(with_overridden_values: bool) -> None:
        stored_values = {
            'step-count': 16,
            'enabled-steps': {f'part{part_number}': [part_number] for part_number in TestParts.part_numbers},
        }
        if with_overridden_values:
            stored_values['overridden-controls'] = {
                f'part{part_number}': {part_number: {'layer1': {'level': 32}}} for part_number in TestParts.part_numbers
            }
        parts = modules.parts.Parts.restore(stored_values)
        for part_number, step_number in itertools.product(TestParts.part_numbers, TestParts.StepRange(16)):
            step = parts.step_at(part_number, step_number)
            assert step.isChecked() is (part_number == step_number)
            if not with_overridden_values or part_number != step_number:
                assert step.get_overridden_values() is None
            else:
                assert step.get_overridden_values() == {'layer1': {'level': 32}}
        assert parts.store()['enabled-steps'] == stored_values['enabled-steps']
        if with_overridden_values:
            assert parts.store()['overridden-controls'] == stored_values['overridden-controls']
        else:
            assert 'overridden-controls' not in parts.store()

    @staticmethod
    def test_change_step_count() -> None:
        stored_values = {
            'step-count': 32,
            'beats-per-measure': 4,
            'enabled-steps': {f'part{part_number}': [] for part_number in TestParts.part_numbers},
        }
        for step_number in TestParts.StepRange(32):
            part_number = (step_number % TestParts.part_count) + 1
            stored_values['enabled-steps'][f'part{part_number}'].append(step_number)
        parts = modules.parts.Parts.restore(stored_values)

        min_step_count = 32
        assert parts.step_count == 32
        for new_step_count in (32, 16, 32):
            parts.change_step_count(new_step_count, stored_values['beats-per-measure'])
            min_step_count = min(min_step_count, new_step_count)
            for part_number, step_number in itertools.product(TestParts.part_numbers, TestParts.StepRange(min_step_count)):
                step = parts.step_at(part_number, step_number)
                expect_checked = part_number == (step_number % TestParts.part_count) + 1
                assert step.isChecked() is expect_checked
            for part_number, step_number in itertools.product(TestParts.part_numbers, list(TestParts.StepRange(new_step_count))[min_step_count:]):
                step = parts.step_at(part_number, step_number)
                assert step.isChecked() is False

    @staticmethod
    def test_insert_delete_steps() -> None:
        def restored_parts(enabled_steps: typing.Optional[typing.List[int]] = None) -> modules.parts.Parts:
            stored_values = {
                'step-count': 16,
                'beats-per-measure': 4,
                'enabled-steps': {'part1': [1, 5, 9, 13]},
            }
            if enabled_steps is not None:
                stored_values['enabled-steps']['part1'] = enabled_steps
            return modules.parts.Parts.restore(stored_values)

        # Insert before.
        for step_count in (1, 2, 3):
            parts = restored_parts()
            parts._Parts__insert_steps(0, step_count)
            assert parts.store()['enabled-steps']['part1'] == [1 + step_count, 5 + step_count, 9 + step_count, 13 + step_count]

            parts._Parts__delete_steps(1, step_count)
            assert parts.store()['enabled-steps']['part1'] == [1, 5, 9, 13]

        # Insert after.
        for step_count in (1, 2, 3):
            parts = restored_parts()
            parts._Parts__insert_steps(1, step_count)
            assert parts.store()['enabled-steps']['part1'] == [1, 5 + step_count, 9 + step_count, 13 + step_count]

            parts._Parts__delete_steps(2, step_count)
            assert parts.store()['enabled-steps']['part1'] == [1, 5, 9, 13]

        # Move everything to the right, all at once.
        parts = restored_parts(list(TestParts.StepRange(16)))
        assert parts.store()['enabled-steps']['part1'] == list(TestParts.StepRange(16))
        parts._Parts__insert_steps(0, 16)
        assert 'enabled-steps' not in parts.store()

        # Move everything to the right, one by one.
        parts = restored_parts(list(TestParts.StepRange(16)))
        for i in range(16):
            assert parts.store()['enabled-steps']['part1'] == list(range(1 + i, 16 + 1))
            parts._Parts__insert_steps(0, 1)
            if i < 15:
                assert parts.store()['enabled-steps']['part1'] == list(range(2 + i, 16 + 1))
            else:
                assert 'enabled-steps' not in parts.store()

        # Delete everything, all at once.
        parts = restored_parts(list(TestParts.StepRange(16)))
        assert parts.store()['enabled-steps']['part1'] == list(TestParts.StepRange(16))
        parts._Parts__delete_steps(1, 16)
        assert 'enabled-steps' not in parts.store()

        # Delete everything, one by one (starting from the beginning).
        parts = restored_parts(list(TestParts.StepRange(16)))
        for i in range(16):
            assert parts.store()['enabled-steps']['part1'] == list(TestParts.StepRange(16 - i))
            parts._Parts__delete_steps(1, 1)
            if i < 15:
                assert parts.store()['enabled-steps']['part1'] == list(TestParts.StepRange(16 - (i + 1)))
            else:
                assert 'enabled-steps' not in parts.store()

        # Delete everything, one by one (starting from the end).
        parts = restored_parts(list(TestParts.StepRange(16)))
        for i in range(16):
            assert parts.store()['enabled-steps']['part1'] == list(TestParts.StepRange(16 - i))
            parts._Parts__delete_steps(16 - i, 1)
            if i < 15:
                assert parts.store()['enabled-steps']['part1'] == list(TestParts.StepRange(16 - (i + 1)))
            else:
                assert 'enabled-steps' not in parts.store()

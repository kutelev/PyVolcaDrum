import itertools
import typing

import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

import common

__all__ = ['Parts']


class Step(PySide6.QtWidgets.QToolButton):
    def __init__(self, part_number: int):
        common.check_int_value('part_number', part_number, 1, 6)
        super().__init__()
        self.setCheckable(True)
        self.setContextMenuPolicy(PySide6.QtCore.Qt.CustomContextMenu)
        self.setProperty('part-number', part_number)
        self.setText('-')

    def set_overridden_values(self, overridden_values: typing.Optional[dict]) -> None:
        self.setProperty('overridden-values', overridden_values)
        self.setText('*' if bool(overridden_values) else '-')

    def get_overridden_values(self) -> typing.Optional[dict]:
        return self.property('overridden-values')


class Dot(PySide6.QtWidgets.QRadioButton):
    def __init__(self, step_index: int):
        super().__init__('')
        self.setProperty('id', step_index)


class Parts(PySide6.QtWidgets.QWidget):
    note_on = PySide6.QtCore.Signal(int)  # Channel number is sent (range from 1 to 6 inclusive).
    step_context_requested = PySide6.QtCore.Signal()
    overridden_values_found = PySide6.QtCore.Signal(int, dict)  # Sends channel number and overridden values.

    __part_count = 6

    def __init__(self, initial_step_count: int = 16):
        common.check_int_value('initial_step_count', initial_step_count, 16, 1024)
        super().__init__()
        self.__step_count = initial_step_count
        self.__current_step_index = 0

        layout = PySide6.QtWidgets.QGridLayout()

        for part_index in range(Parts.__part_count):
            check_box = PySide6.QtWidgets.QCheckBox()
            check_box.setText(f'PART {part_index + 1}')
            check_box.setStyleSheet('QCheckBox { font: bold }')
            check_box.setChecked(True)
            layout.addWidget(check_box, part_index, 0, 1, 1, PySide6.QtCore.Qt.AlignRight)
        for part_index, step_index in itertools.product(range(Parts.__part_count), range(initial_step_count)):
            step = Step(part_index + 1)
            step.customContextMenuRequested.connect(self.step_context_requested)
            layout.addWidget(step, part_index, step_index + 1)
        for step_index in range(initial_step_count):
            dot = Dot(step_index)
            dot.clicked.connect(self.__process_dot_click)
            dot.customContextMenuRequested.connect(self.step_context_requested)
            layout.addWidget(dot, Parts.__part_count, step_index + 1, 1, 1, PySide6.QtCore.Qt.AlignCenter)
        layout.itemAtPosition(Parts.__part_count, 1).widget().setChecked(True)

        self.setLayout(layout)
        self.setSizePolicy(PySide6.QtWidgets.QSizePolicy.Policy.Maximum, PySide6.QtWidgets.QSizePolicy.Policy.Maximum)

        self.__timer = PySide6.QtCore.QTimer()
        self.__timer.timeout.connect(self.__do_step)
        self.change_tempo(60)

    def layout(self) -> PySide6.QtWidgets.QGridLayout:
        return super().layout()

    @property
    def step_count(self) -> int:
        return self.__step_count

    def step_at(self, part_number: int, step_number: int) -> Step:
        common.check_int_value('part_number', part_number, 1, 6)
        common.check_int_value('step_number', step_number, 1, self.__step_count)
        return self.layout().itemAtPosition(part_number - 1, step_number).widget()

    def resize(self, new_step_count) -> None:
        common.check_int_value('new_step_count', new_step_count, 16, 1024)
        if new_step_count == self.__step_count:
            return
        self.stop()
        if new_step_count > self.__step_count:
            for part_index, step_index in itertools.product(range(Parts.__part_count), range(self.__step_count, new_step_count)):
                step = Step(part_index + 1)
                step.customContextMenuRequested.connect(self.step_context_requested)
                self.layout().addWidget(step, part_index, step_index + 1)
            for step_index in range(self.__step_count, new_step_count):
                dot = Dot(step_index)
                dot.clicked.connect(self.__process_dot_click)
                self.layout().addWidget(dot, Parts.__part_count, step_index + 1, 1, 1, PySide6.QtCore.Qt.AlignCenter)
        else:
            for row_index, step_index in itertools.product(range(Parts.__part_count + 1), range(new_step_count, self.__step_count)):
                widget = self.layout().itemAtPosition(row_index, step_index + 1).widget()
                self.layout().removeWidget(widget)
                widget.deleteLater()
        self.__step_count = new_step_count

    @property
    def tempo(self) -> int:
        return 60000 // self.__timer.interval()

    def change_tempo(self, new_tempo: int) -> None:
        self.__timer.setInterval(60000 // new_tempo)

    def play(self) -> None:
        self.__timer.start()

    def stop(self) -> None:
        self.__timer.stop()
        self.__go_to(0)

    def __process_dot_click(self) -> None:
        self.__go_to(self.sender().property('id'))

    def __go_to(self, step_index: int) -> None:
        common.check_int_value('step_index', step_index, 0, self.__step_count - 1)
        self.__current_step_index = step_index
        self.layout().itemAtPosition(Parts.__part_count, step_index + 1).widget().setChecked(True)

    def __do_step(self) -> None:
        enabled_parts = [part_index for part_index in range(Parts.__part_count) if self.layout().itemAtPosition(part_index, 0).widget().isChecked()]
        for part_index in enabled_parts:
            step: Step = self.step_at(part_index + 1, self.__current_step_index + 1)
            overridden_values = step.get_overridden_values()
            if overridden_values:
                self.overridden_values_found.emit(part_index + 1, overridden_values)
            if step.isChecked():
                self.note_on.emit(part_index + 1)
        self.__go_to((self.__current_step_index + 1) % self.__step_count)

    def store(self) -> dict:
        stored_values = {
            'step-count': self.__step_count,
            'tempo': min(360, max(60, self.tempo)),
            'enabled-parts': [
                part_index + 1 for part_index in range(Parts.__part_count) if self.layout().itemAtPosition(part_index, 0).widget().isChecked()
            ],
            'enabled-steps': {f'part{part_index + 1}': [] for part_index in range(Parts.__part_count)},
            'overridden-controls': {f'part{part_index + 1}': {} for part_index in range(Parts.__part_count)},
        }
        for part_index, step_index in itertools.product(range(Parts.__part_count), range(self.__step_count)):
            step: Step = self.step_at(part_index + 1, step_index + 1)
            if step.isChecked():
                stored_values['enabled-steps'][f'part{part_index + 1}'].append(step_index + 1)
            overridden_values = step.get_overridden_values()
            if overridden_values:
                stored_values['overridden-controls'][f'part{part_index + 1}'][step_index + 1] = overridden_values
        stored_values['enabled-steps'] = {k: v for k, v in stored_values['enabled-steps'].items() if v}
        stored_values['overridden-controls'] = {k: v for k, v in stored_values['overridden-controls'].items() if v}
        return stored_values

    @staticmethod
    def restore(stored_values: typing.Optional[dict]):  # -> Parts:
        if 'step-count' in stored_values:
            parts = Parts(stored_values['step-count'])
        else:
            return None
        parts.__timer.setInterval(60000 // stored_values.get('tempo', 60))
        enabled_parts = stored_values.get('enabled-parts', list(range(1, 6 + 1)))
        for part_index in range(Parts.__part_count):
            parts.layout().itemAtPosition(part_index, 0).widget().setChecked(part_index + 1 in enabled_parts)
        if 'enabled-steps' not in stored_values:
            return parts
        for part_index in range(Parts.__part_count):
            part_name = f'part{part_index + 1}'
            if part_name not in stored_values['enabled-steps']:
                continue
            for step_number in filter(lambda x: x <= stored_values['step-count'], stored_values['enabled-steps'][part_name]):
                parts.step_at(part_index + 1, step_number).setChecked(True)
            overridden_controls = stored_values.get('overridden-controls', {}).get(part_name, {})
            for step_number, overridden_controls in filter(lambda x: int(x[0]) <= stored_values['step-count'], overridden_controls.items()):
                parts.step_at(part_index + 1, int(step_number)).set_overridden_values(overridden_controls)

        return parts

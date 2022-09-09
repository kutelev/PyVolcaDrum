import itertools
import typing

import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

import modules.common

__all__ = ['Parts']


class Step(PySide6.QtWidgets.QToolButton):
    def __init__(self, part_number: int, is_strong: bool):
        modules.common.check_int_value('part_number', part_number, 1, 6)
        super().__init__()
        self.setCheckable(True)
        self.setContextMenuPolicy(PySide6.QtCore.Qt.CustomContextMenu)
        self.setProperty('part-number', part_number)
        self.setText('-')
        self.__is_strong = is_strong

    def mark_as_strong(self, is_strong: bool) -> None:
        modules.common.check_bool_value('is_strong', is_strong)
        self.__is_strong = is_strong

    def set_overridden_values(self, overridden_values: typing.Optional[dict]) -> None:
        self.setProperty('overridden-values', overridden_values)
        self.setText('*' if bool(overridden_values) else '-')

    def get_overridden_values(self) -> typing.Optional[dict]:
        return self.property('overridden-values')

    def paintEvent(self, event: PySide6.QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        if not self.__is_strong:
            return
        painter = PySide6.QtGui.QPainter(self)
        painter.setPen(PySide6.QtCore.Qt.GlobalColor.darkRed)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)


class Dot(PySide6.QtWidgets.QRadioButton):
    step_insertion_requested = PySide6.QtCore.Signal(int, int)  # Step index (starts from zero) and step count are sent.
    step_deletion_requested = PySide6.QtCore.Signal(int, int)  # Step index (starts from zero) and step count are sent.

    def __init__(self, step_number: int):
        modules.common.check_int_value('step_number', step_number, 1)
        super().__init__('')
        self.setContextMenuPolicy(PySide6.QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__show_context_menu)
        self.setProperty('step-number', step_number)

    def __show_context_menu(self, position: PySide6.QtCore.QPoint) -> None:
        insert_steps_before_action = PySide6.QtGui.QAction('Insert steps (before)')
        insert_steps_before_action.triggered.connect(self.__process_step_count_change)
        insert_steps_after_action = PySide6.QtGui.QAction('Insert steps (after)')
        insert_steps_after_action.triggered.connect(self.__process_step_count_change)
        delete_steps_action = PySide6.QtGui.QAction('Delete steps')
        delete_steps_action.triggered.connect(self.__process_step_count_change)
        menu = PySide6.QtWidgets.QMenu()
        menu.addAction(insert_steps_before_action)
        menu.addAction(insert_steps_after_action)
        menu.addAction(delete_steps_action)
        menu.exec(self.mapToGlobal(position))

    def __process_step_count_change(self) -> None:
        input_dialog = PySide6.QtWidgets.QInputDialog()
        input_dialog.setWindowTitle('PyVolcaDrum: enter step count')
        input_dialog.setLabelText('Enter step count:')
        input_dialog.setInputMode(PySide6.QtWidgets.QInputDialog.InputMode.IntInput)
        input_dialog.setIntRange(1, 128)
        input_dialog.setFixedSize(input_dialog.minimumSizeHint())
        if input_dialog.exec() != PySide6.QtWidgets.QDialog.Accepted:
            return

        action: PySide6.QtGui.QAction = self.sender()
        if action.text() == 'Insert steps (before)':
            self.step_insertion_requested.emit(self.property('step-number') - 1, input_dialog.intValue())
        elif action.text() == 'Insert steps (after)':
            self.step_insertion_requested.emit(self.property('step-number'), input_dialog.intValue())
        elif action.text() == 'Delete steps':
            self.step_deletion_requested.emit(self.property('step-number'), input_dialog.intValue())


class Parts(PySide6.QtWidgets.QWidget):
    note_on = PySide6.QtCore.Signal(int)  # Channel number is sent (range from 1 to 6 inclusive).
    step_context_requested = PySide6.QtCore.Signal()
    overridden_values_found = PySide6.QtCore.Signal(int, dict)  # Sends channel number and overridden values.
    step_count_changed = PySide6.QtCore.Signal(int)

    __part_count = 6
    __part_numbers = list(range(1, __part_count + 1))
    __min_step_count = 16
    __max_step_count = 1024

    def __init__(self, initial_step_count: int = __min_step_count, initial_bpm: int = 4):
        modules.common.check_int_value('initial_step_count', initial_step_count, Parts.__min_step_count, Parts.__max_step_count)
        modules.common.check_int_value('initial_bpm', initial_bpm, 2, Parts.__min_step_count)

        super().__init__()

        self.__step_count = initial_step_count
        self.__bpm = initial_bpm
        self.__current_step_number = 1

        layout = PySide6.QtWidgets.QGridLayout()

        for part_number in Parts.__part_numbers:
            check_box = PySide6.QtWidgets.QCheckBox()
            check_box.setText(f'PART {part_number}')
            check_box.setStyleSheet('QCheckBox { font: bold }')
            check_box.setChecked(True)
            layout.addWidget(check_box, part_number - 1, 0, 1, 1, PySide6.QtCore.Qt.AlignRight)
        for part_number, step_number in itertools.product(Parts.__part_numbers, range(1, initial_step_count + 1)):
            layout.addWidget(self.__create_step(part_number, ((step_number - 1) % self.__bpm) == 0), part_number - 1, step_number)
        for step_number in range(1, initial_step_count + 1):
            layout.addWidget(self.__create_dot(step_number), Parts.__part_count, step_number, 1, 1, PySide6.QtCore.Qt.AlignCenter)
        layout.itemAtPosition(Parts.__part_count, 1).widget().setChecked(True)

        self.setLayout(layout)
        self.setSizePolicy(PySide6.QtWidgets.QSizePolicy.Policy.Maximum, PySide6.QtWidgets.QSizePolicy.Policy.Maximum)

        self.__timer = PySide6.QtCore.QTimer()
        self.__timer.timeout.connect(self.__do_step)
        self.change_tempo(60)

    def __create_step(self, part_number: int, is_strong: bool) -> Step:
        step = Step(part_number, is_strong)
        step.customContextMenuRequested.connect(self.step_context_requested)
        return step

    def __create_dot(self, step_number: int) -> Dot:
        dot = Dot(step_number)
        dot.clicked.connect(self.__process_dot_click)
        dot.step_insertion_requested.connect(self.__insert_steps)
        dot.step_deletion_requested.connect(self.__delete_steps)
        return dot

    def layout(self) -> PySide6.QtWidgets.QGridLayout:
        return super().layout()

    @property
    def step_count(self) -> int:
        return self.__step_count

    @property
    def bpm(self) -> int:
        return self.__bpm

    def step_at(self, part_number: int, step_number: int) -> Step:
        modules.common.check_int_value('part_number', part_number, 1, Parts.__part_count)
        modules.common.check_int_value('step_number', step_number, 1, self.__step_count)
        return self.layout().itemAtPosition(part_number - 1, step_number).widget()

    def change_step_count(self, new_step_count: int, new_bpm: int) -> None:
        modules.common.check_int_value('new_step_count', new_step_count, Parts.__min_step_count, Parts.__max_step_count)
        modules.common.check_int_value('new_bpm', new_bpm, 2, Parts.__min_step_count)
        if new_step_count == self.__step_count and new_bpm == self.__bpm:
            return
        step_count_change_requested = new_step_count != self.__step_count
        if step_count_change_requested:
            self.stop()
        if new_step_count > self.__step_count:
            for part_number, step_number in itertools.product(Parts.__part_numbers, range(self.__step_count + 1, new_step_count + 1)):
                self.layout().addWidget(self.__create_step(part_number, ((step_number - 1) % self.__bpm) == 0), part_number - 1, step_number)
            for step_number in range(self.__step_count + 1, new_step_count + 1):
                self.layout().addWidget(self.__create_dot(step_number), Parts.__part_count, step_number, 1, 1, PySide6.QtCore.Qt.AlignCenter)
        elif new_step_count < self.__step_count:
            for row_index, step_number in itertools.product(range(Parts.__part_count + 1), range(new_step_count + 1, self.__step_count + 1)):
                widget = self.layout().itemAtPosition(row_index, step_number).widget()
                self.layout().removeWidget(widget)
                widget.deleteLater()
        self.__step_count = new_step_count
        self.__bpm = new_bpm
        for part_number, step_number in itertools.product(Parts.__part_numbers, range(1, new_step_count + 1)):
            step = self.step_at(part_number, step_number)
            step.mark_as_strong(((step_number - 1) % new_bpm) == 0)
        self.repaint()
        if step_count_change_requested:
            self.step_count_changed.emit(new_step_count)

    def __move_steps(self, position: int, distance: int) -> None:
        src_step_range = list(range(position, self.__step_count + (abs(distance) if distance < 0 else 0) + 1))
        if distance > 0:
            src_step_range.reverse()

        def move_step(src_step_number: typing.Optional[int], dst_step_number: typing.Optional[int]) -> None:
            src_step = self.step_at(part_number, src_step_number) if 1 <= src_step_number <= self.__step_count else None
            dst_step = self.step_at(part_number, dst_step_number) if 1 <= dst_step_number <= self.__step_count else None
            if dst_step is not None:
                dst_step.setChecked(src_step.isChecked() if src_step is not None else False)
                dst_step.set_overridden_values(src_step.get_overridden_values() if src_step is not None else None)
            if src_step is not None:
                src_step.setChecked(False)
                src_step.set_overridden_values(None)

        for part_number, step_number in itertools.product(Parts.__part_numbers, src_step_range):
            move_step(step_number, step_number + distance)

    def __insert_steps(self, position: int, steps_to_insert: int) -> None:
        self.change_step_count(self.step_count + steps_to_insert, self.__bpm)
        self.__move_steps(position + 1, steps_to_insert)

    def __delete_steps(self, position: int, steps_to_delete: int) -> None:
        self.__move_steps(position + steps_to_delete, -steps_to_delete)
        self.change_step_count(self.step_count - steps_to_delete, self.__bpm)

    @property
    def tempo(self) -> int:
        return 60000 // self.__timer.interval()

    def change_tempo(self, new_tempo: int) -> None:
        self.__timer.setInterval(60000 // new_tempo)

    def play(self) -> None:
        self.__timer.start()

    def stop(self) -> None:
        self.__timer.stop()
        self.__go_to(1)

    def enable_current_step(self, part_number: int) -> None:
        modules.common.check_int_value('part_number', part_number, 1, Parts.__part_count)
        self.note_on.emit(part_number)
        if not self.__timer.isActive():
            return
        insert_to_the_previous_step = self.__timer.remainingTime() > self.__timer.interval() / 2
        if insert_to_the_previous_step:
            step_number = self.__step_count if self.__current_step_number == 1 else self.__current_step_number - 1
        else:
            step_number = self.__current_step_number
        self.step_at(part_number, step_number).setChecked(True)

    def __process_dot_click(self) -> None:
        self.__go_to(self.sender().property('step-number'))

    def __go_to(self, step_number: int) -> None:
        modules.common.check_int_value('step_number', step_number, 1, self.__step_count)
        self.__current_step_number = step_number
        self.layout().itemAtPosition(Parts.__part_count, step_number).widget().setChecked(True)

    def __do_step(self) -> None:
        enabled_parts = [
            part_number for part_number in Parts.__part_numbers if self.layout().itemAtPosition(part_number - 1, 0).widget().isChecked()
        ]
        for part_number in enabled_parts:
            step: Step = self.step_at(part_number, self.__current_step_number)
            overridden_values = step.get_overridden_values()
            if overridden_values:
                self.overridden_values_found.emit(part_number, overridden_values)
            if step.isChecked():
                self.note_on.emit(part_number)
        self.__go_to(1 if self.__current_step_number == self.__step_count else self.__current_step_number + 1)

    def store(self) -> dict:
        stored_values = {
            'step-count': self.__step_count,
            'beats-per-measure': self.__bpm,
            'tempo': min(360, max(60, self.tempo)),
            'enabled-parts': [
                part_number for part_number in Parts.__part_numbers if self.layout().itemAtPosition(part_number - 1, 0).widget().isChecked()
            ],
            'enabled-steps': {f'part{part_number}': [] for part_number in Parts.__part_numbers},
            'overridden-controls': {f'part{part_number}': {} for part_number in Parts.__part_numbers},
        }
        for part_number, step_number in itertools.product(Parts.__part_numbers, range(1, self.__step_count + 1)):
            step: Step = self.step_at(part_number, step_number)
            if step.isChecked():
                stored_values['enabled-steps'][f'part{part_number}'].append(step_number)
            overridden_values = step.get_overridden_values()
            if overridden_values:
                stored_values['overridden-controls'][f'part{part_number}'][step_number] = overridden_values
        stored_values['enabled-steps'] = {k: v for k, v in stored_values['enabled-steps'].items() if v}
        stored_values['overridden-controls'] = {k: v for k, v in stored_values['overridden-controls'].items() if v}
        for k in ('enabled-steps', 'overridden-controls'):
            if len(stored_values[k]) == 0:
                del stored_values[k]
        return stored_values

    @staticmethod
    def restore(stored_values: typing.Optional[dict]):  # -> Parts:
        if 'step-count' in stored_values:
            parts = Parts(stored_values['step-count'], stored_values.get('beats-per-measure', 4))
        else:
            return None
        parts.__timer.setInterval(60000 // stored_values.get('tempo', 60))
        enabled_parts = stored_values.get('enabled-parts', list(Parts.__part_numbers))
        for part_number in Parts.__part_numbers:
            parts.layout().itemAtPosition(part_number - 1, 0).widget().setChecked(part_number in enabled_parts)
        for part_number in Parts.__part_numbers:
            part_name = f'part{part_number}'
            enabled_steps = stored_values.get('enabled-steps', {}).get(part_name, [])
            for step_number in filter(lambda x: x <= stored_values['step-count'], enabled_steps):
                parts.step_at(part_number, step_number).setChecked(True)
            overridden_controls = stored_values.get('overridden-controls', {}).get(part_name, {})
            for step_number, overridden_controls in filter(lambda x: int(x[0]) <= stored_values['step-count'], overridden_controls.items()):
                parts.step_at(part_number, int(step_number)).set_overridden_values(overridden_controls)

        return parts

import os
import typing

import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

import common


class Knob(PySide6.QtWidgets.QDial):
    def __init__(self, control_number: int, control_name: str, default_value: int):
        super().__init__()
        self.setProperty('control-number', control_number)
        self.setProperty('control-name', control_name)
        self.setProperty('default-value', default_value)
        self.setWrapping(False)
        self.setRange(0, 127)
        self.setNotchesVisible(True)
        self.setFixedSize(self.minimumSizeHint())

    def paintEvent(self, event: PySide6.QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = PySide6.QtGui.QPainter(self)
        font_metrics = painter.fontMetrics()
        text = str(self.value())
        text_size = font_metrics.size(0, text, 0)
        painter.drawText((self.width() - text_size.width()) // 2, (self.height() + text_size.height() // 2) // 2, text)


class Selector(PySide6.QtWidgets.QWidget):
    valueChanged = PySide6.QtCore.Signal(int)

    def __init__(self, control_number: int, control_name: str):
        super().__init__()
        self.setLayout(PySide6.QtWidgets.QGridLayout())
        self.setProperty('control-number', control_number)
        self.setProperty('control-name', control_name)
        self.setProperty('default-value', 0)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), PySide6.QtWidgets.QSizePolicy.Policy.Maximum)
        self._value = 0

    def _layout(self) -> PySide6.QtWidgets.QGridLayout:
        return super().layout()

    def _add_row_of_tool_buttons(self, name: str, row: int, names: typing.List[str], resource_type: str) -> \
            PySide6.QtWidgets.QButtonGroup:
        self.layout().addWidget(PySide6.QtWidgets.QLabel(f'<b>{name}</b>'), row, 0, 1, 1, PySide6.QtCore.Qt.AlignRight)
        button_group = PySide6.QtWidgets.QButtonGroup(self)
        for i, parameter_name in enumerate(names):
            icon_name = parameter_name.lower().replace(' ', '-')
            icon_path = os.path.join(common.resources_directory_path, resource_type, f'{icon_name}.svg')
            icon = PySide6.QtGui.QIcon(icon_path)
            button = PySide6.QtWidgets.QToolButton()
            button.setIcon(icon)
            button.setCheckable(True)
            button.setChecked(i == 0)
            button.setToolTip(parameter_name)
            button_group.addButton(button)
            button_group.setId(button, i)
            self.layout().addWidget(button, row, 1 + i)
        button_group.buttonToggled.connect(self._process_control_change)
        return button_group

    def _process_control_change(self, checked: bool) -> None:
        raise NotImplemented

    def setValue(self, value) -> None:  # noqa: Qt notation is used intentionally.
        raise NotImplemented

    def value(self) -> int:
        return self._value


class SelectControl(Selector):
    def __init__(self, control_number: int):
        super().__init__(control_number, 'select')

        sound_sources = [
            'Sine wave',
            'Sawtooth wave',
            'High pass filtered noise',
            'Low pass filtered noise',
            'Band pass filtered noise',
        ]

        pitch_modulators = [
            'Rise-fall',
            'Oscillate',
            'Random',
        ]

        amplitude_envelope_generators = [
            'Linear attack-release',
            'Exponential attack-release',
            'Multi-peak attack-release',
        ]

        self.__sound_source_selector = self._add_row_of_tool_buttons('SRC', 0, sound_sources, 'sound-source')
        self.__pitch_modulator_selector = self._add_row_of_tool_buttons('MOD', 1, pitch_modulators, 'pitch-modulator')
        self.__amplitude_envelope_generator_selector = self._add_row_of_tool_buttons('EG', 2, amplitude_envelope_generators, 'amplitude-envelope-generator')

    @property
    def __combination_index(self) -> int:
        return self.__sound_source_selector.checkedId() * 9 + \
               self.__pitch_modulator_selector.checkedId() * 3 + \
               self.__amplitude_envelope_generator_selector.checkedId()

    @property
    def __max_combination_count_index(self) -> int:
        combination_count = 5 * 3 * 3  # (5 sound source types) X (3 pitch modulator types) X (3 amplitude envelope generator types)
        return combination_count - 1

    @property
    def __normalized_combination_index(self) -> int:
        return (127 * self.__combination_index + self.__max_combination_count_index - 1) // self.__max_combination_count_index

    def _process_control_change(self, button: typing.Optional[PySide6.QtWidgets.QPushButton], checked: bool) -> None:
        if not checked:
            return
        self.setValue(self.__normalized_combination_index)

    def setValue(self, value) -> None:  # noqa: Qt notation is used intentionally.
        if value == self.value():
            return
        combination_index = value * self.__max_combination_count_index // 127
        amplitude_envelope_generator_type = combination_index % 3
        pitch_modulator_type = (combination_index // 3) % 3
        sound_source_type = (combination_index // 9) % 5
        for button_group in [self.__sound_source_selector, self.__pitch_modulator_selector, self.__amplitude_envelope_generator_selector]:
            button_group.blockSignals(True)
        self.__sound_source_selector.button(sound_source_type).setChecked(True)
        self.__pitch_modulator_selector.button(pitch_modulator_type).setChecked(True)
        self.__amplitude_envelope_generator_selector.button(amplitude_envelope_generator_type).setChecked(True)
        for button_group in [self.__sound_source_selector, self.__pitch_modulator_selector, self.__amplitude_envelope_generator_selector]:
            button_group.blockSignals(False)
        self._value = value
        self.valueChanged.emit(value)


class ResonatorModelControl(Selector):
    def __init__(self, control_number: int):
        super().__init__(control_number, 'resonator-model')
        self.__resonator_model_selector = self._add_row_of_tool_buttons('RES', 0, ['Tube', 'String'], 'waveguide-resonator')

    def _process_control_change(self, button: typing.Optional[PySide6.QtWidgets.QPushButton], checked: bool) -> None:
        if not checked:
            return
        self.setValue(self.__resonator_model_selector.checkedId() * 127)

    def setValue(self, value) -> None:  # noqa: Qt notation is used intentionally.
        if value == self.value():
            return
        self.__resonator_model_selector.blockSignals(True)
        self.__resonator_model_selector.button(value // 127).setChecked(True)
        self.__resonator_model_selector.blockSignals(False)
        self._value = value
        self.valueChanged.emit(value)


class GroupOfControls(PySide6.QtWidgets.QGroupBox):
    control_changed = PySide6.QtCore.Signal(int, int)

    def __init__(self, title: str):
        super().__init__()
        self.setTitle(title)
        self.setStyleSheet('QGroupBox { font: bold }')
        self._controls: typing.List[typing.Union[Knob, Selector]] = []

    def add_knob(self, layout: PySide6.QtWidgets.QGridLayout, title: str, control_number: int, control_name: str, default_value: int, row: int, col: int) -> \
            Knob:
        layout.addWidget(PySide6.QtWidgets.QLabel(f'<b>{title}</b>'), row, col, 1, 1, PySide6.QtCore.Qt.AlignCenter | PySide6.QtCore.Qt.AlignBottom)
        knob = Knob(control_number, control_name, default_value)
        knob.valueChanged.connect(self.process_control_change)
        layout.addWidget(knob, row + 1, col, 1, 1, PySide6.QtCore.Qt.AlignCenter | PySide6.QtCore.Qt.AlignTop)
        return knob

    @staticmethod
    def restore_control(control: typing.Union[PySide6.QtWidgets.QDial, Selector], value: int, force: bool) -> None:
        if control.value() != value:
            control.setValue(value)
        elif force:
            # Force sending signal to the device even if local value is up-to-date.
            # This is only required when settings are restored from a configuration file (on application start).
            control.valueChanged.emit(control.value())

    def process_control_change(self) -> None:
        sender = self.sender()
        self.control_changed.emit(sender.property('control-number'), sender.value())

    def store(self) -> dict:
        return {control.property('control-name'): control.value() for control in self._controls}

    def restore(self, stored_values: typing.Optional[dict], force: bool = True) -> None:
        for control in self._controls:
            self.restore_control(control, stored_values.get(control.property('control-name'), control.property('default-value')), force)


class LayerControls(GroupOfControls):
    layer_toggled = PySide6.QtCore.Signal()

    def __init__(self, part_number: int, layer_number: int):
        common.check_int_value('part_number', part_number, 1, 6)
        common.check_int_value('layer_number', layer_number, 1, 2)
        super().__init__(f'LAYER {layer_number}')
        self.layer_number = layer_number
        self.part_number = part_number

        knobs_layout = PySide6.QtWidgets.QGridLayout()
        select_control = SelectControl(14 + layer_number - 1)  # SELECT1 or SELECT2
        self._controls = [
            select_control,  # SELECT1 or SELECT2
            # Row 0
            self.add_knob(knobs_layout, 'LEVEL', 17 + layer_number - 1, 'level', 64, 0, 0),  # LEVEL1 or LEVEL2
            self.add_knob(knobs_layout, 'AMOUNT', 29 + layer_number - 1, 'modulation-amount', 64, 0, 1),  # MODAMT1 or MODAMT2
            self.add_knob(knobs_layout, 'RATE', 46 + layer_number - 1, 'modulation-rate', 64, 0, 2),  # MODRATE1 or MODRATE2
        ]
        if layer_number == 1:
            self._controls.extend([
                # Row 0
                self.add_knob(knobs_layout, 'PAN', 10, 'left-right-pan', 64, 0, 3),  # PAN
            ])
        self._controls.extend([
            # Row 2
            self.add_knob(knobs_layout, 'PITCH', 26 + layer_number - 1, 'pitch', 32, 2, 0),  # PITCH1 or PITCH2
            self.add_knob(knobs_layout, 'ATTACK', 20 + layer_number - 1, 'envelope-generator-attack', 64, 2, 1),  # EGATT1 or EGATT2
            self.add_knob(knobs_layout, 'RELEASE', 23 + layer_number - 1, 'envelope-generator-release', 64, 2, 2),  # EGREL1 or EGREL2
        ])

        if layer_number == 1:
            self._controls.extend([
                # Row 2
                self.add_knob(knobs_layout, 'SEND', 103, 'send-amount', 0, 2, 3),  # SEND
                # Row 4
                self.add_knob(knobs_layout, 'BIT', 49, 'bit-reduction-amount', 0, 4, 0),  # BIT RED
                self.add_knob(knobs_layout, 'FLD', 50, 'wave-folder-amount', 0, 4, 1),  # FOLD
                self.add_knob(knobs_layout, 'DRV', 51, 'overdrive-gain', 0, 4, 2),  # DRIVE
                self.add_knob(knobs_layout, 'GAN', 52, 'pre-mix-gain-adjustment', 127, 4, 3),  # DRY GAIN
            ])

        select_control.valueChanged.connect(self.process_control_change)
        self.toggled.connect(self.layer_toggled)

        layout = PySide6.QtWidgets.QVBoxLayout()
        layout.addWidget(select_control)
        layout.addLayout(knobs_layout)
        self.setLayout(layout)

    def sync(self, other) -> None:
        self.restore(other.store(), False)

    def restore(self, stored_values: typing.Optional[dict], force: bool = True) -> None:
        super().restore(stored_values, force)


class PartControls(PySide6.QtWidgets.QGroupBox):
    control_changed = PySide6.QtCore.Signal(int, int)

    def __init__(self, part_number: int):
        common.check_int_value('part_number', part_number, 1, 6)
        super().__init__()
        self.setTitle(f'PART {part_number}')
        self.setStyleSheet('QGroupBox { font: bold }')
        self.part_number = part_number
        layout = PySide6.QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.layer_controls = [LayerControls(part_number, i) for i in range(1, 2 + 1)]
        for i, layer_control in enumerate(self.layer_controls):
            layer_control.setCheckable(i == 1)
            layer_control.setChecked(i == 0)
            layout.addWidget(layer_control)
            layer_control.control_changed.connect(self.process_control_change)
        self.layer_controls[1].layer_toggled.connect(self.process_layer_toggle)

    def process_control_change(self, control: int, value: int) -> None:
        self.control_changed.emit(control, value)
        if self.sender() is self.layer_controls[0] and not self.layer_controls[1].isChecked():
            self.layer_controls[1].sync(self.layer_controls[0])

    def process_layer_toggle(self) -> None:
        self.layer_controls[1].sync(self.layer_controls[0])

    def store(self) -> dict:
        stored_values = {'layer1': self.layer_controls[0].store()}
        if self.layer_controls[1].isChecked():
            stored_values['layer2'] = self.layer_controls[1].store()
        return stored_values

    def restore(self, stored_values) -> None:
        self.layer_controls[1].blockSignals(True)
        self.layer_controls[1].setChecked(True)
        self.layer_controls[1].blockSignals(False)
        self.layer_controls[0].restore(stored_values.get('layer1', {}))
        self.layer_controls[1].restore(stored_values.get('layer2' if 'layer2' in stored_values else 'layer1', {}))
        self.layer_controls[1].setChecked('layer2' in stored_values)


class WaveguideResonatorControls(GroupOfControls):
    def __init__(self):
        super().__init__('WAVE GUIDE')
        knobs_layout = PySide6.QtWidgets.QGridLayout()
        layout = PySide6.QtWidgets.QVBoxLayout()
        resonator_model_control = ResonatorModelControl(116)  # WAVEGUIDE MODEL
        self._controls = [
            resonator_model_control,   # WAVEGUIDE MODEL
            self.add_knob(knobs_layout, 'DECAY', 117, 'decay-time', 64, 0, 0),  # DECAY
            self.add_knob(knobs_layout, 'BODY', 118, 'timbral-character', 64, 2, 0),  # BODY
            self.add_knob(knobs_layout, 'TUNE', 119, 'pitch-tuning', 64, 4, 0),  # TUNE
        ]
        resonator_model_control.valueChanged.connect(self.process_control_change)

        layout.addWidget(resonator_model_control)
        layout.addLayout(knobs_layout)
        layout.addItem(PySide6.QtWidgets.QSpacerItem(0, 0, PySide6.QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                                     PySide6.QtWidgets.QSizePolicy.Policy.MinimumExpanding))
        self.setLayout(layout)

        self.setFixedWidth(self.minimumSizeHint().width())
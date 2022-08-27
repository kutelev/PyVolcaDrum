import enum
import json
import os
import sys
import typing

import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets
import mido

root_directory_path = os.path.abspath(os.path.dirname(os.path.relpath(__file__)))
resources_directory_path = os.path.join(root_directory_path, 'resources')


def check_int_value(name: str, value: int, min_value: int, max_value: int) -> None:
    if not isinstance(value, int):
        raise TypeError(f'{name} must be of type int')
    if not min_value <= value <= max_value:
        raise TypeError(f'{name} must in the range from {min_value} to {max_value}')


class LayerControl(PySide6.QtWidgets.QGroupBox):
    control_changed = PySide6.QtCore.Signal(int, int)
    layer_toggled = PySide6.QtCore.Signal()

    class SoundSourceTypes(enum.IntEnum):
        SINE_WAVE = 0
        SAWTOOTH_WAVE = 1
        HIGH_PASS_FILTERED_NOISE = 2
        LOW_PASS_FILTERED_NOISE = 3
        BAND_PASS_FILTERED_NOISE = 4

    class PitchModulatorTypes(enum.IntEnum):
        RISE_FALL = 0
        OSCILLATE = 1
        RANDOM = 2

    class AmplitudeEnvelopeGeneratorTypes(enum.IntEnum):
        LINEAR_ATTACK_RELEASE = 0
        EXPONENTIAL_ATTACK_RELEASE = 1
        MULTI_PEAK_ATTACK_RELEASE = 2

    sound_source_names = {
        SoundSourceTypes.SINE_WAVE: 'Sine wave',
        SoundSourceTypes.SAWTOOTH_WAVE: 'Sawtooth wave',
        SoundSourceTypes.HIGH_PASS_FILTERED_NOISE: 'High pass filtered noise',
        SoundSourceTypes.LOW_PASS_FILTERED_NOISE: 'Low pass filtered noise',
        SoundSourceTypes.BAND_PASS_FILTERED_NOISE: 'Band pass filtered noise',
    }

    pitch_modulator_names = {
        PitchModulatorTypes.RISE_FALL: 'Rise-fall',
        PitchModulatorTypes.OSCILLATE: 'Oscillate',
        PitchModulatorTypes.RANDOM: 'Random',
    }

    amplitude_envelope_generator_names = {
        AmplitudeEnvelopeGeneratorTypes.LINEAR_ATTACK_RELEASE: 'Linear attack-release',
        AmplitudeEnvelopeGeneratorTypes.EXPONENTIAL_ATTACK_RELEASE: 'Exponential attack-release',
        AmplitudeEnvelopeGeneratorTypes.MULTI_PEAK_ATTACK_RELEASE: 'Multi-peak attack-release',
    }

    def __init__(self, part_number: int, layer_numer: int):
        check_int_value('part_number', part_number, 1, 6)
        check_int_value('layer_numer', layer_numer, 1, 2)
        super().__init__()
        self.setTitle(f'Layer {layer_numer}')
        self.layer_numer = layer_numer
        self.part_number = part_number
        combination_layout = PySide6.QtWidgets.QGridLayout()
        knobs_layout = PySide6.QtWidgets.QGridLayout()
        layout = PySide6.QtWidgets.QVBoxLayout()
        layout.addLayout(combination_layout)
        layout.addLayout(knobs_layout)
        self.setLayout(layout)

        self.sound_sources_button_group = self.add_row_of_parameters(combination_layout, 'SRC', 0, LayerControl.sound_source_names, 'sound-sources')
        self.pitch_modulators_button_group = self.add_row_of_parameters(combination_layout, 'MOD', 1, LayerControl.pitch_modulator_names, 'pitch-modulators')
        self.amplitude_envelope_generators_button_group = \
            self.add_row_of_parameters(combination_layout, 'EG', 2, LayerControl.amplitude_envelope_generator_names, 'amplitude-envelope-generators')

        self.level_control = self.add_knob(knobs_layout, 'LEVEL', 17, 0, 0)
        self.modulation_amount_control = self.add_knob(knobs_layout, 'AMOUNT', 29, 0, 1)
        knobs_layout.addWidget(PySide6.QtWidgets.QLabel(f'<b>MOD</b>'), 0, 2, 2, 1, PySide6.QtCore.Qt.AlignCenter | PySide6.QtCore.Qt.AlignVCenter)
        self.modulation_rate_control = self.add_knob(knobs_layout, 'RATE', 46, 0, 3)

        self.pitch_control = self.add_knob(knobs_layout, 'PITCH', 26, 2, 0)
        self.envelope_generator_attack_control = self.add_knob(knobs_layout, 'ATTACK', 20, 2, 1)
        knobs_layout.addWidget(PySide6.QtWidgets.QLabel(f'<b>EG</b>'), 2, 2, 2, 1, PySide6.QtCore.Qt.AlignCenter | PySide6.QtCore.Qt.AlignVCenter)
        self.envelope_generator_release_control = self.add_knob(knobs_layout, 'RELEASE', 23, 2, 3)

        self.toggled.connect(self.layer_toggled)

    def add_row_of_parameters(self, layout: PySide6.QtWidgets.QGridLayout, name: str, row: int, names: typing.Dict[enum.IntEnum, str], resource_type: str) -> \
            PySide6.QtWidgets.QButtonGroup:
        layout.addWidget(PySide6.QtWidgets.QLabel(f'<b>{name}</b>'), row, 0, 1, 1, PySide6.QtCore.Qt.AlignRight)
        button_group = PySide6.QtWidgets.QButtonGroup(self)
        for i, parameter_name in enumerate(names.values()):
            icon_name = parameter_name.lower().replace(" ", "-")
            icon_path = os.path.join(resources_directory_path, resource_type, f'{icon_name}.svg')
            icon = PySide6.QtGui.QIcon(icon_path)
            button = PySide6.QtWidgets.QToolButton()
            button.setIcon(icon)
            button.setCheckable(True)
            button.setChecked(i == 0)
            button.setToolTip(parameter_name)
            button_group.addButton(button)
            button_group.setId(button, i)
            layout.addWidget(button, row, 1 + i)
        button_group.buttonToggled.connect(self.process_combination_change)
        return button_group

    def add_knob(self, layout: PySide6.QtWidgets.QGridLayout, name: str, control: int, row: int, col: int) -> PySide6.QtWidgets.QDial:
        layout.addWidget(PySide6.QtWidgets.QLabel(f'<b>{name}</b>'), row, col, 1, 1, PySide6.QtCore.Qt.AlignCenter | PySide6.QtCore.Qt.AlignBottom)
        knob = PySide6.QtWidgets.QDial()
        knob.setWrapping(False)
        knob.setRange(0, 127)
        knob.setNotchesVisible(True)
        knob.setProperty("control", control)
        knob.valueChanged.connect(self.process_control_change)
        layout.addWidget(knob, row + 1, col, 1, 1, PySide6.QtCore.Qt.AlignCenter | PySide6.QtCore.Qt.AlignTop)
        return knob

    @property
    def combination_index(self) -> int:
        return self.amplitude_envelope_generators_button_group.checkedId() + \
               self.pitch_modulators_button_group.checkedId() * 3 + \
               self.sound_sources_button_group.checkedId() * 9

    @property
    def normalized_combination_index(self) -> int:
        combination_count = 5 * 3 * 3  # (5 sound source types) X (3 pitch modulator types) X (3 amplitude envelope generator types)
        max_combination_count_index = combination_count - 1
        return (127 * self.combination_index + max_combination_count_index - 1) // max_combination_count_index

    def process_combination_change(self, button: typing.Optional[PySide6.QtWidgets.QPushButton], checked: bool) -> None:
        if not checked:
            return
        self.control_changed.emit(14 + self.layer_numer - 1, self.normalized_combination_index)

    def process_control_change(self) -> None:
        sender = self.sender()
        self.control_changed.emit(sender.property("control") + self.layer_numer - 1, sender.value())

    def set_combination(self, combination_index: int) -> None:
        amplitude_envelope_generator_type = combination_index % 3
        pitch_modulator_type = (combination_index // 3) % 3
        sound_source_type = (combination_index // 9) % 5
        self.sound_sources_button_group.button(sound_source_type).setChecked(True)
        self.pitch_modulators_button_group.button(pitch_modulator_type).setChecked(True)
        self.amplitude_envelope_generators_button_group.button(amplitude_envelope_generator_type).setChecked(True)
        self.process_combination_change(None, True)

    def sync(self, other) -> None:
        self.sound_sources_button_group.button(other.sound_sources_button_group.checkedId()).setChecked(True)
        self.pitch_modulators_button_group.button(other.pitch_modulators_button_group.checkedId()).setChecked(True)
        self.amplitude_envelope_generators_button_group.button(other.amplitude_envelope_generators_button_group.checkedId()).setChecked(True)
        self.level_control.setValue(other.level_control.value())
        self.modulation_amount_control.setValue(other.modulation_amount_control.value())
        self.modulation_rate_control.setValue(other.modulation_rate_control.value())
        self.pitch_control.setValue(other.pitch_control.value())
        self.envelope_generator_attack_control.setValue(other.envelope_generator_attack_control.value())
        self.envelope_generator_release_control.setValue(other.envelope_generator_release_control.value())

    def store(self) -> dict:
        return {
            'combination-index': self.combination_index,
            'level': self.level_control.value(),
            'modulation-amount': self.modulation_amount_control.value(),
            'modulation-rate': self.modulation_rate_control.value(),
            'pitch': self.pitch_control.value(),
            'envelope-generator-attack': self.envelope_generator_attack_control.value(),
            'envelope-generator-release': self.envelope_generator_release_control.value(),
        }

    def restore(self, stored_values: typing.Optional[dict]) -> None:
        self.set_combination(stored_values.get('combination-index', 127 // 2))
        self.level_control.setValue(stored_values.get('level', 127 // 2))
        self.modulation_amount_control.setValue(stored_values.get('modulation-amount', 127 // 2))
        self.modulation_rate_control.setValue(stored_values.get('modulation-rate', 127 // 2))
        self.pitch_control.setValue(stored_values.get('pitch', 127 // 4))
        self.envelope_generator_attack_control.setValue(stored_values.get('envelope-generator-attack', 127 // 2))
        self.envelope_generator_release_control.setValue(stored_values.get('envelope-generator-release', 127 // 2))

        # Just set the following parameters to defaults:
        self.control_changed.emit(10, 127 // 2)  # left-right pan
        self.control_changed.emit(49, 127 // 2)  # bit reduction amount
        self.control_changed.emit(50, 127 // 2)  # wave folder amount
        self.control_changed.emit(51, 127 // 2)  # overdrive gain
        self.control_changed.emit(52, 127 // 2)  # pre-mix gain adjustment


class PartControl(PySide6.QtWidgets.QGroupBox):
    control_changed = PySide6.QtCore.Signal(int, int)

    def __init__(self, part_number: int):
        check_int_value('part_number', part_number, 1, 6)
        super().__init__()
        self.setTitle(f'Part {part_number}')
        self.part_number = part_number
        layout = PySide6.QtWidgets.QGridLayout()
        self.setLayout(layout)
        self.layer_controls = [LayerControl(part_number, i) for i in range(1, 2 + 1)]
        for i, layer_control in enumerate(self.layer_controls):
            layer_control.setCheckable(i == 1)
            layer_control.setChecked(i == 0)
            layout.addWidget(layer_control, 0, i)
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
        self.layer_controls[0].restore(stored_values.get('layer1', {}))
        self.layer_controls[1].restore(stored_values.get('layer2' if 'layer2' in stored_values else 'layer1', {}))
        self.layer_controls[1].setChecked('layer2' in stored_values)


class MainWindow(PySide6.QtWidgets.QMainWindow):
    config_path = os.path.join(root_directory_path, 'config.json')

    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyVolca')
        self.setCentralWidget(PySide6.QtWidgets.QWidget())
        layout = PySide6.QtWidgets.QGridLayout()
        self.centralWidget().setLayout(layout)
        self.part_controls = [PartControl(i) for i in range(1, 6 + 1)]
        for i, part_control in enumerate(self.part_controls):
            layout.addWidget(part_control, i // 3, i % 3)
            part_control.control_changed.connect(self.process_control_change)

        device_name = 'UM-ONE 1'  # TODO: make it selectable.
        self.port = mido.open_output(device_name)  # noqa: open_output is a dynamically generated thing.

    def __del__(self):
        self.port.close()

    @PySide6.QtCore.Slot()
    def process_control_change(self, control: int, value: int) -> None:
        print(f'channel={self.part_controls.index(self.sender())}, control={control}, value={value}')
        message = mido.Message('control_change', channel=self.part_controls.index(self.sender()), control=control, value=value)
        self.port.send(message)

    def store(self) -> None:
        stored_values = {'parts': {f'part{i + 1}': self.part_controls[i].store() for i in range(6)}}
        with open(MainWindow.config_path, 'w') as f:
            f.write(json.dumps(stored_values, indent=2))

    def restore(self) -> None:
        if os.path.exists(MainWindow.config_path):
            with open(MainWindow.config_path) as f:
                stored_values = json.loads(f.read())
        else:
            stored_values = {}

        for i in range(6):
            self.part_controls[i].restore(stored_values.get('parts', {}).get(f'part{i + 1}', {}))


def main() -> int:
    application = PySide6.QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.showMaximized()
    main_window.restore()
    ret_code = application.exec()
    main_window.store()
    return ret_code


if __name__ == '__main__':
    sys.exit(main())

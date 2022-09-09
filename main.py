import os
import sys
import typing

import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets
import mido

import config
import modules.common
import modules.controls
import modules.parts


class PortSelectionDialog(PySide6.QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyVolcaDrum: choose port')

        self.port_selector = PySide6.QtWidgets.QComboBox()
        self.port_selector.addItem('')
        for port_name in mido.get_output_names():  # noqa: get_output_names is a dynamically generated thing.
            self.port_selector.addItem(port_name)
        self.port_selector.currentTextChanged.connect(self.__port_selected)

        self.ok_button = PySide6.QtWidgets.QPushButton('OK')
        self.ok_button.setSizePolicy(PySide6.QtWidgets.QSizePolicy.Policy.Maximum, PySide6.QtWidgets.QSizePolicy.Policy.Maximum)
        self.ok_button.hide()
        self.ok_button.clicked.connect(self.accept)

        layout = PySide6.QtWidgets.QVBoxLayout()
        layout.addWidget(self.port_selector, 0, PySide6.QtCore.Qt.AlignCenter)
        layout.addWidget(self.ok_button, 0, PySide6.QtCore.Qt.AlignCenter)
        self.setLayout(layout)

        self.setFixedSize(self.sizeHint())

    def __port_selected(self) -> None:
        self.ok_button.setVisible(bool(self.port_selector.currentText()))
        self.setFixedSize(self.sizeHint())

    def get_port_name(self) -> typing.Optional[str]:
        return self.port_selector.currentText() if self.port_selector.currentText() else None

    def showEvent(self, event: PySide6.QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if not os.path.exists(modules.common.config_path):
            return
        stored_values = config.load_config(file_path=modules.common.config_path)
        if 'port' in stored_values:
            self.port_selector.setCurrentText(stored_values['port'])


class MainWindow(PySide6.QtWidgets.QMainWindow):
    def __init__(self, port_name: str):
        super().__init__()
        self.setWindowTitle('PyVolcaDrum')

        # Controls
        layout = PySide6.QtWidgets.QGridLayout()
        self.__part_controls = [modules.controls.PartControls(i) for i in range(1, 6 + 1)]
        for i, part_control in enumerate(self.__part_controls):
            layout.addWidget(part_control, 0, i)
            part_control.control_changed.connect(self.__process_control_change)
        self.__waveguide_resonator_control = modules.controls.WaveguideResonatorControls()
        layout.addWidget(self.__waveguide_resonator_control, 0, 6)
        self.__waveguide_resonator_control.control_changed.connect(self.__process_control_change)

        # Parts data (timeline)
        self.__parts = modules.parts.Parts()
        self.__parts.note_on.connect(self.__process_note_on)
        self.__parts.overridden_values_found.connect(self.__process_overridden_values)
        self.__parts.step_context_requested.connect(self.__show_override_controls_dialog)
        self.__scroll_area = PySide6.QtWidgets.QScrollArea()
        self.__scroll_area.setWidget(self.__parts)
        self.__scroll_area.setWidgetResizable(True)
        self.__scroll_area.setMinimumHeight(self.__scroll_area.sizeHint().height() + self.__scroll_area.horizontalScrollBar().height())
        layout.addWidget(self.__scroll_area, 1, 0, 1, 7)

        # Play controls
        play_controls_layout = PySide6.QtWidgets.QHBoxLayout()
        play_icon = PySide6.QtGui.QIcon(os.path.join(modules.common.resources_directory_path, 'play.svg'))
        self.__play_button = PySide6.QtWidgets.QToolButton()
        self.__play_button.setCheckable(True)
        self.__play_button.setIcon(play_icon)
        self.__play_button.toggled.connect(self.__process_play_button_push)
        play_controls_layout.addWidget(self.__play_button)
        play_controls_layout.addSpacerItem(PySide6.QtWidgets.QSpacerItem(0, 0, PySide6.QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                                                         PySide6.QtWidgets.QSizePolicy.Policy.Maximum))
        play_controls_layout.addWidget(PySide6.QtWidgets.QLabel('<b>STEP COUNT</b>'))
        self.__step_count_control = PySide6.QtWidgets.QSpinBox()
        self.__step_count_control.setRange(16, 1024)
        self.__step_count_control.editingFinished.connect(self.__resize_parts)
        self.__parts.step_count_changed.connect(self.__step_count_control.setValue)
        play_controls_layout.addWidget(self.__step_count_control)
        play_controls_layout.addWidget(PySide6.QtWidgets.QLabel('<b>BPM</b>'))
        self.__bpm_control = PySide6.QtWidgets.QSpinBox()
        self.__bpm_control.setRange(2, 16)
        self.__bpm_control.editingFinished.connect(self.__resize_parts)
        play_controls_layout.addWidget(self.__bpm_control)
        play_controls_layout.addWidget(PySide6.QtWidgets.QLabel('<b>TEMPO</b>'))
        self.__tempo_control = PySide6.QtWidgets.QSpinBox()
        self.__tempo_control.setRange(60, 360)
        self.__tempo_control.valueChanged.connect(self.__change_tempo)
        play_controls_layout.addWidget(self.__tempo_control)
        layout.addLayout(play_controls_layout, 2, 0, 1, 7)

        self.setCentralWidget(PySide6.QtWidgets.QWidget())
        self.centralWidget().setLayout(layout)

        self.__port = mido.open_output(port_name)  # noqa: open_output is a dynamically generated thing.

    def __del__(self):
        self.__port.close()

    def __process_control_change(self, control: int, value: int) -> None:
        channel_index = 0 if self.sender() is self.__waveguide_resonator_control else self.__part_controls.index(self.sender())
        print(f'control_change, channel={channel_index + 1}, control={control}, value={value}')
        self.__port.send(mido.Message('control_change', channel=channel_index, control=control, value=value))

    def __process_note_on(self, channel_number: int) -> None:
        print(f'note_on, channel={channel_number}')
        self.__port.send(mido.Message('note_on', channel=channel_number - 1))

    def __process_overridden_values(self, channel_number: int, overridden_values: dict) -> None:
        print(f'channel_number={channel_number}, overridden_values={overridden_values}')
        self.__part_controls[channel_number - 1].send_overridden_values(overridden_values)

    def __process_play_button_push(self, checked: bool) -> None:
        if checked:
            self.__parts.play()
        else:
            self.__parts.stop()

    def __resize_parts(self) -> None:
        self.__play_button.setChecked(False)
        self.__parts.change_step_count(self.__step_count_control.value(), self.__bpm_control.value())

    def __change_tempo(self) -> None:
        sender: PySide6.QtWidgets.QSpinBox = self.sender()
        self.__parts.change_tempo(sender.value())

    def __show_override_controls_dialog(self) -> None:
        step: modules.parts.Step = self.sender().sender()
        original_part_controls = self.__part_controls[step.property('part-number') - 1]
        overridden_values = step.property('overridden-values')
        fine_tuning_dialog = modules.controls.PartOverrideControls(original_part_controls, overridden_values)
        if fine_tuning_dialog.exec() != PySide6.QtWidgets.QDialog.Accepted:
            return
        overridden_values = fine_tuning_dialog.get_overridden_values()
        step.set_overridden_values(overridden_values)

    def showEvent(self, event: PySide6.QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self.restore()

    def closeEvent(self, event: PySide6.QtGui.QCloseEvent) -> None:
        self.__play_button.setChecked(False)
        super().closeEvent(event)

    def keyPressEvent(self, event: PySide6.QtGui.QKeyEvent) -> None:
        key_to_part = {
            PySide6.QtCore.Qt.Key_1: 1,
            PySide6.QtCore.Qt.Key_2: 2,
            PySide6.QtCore.Qt.Key_3: 3,
            PySide6.QtCore.Qt.Key_4: 4,
            PySide6.QtCore.Qt.Key_5: 5,
            PySide6.QtCore.Qt.Key_6: 6,
        }
        if event.key() not in key_to_part:
            return
        self.__parts.enable_current_step(key_to_part[event.key()])

    def store(self) -> None:
        stored_values = {
            'port': self.__port.name,
            'controls': {
                'parts': {f'part{i + 1}': self.__part_controls[i].store() for i in range(6)},
                'waveguide-resonator': self.__waveguide_resonator_control.store(),
            },
            'parts': self.__parts.store(),
        }
        config.store_config(stored_values, modules.common.config_path)

    def restore(self) -> None:
        stored_values = config.load_config(file_path=modules.common.config_path)
        for i in range(6):
            self.__part_controls[i].restore(stored_values.get('controls', {}).get('parts', {}).get(f'part{i + 1}', {}))
        self.__waveguide_resonator_control.restore(stored_values.get('controls', {}).get('waveguide-resonator', {}))
        restored_parts = self.__parts.restore(stored_values.get('parts', {}))
        if restored_parts is not None:
            old_parts = self.__scroll_area.takeWidget()
            self.__scroll_area.setWidget(restored_parts)
            self.__parts = restored_parts
            old_parts.deleteLater()
            new_parts: parts.Parts = self.__scroll_area.widget()  # noqa: we know that scroll area holds Parts instance.
            new_parts.note_on.connect(self.__process_note_on)
            new_parts.overridden_values_found.connect(self.__process_overridden_values)
            new_parts.step_context_requested.connect(self.__show_override_controls_dialog)
            new_parts.step_count_changed.connect(self.__step_count_control.setValue)
        for widget in [self.__step_count_control, self.__bpm_control, self.__tempo_control]:
            widget.blockSignals(True)
        self.__step_count_control.setValue(self.__parts.step_count)
        self.__bpm_control.setValue(self.__parts.bpm)
        self.__tempo_control.setValue(self.__parts.tempo)
        for widget in [self.__step_count_control, self.__bpm_control, self.__tempo_control]:
            widget.blockSignals(False)


def main() -> int:
    application = PySide6.QtWidgets.QApplication(sys.argv)
    application.setWheelScrollLines(1)
    application.setWindowIcon(PySide6.QtGui.QIcon(os.path.join(modules.common.resources_directory_path, 'icon.svg')))

    port_selector = PortSelectionDialog()
    if port_selector.exec() != PySide6.QtWidgets.QDialog.Accepted:
        return 1

    main_window = MainWindow(port_selector.get_port_name())
    main_window.showMaximized()
    ret_code = application.exec()
    main_window.store()
    return ret_code


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:  # noqa
        print(f'Fatal error: {str(e)}', file=sys.stderr)
        sys.exit(1)

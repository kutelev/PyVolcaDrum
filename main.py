import os
import sys
import typing

import PySide6.QtGui
import PySide6.QtWidgets
import mido

import config
import controls

root_directory_path = os.path.abspath(os.path.dirname(os.path.relpath(__file__)))


class PortSelectionDialog(PySide6.QtWidgets.QDialog):
    config_path = os.path.join(root_directory_path, 'config.json')

    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyVolcaDrum: chose port')

        self.port_selector = PySide6.QtWidgets.QComboBox()
        self.port_selector.addItem('')
        for port_name in mido.get_output_names():  # noqa: get_output_names is a dynamically generated thing.
            self.port_selector.addItem(port_name)
        self.port_selector.currentTextChanged.connect(self.port_selected)

        self.ok_button = PySide6.QtWidgets.QPushButton('Ok')
        self.ok_button.hide()
        self.ok_button.clicked.connect(self.accept)

        layout = PySide6.QtWidgets.QVBoxLayout()
        layout.addWidget(self.port_selector)
        layout.addWidget(self.ok_button)
        self.setLayout(layout)

        self.setFixedSize(self.sizeHint())

    def port_selected(self) -> None:
        self.ok_button.setVisible(bool(self.port_selector.currentText()))
        self.setFixedSize(self.sizeHint())

    def get_port_name(self) -> typing.Optional[str]:
        return self.port_selector.currentText() if self.port_selector.currentText() else None

    def showEvent(self, event: PySide6.QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if not os.path.exists(PortSelectionDialog.config_path):
            return
        stored_values = config.load_config(file_path=PortSelectionDialog.config_path)
        if 'port' in stored_values:
            self.port_selector.setCurrentText(stored_values['port'])


class MainWindow(PySide6.QtWidgets.QMainWindow):
    config_path = os.path.join(root_directory_path, 'config.json')

    def __init__(self, port_name: str):
        super().__init__()
        self.setWindowTitle('PyVolcaDrum')
        self.setCentralWidget(PySide6.QtWidgets.QWidget())
        layout = PySide6.QtWidgets.QGridLayout()
        self.centralWidget().setLayout(layout)
        self.__part_controls = [controls.PartControls(i) for i in range(1, 6 + 1)]
        for i, part_control in enumerate(self.__part_controls):
            layout.addWidget(part_control, 0, i)
            part_control.control_changed.connect(self.process_control_change)
        self.__waveguide_resonator_control = controls.WaveguideResonatorControls()
        layout.addWidget(self.__waveguide_resonator_control, 0, 6)
        self.__waveguide_resonator_control.control_changed.connect(self.process_control_change)
        self.__port = mido.open_output(port_name)  # noqa: open_output is a dynamically generated thing.

    def __del__(self):
        self.__port.close()

    def process_control_change(self, control: int, value: int) -> None:
        channel = 1 if self.sender() is self.__waveguide_resonator_control else self.__part_controls.index(self.sender())
        print(f'channel={channel}, control={control}, value={value}')
        self.__port.send(mido.Message('control_change', channel=channel, control=control, value=value))

    def showEvent(self, event: PySide6.QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self.restore()

    def store(self) -> None:
        stored_values = {
            'port': self.__port.name,
            'controls': {
                'parts': {f'part{i + 1}': self.__part_controls[i].store() for i in range(6)},
                'waveguide-resonator': self.__waveguide_resonator_control.store(),
            },
        }
        config.store_config(stored_values, MainWindow.config_path)

    def restore(self) -> None:
        stored_values = config.load_config(file_path=MainWindow.config_path)
        for i in range(6):
            self.__part_controls[i].restore(stored_values.get('controls', {}).get('parts', {}).get(f'part{i + 1}', {}))
        self.__waveguide_resonator_control.restore(stored_values.get('controls', {}).get('waveguide-resonator', {}))


def main() -> int:
    application = PySide6.QtWidgets.QApplication(sys.argv)

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

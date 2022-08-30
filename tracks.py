import itertools
import os
import typing

import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

import common

__all__ = ['Timeline']


class Step(PySide6.QtWidgets.QToolButton):
    def __init__(self):
        super().__init__()
        self.setCheckable(True)


class Dot(PySide6.QtWidgets.QRadioButton):
    def __init__(self, step_index: int):
        super().__init__('')
        self.setProperty('id', step_index)


class Tracks(PySide6.QtWidgets.QWidget):
    note_on = PySide6.QtCore.Signal(int)  # Channel number is sent (range from 1 to 6 inclusive).

    __track_count = 6

    def __init__(self, initial_step_count: int = 16):
        common.check_int_value('initial_step_count', initial_step_count, 16, 1024)
        super().__init__()
        self.__step_count = initial_step_count
        self.__current_step_index = 0

        layout = PySide6.QtWidgets.QGridLayout()

        for track_index in range(Tracks.__track_count):
            check_box = PySide6.QtWidgets.QCheckBox()
            check_box.setText(f'TRACK {track_index + 1}')
            check_box.setStyleSheet('QCheckBox { font: bold }')
            check_box.setChecked(True)
            layout.addWidget(check_box, track_index, 0, 1, 1, PySide6.QtCore.Qt.AlignRight)
        for track_index, step_index in itertools.product(range(Tracks.__track_count), range(initial_step_count)):
            layout.addWidget(Step(), track_index, step_index + 1)
        for step_index in range(initial_step_count):
            dot = Dot(step_index)
            dot.clicked.connect(self.__process_dot_click)
            layout.addWidget(dot, Tracks.__track_count, step_index + 1, 1, 1, PySide6.QtCore.Qt.AlignCenter)
        layout.itemAtPosition(Tracks.__track_count, 1).widget().setChecked(True)

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

    def resize(self, new_step_count) -> None:
        common.check_int_value('new_step_count', new_step_count, 16, 1024)
        if new_step_count == self.__step_count:
            return
        self.stop()
        if new_step_count > self.__step_count:
            for track_index, step_index in itertools.product(range(Tracks.__track_count), range(self.__step_count, new_step_count)):
                self.layout().addWidget(Step(), track_index, step_index + 1)
            for step_index in range(self.__step_count, new_step_count):
                dot = Dot(step_index)
                dot.clicked.connect(self.__process_dot_click)
                self.layout().addWidget(dot, Tracks.__track_count, step_index + 1, 1, 1, PySide6.QtCore.Qt.AlignCenter)
        else:
            for row_index, step_index in itertools.product(range(Tracks.__track_count + 1), range(new_step_count, self.__step_count)):
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
        self.layout().itemAtPosition(Tracks.__track_count, step_index + 1).widget().setChecked(True)

    def __do_step(self) -> None:
        enabled_tracks = [track_index for track_index in range(Tracks.__track_count) if self.layout().itemAtPosition(track_index, 0).widget().isChecked()]
        for track_index in enabled_tracks:
            if self.layout().itemAtPosition(track_index, self.__current_step_index + 1).widget().isChecked():
                self.note_on.emit(track_index + 1)
        self.__go_to((self.__current_step_index + 1) % self.__step_count)

    def store(self) -> dict:
        stored_values = {
            'step-count': self.__step_count,
            'tempo': self.tempo,
            'enabled-tracks': [
                track_index + 1 for track_index in range(Tracks.__track_count) if self.layout().itemAtPosition(track_index, 0).widget().isChecked()
            ],
            'tracks': {f'track{track_index + 1}': [] for track_index in range(Tracks.__track_count)},
        }
        for track_index, step_index in itertools.product(range(Tracks.__track_count), range(self.__step_count)):
            if self.layout().itemAtPosition(track_index, step_index + 1).widget().isChecked():
                stored_values['tracks'][f'track{track_index + 1}'].append(step_index + 1)
        return stored_values

    @staticmethod
    def restore(stored_values: typing.Optional[dict]):  # -> Tracks:
        if 'step-count' in stored_values:
            tracks = Tracks(stored_values['step-count'])
        else:
            return None
        tracks.__timer.setInterval(60000 // stored_values.get('tempo', 60))
        enabled_tracks = stored_values.get('enabled-tracks', [])
        for track_index in range(Tracks.__track_count):
            tracks.layout().itemAtPosition(track_index, 0).widget().setChecked(track_index + 1 in enabled_tracks)
        if 'tracks' not in stored_values:
            return tracks
        for track_index in range(Tracks.__track_count):
            track_name = f'track{track_index + 1}'
            if track_name not in stored_values['tracks']:
                continue
            for step_number in stored_values['tracks'][track_name]:
                if step_number > stored_values['step-count']:
                    # This place can only be place if given configuration is invalid.
                    # Unfortunately this validation can not be performed during JSON schema validation.
                    continue
                tracks.layout().itemAtPosition(track_index, step_number).widget().setChecked(True)
        return tracks


class Timeline(PySide6.QtWidgets.QWidget):
    note_on = PySide6.QtCore.Signal(int)  # Channel number is sent (range from 1 to 6 inclusive).

    def __init__(self):
        super().__init__()

        self.__scroll_area = PySide6.QtWidgets.QScrollArea()
        self.__tracks = Tracks()
        self.__tracks.note_on.connect(self.note_on)
        self.__scroll_area.setWidget(self.__tracks)
        self.__scroll_area.setWidgetResizable(True)
        self.__scroll_area.setMinimumHeight(self.__scroll_area.sizeHint().height() + self.__scroll_area.horizontalScrollBar().height())

        play_controls_layout = PySide6.QtWidgets.QHBoxLayout()
        play_icon = PySide6.QtGui.QIcon(os.path.join(common.resources_directory_path, 'play.svg'))
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
        self.__step_count_control.editingFinished.connect(self.__resize_tracks)
        play_controls_layout.addWidget(self.__step_count_control)

        play_controls_layout.addWidget(PySide6.QtWidgets.QLabel('<b>TEMPO</b>'))
        self.__tempo_control = PySide6.QtWidgets.QSpinBox()
        self.__tempo_control.setRange(60, 240)
        self.__tempo_control.editingFinished.connect(self.__change_tempo)
        play_controls_layout.addWidget(self.__tempo_control)

        tracks_layout = PySide6.QtWidgets.QVBoxLayout()
        tracks_layout.addWidget(self.__scroll_area)
        tracks_layout.addLayout(play_controls_layout)
        self.setLayout(tracks_layout)
        self.setSizePolicy(PySide6.QtWidgets.QSizePolicy.Policy.MinimumExpanding, PySide6.QtWidgets.QSizePolicy.Policy.MinimumExpanding)

    def __process_play_button_push(self, checked: bool) -> None:
        if checked:
            self.__tracks.play()
        else:
            self.__tracks.stop()

    def __resize_tracks(self) -> None:
        sender: PySide6.QtWidgets.QSpinBox = self.sender()
        self.__play_button.setChecked(False)
        self.__tracks.resize(sender.value())

    def __change_tempo(self) -> None:
        sender: PySide6.QtWidgets.QSpinBox = self.sender()
        self.__tracks.change_tempo(sender.value())

    def store(self) -> dict:
        return {'tracks': self.__tracks.store()}

    def restore(self, stored_values: typing.Optional[dict]) -> None:
        restored_tracks = Tracks.restore(stored_values.get('tracks', {}))
        if restored_tracks is not None:
            old_tracks = self.__scroll_area.takeWidget()
            self.__scroll_area.setWidget(restored_tracks)
            self.__tracks = restored_tracks
            old_tracks.deleteLater()
        tracks: Tracks = self.__scroll_area.widget()  # noqa: we know that scroll area holds Tracks instance.
        tracks.note_on.connect(self.note_on)
        self.__step_count_control.setValue(tracks.step_count)
        self.__tempo_control.setValue(tracks.tempo)

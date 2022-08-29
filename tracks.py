import os
import itertools

import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

root_directory_path = os.path.abspath(os.path.dirname(os.path.relpath(__file__)))
resources_directory_path = os.path.join(root_directory_path, 'resources')


class Step(PySide6.QtWidgets.QToolButton):
    def __init__(self):
        super().__init__()
        self.setCheckable(True)


class Tracks(PySide6.QtWidgets.QWidget):
    def __init__(self, steps_per_page: int = 256):
        super().__init__()

        layout = PySide6.QtWidgets.QGridLayout()

        track_count = 6
        for track_index in range(track_count):
            layout.addWidget(PySide6.QtWidgets.QLabel(f'<b>TRACK {track_index + 1}</b>'), track_index, 0, 1, 1, PySide6.QtCore.Qt.AlignRight)
        for track_index, step_index in itertools.product(range(track_count), range(steps_per_page)):
            layout.addWidget(Step(), track_index, step_index + 1)
        for step_index in range(steps_per_page):
            layout.addWidget(PySide6.QtWidgets.QRadioButton(''), track_count, step_index + 1, 1, 1, PySide6.QtCore.Qt.AlignCenter)
        layout.itemAtPosition(track_count, 1).widget().setChecked(True)

        self.setLayout(layout)


class Timeline(PySide6.QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.scroll_area = PySide6.QtWidgets.QScrollArea()
        self.tracks = Tracks()
        self.scroll_area.setWidget(self.tracks)
        self.scroll_area.setMinimumHeight(self.scroll_area.sizeHint().height() + self.scroll_area.horizontalScrollBar().height())

        play_controls_layout = PySide6.QtWidgets.QHBoxLayout()
        play_icon = PySide6.QtGui.QIcon(os.path.join(resources_directory_path, 'play.svg'))
        self.play_button = PySide6.QtWidgets.QToolButton()
        self.play_button.setCheckable(True)
        self.play_button.setIcon(play_icon)
        play_controls_layout.addWidget(self.play_button)
        play_controls_layout.addSpacerItem(PySide6.QtWidgets.QSpacerItem(0, 0, PySide6.QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                                                         PySide6.QtWidgets.QSizePolicy.Policy.Maximum))

        tracks_layout = PySide6.QtWidgets.QVBoxLayout()
        tracks_layout.addWidget(self.scroll_area)
        tracks_layout.addLayout(play_controls_layout)
        self.setLayout(tracks_layout)
        self.setSizePolicy(PySide6.QtWidgets.QSizePolicy.Policy.MinimumExpanding, PySide6.QtWidgets.QSizePolicy.Policy.MinimumExpanding)

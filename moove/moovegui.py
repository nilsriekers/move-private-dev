# moovegui.py – PyQt6 main window
import os
import sys
import configparser
import shutil
import platform
import ctypes
import logging
import threading
import signal
import time
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.widgets import RectangleSelector
from PIL import Image

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QCheckBox, QRadioButton, QButtonGroup,
    QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPalette

from moove.qt_helpers import QRangeSliderV, RadioAdapter, set_combo_items, invoke_in_main_thread
from moove.utils import (
    get_display_data, get_directories, read_batch, get_file_data_by_index,
    save_seg_class_recfile, plot_data, select_event, edit_syllable,
    handle_keypress, zoom, unzoom, swipe_left, swipe_right, handle_playback,
    handle_delete, handle_crop, open_resegment_window, update,
    open_cluster_window, open_training_window, open_relabel_window, find_batch_files,
    create_batch_file,
)
from moove.models.ConvMLP import ConvMLP
from moove.models.CNN import CNN
from moove.app_state import AppState

for key in list(mpl.rcParams):
    if key.startswith('keymap.'):
        mpl.rcParams[key] = []

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loading (unchanged logic)
# ---------------------------------------------------------------------------
moove_config_dir = os.environ.get('MOOVE_CONFIG_DIR')
if moove_config_dir:
    home_config_dir = os.path.expanduser(moove_config_dir)
else:
    home_config_dir = os.path.join(Path.home(), ".moove")

config_file_path = os.path.join(home_config_dir, 'moove_config.ini')

if not os.path.exists(config_file_path):
    example_config_file_path = os.path.join(os.path.dirname(__file__), 'moove_config.ini.example')
    os.makedirs(home_config_dir, exist_ok=True)
    shutil.copy(example_config_file_path, config_file_path)
    logger.info(f"Created config file at: {config_file_path}")

_config = configparser.ConfigParser()
_config.read(config_file_path)
_global_dir = os.path.expanduser(_config.get("GENERAL", "global_dir"))

for subdir in ["rec_data", "trained_models", "training_data", "cluster_data", "playbacks"]:
    os.makedirs(os.path.join(_global_dir, subdir), exist_ok=True)

package_example_data = os.path.join(os.path.dirname(__file__), "example_data", "bird_x")
target_bird_x_dir = os.path.join(_global_dir, "rec_data", "bird_x")
if not os.path.exists(target_bird_x_dir):
    shutil.copytree(package_example_data, target_bird_x_dir)

package_example_data_WN = os.path.join(os.path.dirname(__file__), "example_data", "white_noise")
target_WN_dir = os.path.join(_global_dir, "playbacks", "white_noise")
if not os.path.exists(target_WN_dir):
    shutil.copytree(package_example_data_WN, target_WN_dir)


class MooveMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MooveGUI")
        self._set_icon()

        # App state
        self.app_state = AppState(_global_dir)
        self.app_state.load_state()
        self._apply_config()

        # Derive colours from palette
        bg = self.palette().color(QPalette.ColorRole.Window)
        brightness = (bg.red() * 299 + bg.green() * 587 + bg.blue() * 114) / 1000
        self.app_state.text_color = "#ffffff" if brightness < 128 else "#000000"
        self.app_state.bg_color = bg.name()

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(2)

        self._build_top_bar(main_layout)
        self._build_plot_area(main_layout)
        self._build_button_bar(main_layout)
        self._build_radio_bar(main_layout)
        self._connect_canvas_events()

        plot_data(self.app_state)
        self.app_state.init_flag = True

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------
    def _apply_config(self):
        s = self.app_state
        s.config["global_dir"] = _global_dir
        s.config["rec_data"] = os.path.join(_global_dir, "rec_data")
        s.config["lower_spec_plot"] = int(_config.get('GUI', 'lower_spec_plot'))
        s.config["upper_spec_plot"] = int(_config.get('GUI', 'upper_spec_plot'))
        s.config["vmin_range_slider"] = float(_config.get('GUI', 'vmin_range_slider'))
        s.config["vmax_range_slider"] = float(_config.get('GUI', 'vmax_range_slider'))
        s.config["spec_nperseg"] = int(_config.get('GUI', 'spec_nperseg'))
        s.config["spec_noverlap"] = int(_config.get('GUI', 'spec_noverlap'))
        s.config["spec_nfft"] = int(_config.get('GUI', 'spec_nfft'))
        s.config["performance"] = str(_config.get('GUI', 'performance'))

    # ------------------------------------------------------------------
    # Icon
    # ------------------------------------------------------------------
    def _set_icon(self):
        try:
            pkg_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(pkg_dir, "templates", "logo_128_white_bg_small.png")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(pkg_dir, "templates", "logo.png")
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                self.setWindowIcon(icon)
                QApplication.instance().setWindowIcon(icon)
            if os.name == 'nt':
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('moove.gui')
        except Exception as e:
            logger.warning(f"Could not set window icon: {e}")

    # ------------------------------------------------------------------
    # Top bar (comboboxes + checkboxes)
    # ------------------------------------------------------------------
    def _build_top_bar(self, parent_layout):
        s = self.app_state
        bar = QHBoxLayout()

        # Determine restored path parts
        path_parts = None
        if s.data_dir:
            selected_day_path = s.data_dir
            path_parts = Path(selected_day_path).parts
            if path_parts[-4] != Path(s.config['rec_data']).name:
                s.data_dir = None
                path_parts = None

        # Bird
        birds = sorted(get_directories(s.config['rec_data']))
        self.bird_combo = QComboBox()
        self.bird_combo.addItems(birds)
        s.bird_combobox = self.bird_combo
        if path_parts and path_parts[-3] in birds:
            self.bird_combo.setCurrentText(path_parts[-3])
        self.bird_combo.currentTextChanged.connect(self._on_bird_changed)
        bar.addWidget(self.bird_combo)

        # Experiment
        self.experiment_combo = QComboBox()
        self.experiment_combo.setMinimumWidth(180)
        s.experiment_combobox = self.experiment_combo
        self._populate_experiments()
        if path_parts:
            exps = [self.experiment_combo.itemText(i) for i in range(self.experiment_combo.count())]
            if path_parts[-2] in exps:
                self.experiment_combo.setCurrentText(path_parts[-2])
        self.experiment_combo.currentTextChanged.connect(self._on_experiment_changed)
        bar.addWidget(self.experiment_combo)

        # Day
        self.day_combo = QComboBox()
        s.day_combobox = self.day_combo
        self._populate_days()
        if path_parts:
            days_list = [self.day_combo.itemText(i) for i in range(self.day_combo.count())]
            if path_parts[-1] in days_list:
                self.day_combo.setCurrentText(path_parts[-1])
            else:
                self._set_data_dir_from_combos()
        else:
            self._set_data_dir_from_combos()
        self.day_combo.currentTextChanged.connect(lambda: self._on_day_changed())
        bar.addWidget(self.day_combo)

        # Load batch & song files
        selected_day_path = s.data_dir or os.path.join(
            s.config['rec_data'], self.bird_combo.currentText(),
            self.experiment_combo.currentText(), self.day_combo.currentText())
        s.data_dir = selected_day_path

        batch_files = find_batch_files(selected_day_path)
        if s.current_batch_file in batch_files:
            s.song_files = read_batch(selected_day_path, s.current_batch_file)
        else:
            s.current_batch_file = "batch.txt"
            s.song_files = read_batch(selected_day_path)
        if s.current_file_index is None:
            s.current_file_index = 0

        # Refresh batch files on startup
        valid_files = sorted(
            f for f in os.listdir(s.data_dir) if f.endswith('.wav') or f.endswith('.cbin'))
        for batch in batch_files:
            bp = os.path.join(s.data_dir, batch)
            if batch == 'batch.txt':
                with open(bp, 'w') as fh:
                    fh.write('\n'.join(valid_files))
            else:
                with open(bp, 'r') as fh:
                    keep = fh.read().splitlines()
                with open(bp, 'w') as fh:
                    fh.write('\n'.join(f for f in keep if f in valid_files))
        s.song_files = read_batch(s.data_dir, s.current_batch_file)

        file_path = get_file_data_by_index(s.data_dir, s.song_files, s.current_file_index, s)
        s.display_dict = get_display_data(file_path, s.config)

        # File combobox
        self.file_combo = QComboBox()
        self.file_combo.setMinimumWidth(260)
        self.file_combo.addItems(s.song_files)
        if s.song_files:
            self.file_combo.setCurrentText(s.song_files[s.current_file_index])
        s.combobox = self.file_combo
        self.file_combo.currentTextChanged.connect(self._on_file_changed)
        bar.addWidget(self.file_combo)

        # Batch combobox
        self.batch_combo = QComboBox()
        self.batch_combo.setMinimumWidth(180)
        self.batch_combo.addItems(batch_files)
        self.batch_combo.setCurrentText(s.current_batch_file)
        s.batch_combobox = self.batch_combo
        self.batch_combo.currentTextChanged.connect(self._on_batch_changed)
        bar.addWidget(self.batch_combo)

        bar.addStretch()

        # Segmented / Classified checkboxes
        self.segmented_cb = QCheckBox("Segmented")
        self.classified_cb = QCheckBox("Classified")
        s.segmented_checkbox = self.segmented_cb
        s.classified_checkbox = self.classified_cb
        self.segmented_cb.stateChanged.connect(self._on_checkbox_toggle)
        self.classified_cb.stateChanged.connect(self._on_checkbox_toggle)
        bar.addWidget(self.segmented_cb)
        bar.addWidget(self.classified_cb)

        parent_layout.addLayout(bar)

    # ------------------------------------------------------------------
    # Plot area (matplotlib canvas + range slider)
    # ------------------------------------------------------------------
    def _build_plot_area(self, parent_layout):
        s = self.app_state
        plot_row = QHBoxLayout()

        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(
            3, 1, figsize=(9, 5.5),
            gridspec_kw={'height_ratios': [6, 1, 6]}, sharex=True)

        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        s.set_axes(self.ax1, self.ax2, self.ax3)
        s.set_canvas(self.canvas)
        s.display_dict = get_display_data(
            get_file_data_by_index(s.data_dir, s.song_files, s.current_file_index, s),
            s.config)
        s.ax3_background = s.canvas.copy_from_bbox(s.ax3.bbox)

        plot_row.addWidget(self.canvas, stretch=1)

        # Range slider
        vmin_cfg = s.config['vmin_range_slider']
        vmax_cfg = s.config['vmax_range_slider']
        if (s.current_vmin is not None and s.current_vmax is not None
                and s.current_vmin > vmin_cfg and s.current_vmax < vmax_cfg):
            init_bot, init_top = s.current_vmin, s.current_vmax
        else:
            dist = (vmax_cfg - vmin_cfg) / 4
            init_bot, init_top = vmin_cfg + dist, vmax_cfg - dist

        self.range_slider = QRangeSliderV(vmin_cfg, vmax_cfg, init_bot, init_top)
        self.range_slider.setFixedWidth(100)
        self.range_slider.valuesChanged.connect(self._on_slider_changed)
        plot_row.addWidget(self.range_slider)

        parent_layout.addLayout(plot_row, stretch=1)

        # Rectangle selectors
        self.rect_sel_ax1 = RectangleSelector(
            self.ax1, self._on_rect_select, useblit=True, button=[1],
            minspanx=30, minspany=30, spancoords='pixels', interactive=False,
            state_modifier_keys={"rotate": ""})
        self.rect_sel_ax3 = RectangleSelector(
            self.ax3, self._on_rect_select, useblit=True, button=[1],
            minspanx=30, minspany=30, spancoords='pixels', interactive=False,
            state_modifier_keys={"rotate": ""})

    # ------------------------------------------------------------------
    # Button bar
    # ------------------------------------------------------------------
    def _build_button_bar(self, parent_layout):
        s = self.app_state
        bar = QHBoxLayout()

        refresh_text = "↻" if platform.system() == 'Darwin' else "⟳"
        btn = lambda text, cb: self._make_btn(text, cb, bar)

        btn(refresh_text, lambda: update(s))
        btn("Previous", lambda: (s.change_file(-1), plot_data(s)))
        btn("Next", lambda: (s.change_file(1), plot_data(s)))
        btn("  <  ", lambda: swipe_left(s))
        btn("  >  ", lambda: swipe_right(s))
        btn("Zoom", lambda: zoom(s))
        btn("Unzoom", lambda: unzoom(s))
        btn("Crop", lambda: handle_crop(s))
        btn("Delete", lambda: handle_delete(s))
        btn("Play", lambda: handle_playback(s))
        btn("Resegment", lambda: open_resegment_window(self, s))
        btn("Relabel", lambda: open_relabel_window(self, s))
        btn("Training", lambda: open_training_window(self, s))
        btn("Cluster", lambda: open_cluster_window(self, s))

        bar.addStretch()
        parent_layout.addLayout(bar)

    @staticmethod
    def _make_btn(text, callback, layout):
        b = QPushButton(text)
        b.clicked.connect(callback)
        layout.addWidget(b)
        return b

    # ------------------------------------------------------------------
    # Radio buttons for edit mode
    # ------------------------------------------------------------------
    def _build_radio_bar(self, parent_layout):
        bar = QHBoxLayout()
        bar.addStretch()
        self.edit_group = QButtonGroup(self)
        options = [("None", 1), ("New Segment", 2), ("Delete Segment", 3),
                   ("Move Segment", 4), ("Label Interactive", 5)]
        for txt, val in options:
            rb = QRadioButton(txt)
            self.edit_group.addButton(rb, val)
            bar.addWidget(rb)
            if val == 1:
                rb.setChecked(True)
        self.edit_group.idToggled.connect(self._on_edit_type_toggled)
        bar.addStretch()
        parent_layout.addLayout(bar)

        self.radio_adapter = RadioAdapter(self.edit_group)
        self.app_state.reset_edit_type_gui = lambda: self.radio_adapter.set("1")

    # ------------------------------------------------------------------
    # Canvas events
    # ------------------------------------------------------------------
    def _connect_canvas_events(self):
        s = self.app_state
        self.canvas.mpl_connect('key_press_event',
                                lambda ev: handle_keypress(ev, s, self.radio_adapter))
        self.canvas.mpl_connect('button_press_event', lambda ev: select_event(ev, s))
        self.canvas.mpl_connect('key_press_event', lambda ev: edit_syllable(ev, s))

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_bird_changed(self):
        self._populate_experiments()
        self._populate_days()
        self._on_day_changed()

    def _on_experiment_changed(self):
        self._populate_days()
        self._on_day_changed()

    def _on_day_changed(self):
        s = self.app_state
        if not s.init_flag:
            return
        self._set_data_dir_from_combos()
        s.current_file_index = 0

        batch_files = find_batch_files(s.data_dir)
        set_combo_items(self.batch_combo, batch_files, "batch.txt")
        if not batch_files:
            create_batch_file(s.data_dir)
        s.current_batch_file = "batch.txt"

        s.song_files = read_batch(s.data_dir, s.current_batch_file)
        set_combo_items(self.file_combo, s.song_files,
                        s.song_files[s.current_file_index] if s.song_files else None)
        plot_data(s)

    def _on_file_changed(self):
        s = self.app_state
        selected = self.file_combo.currentText()
        if selected and selected in s.song_files:
            s.current_file_index = s.song_files.index(selected)
            plot_data(s)

    def _on_batch_changed(self):
        s = self.app_state
        selected = self.batch_combo.currentText()
        if not selected:
            return
        s.current_batch_file = selected
        s.song_files = read_batch(s.data_dir, selected)
        s.current_file_index = 0 if s.song_files else None
        set_combo_items(self.file_combo, s.song_files,
                        s.song_files[0] if s.song_files else "")
        if s.song_files:
            plot_data(s)
        else:
            for ax in [s.ax1, s.ax2, s.ax3]:
                ax.clear()
            s.canvas.draw()

    def _on_slider_changed(self, vmin, vmax):
        s = self.app_state
        s.current_vmin = vmin
        s.current_vmax = vmax
        s.redraw_spectrogram(vmin, vmax)

    def _on_checkbox_toggle(self):
        s = self.app_state
        seg = "1" if self.segmented_cb.isChecked() else "0"
        cla = "1" if self.classified_cb.isChecked() else "0"
        s.segmented_var.set(seg)
        s.classified_var.set(cla)
        fp = get_file_data_by_index(s.data_dir, s.song_files, s.current_file_index, s)
        rec_path = os.path.splitext(fp["file_path"])[0] + ".rec"
        save_seg_class_recfile(rec_path, seg, cla)

    def _on_rect_select(self, eclick, erelease):
        if abs(eclick.xdata - erelease.xdata) * 1000 < 5:
            return
        def _set(axis, ec, er):
            if ec.ydata > er.ydata:
                ec.ydata, er.ydata = er.ydata, ec.ydata
            if ec.xdata > er.xdata:
                ec.xdata, er.xdata = er.xdata, ec.xdata
            axis.set_xlim(ec.xdata, er.xdata)
        if eclick.inaxes == self.ax1:
            _set(self.ax1, eclick, erelease)
        elif eclick.inaxes == self.ax3:
            _set(self.ax3, eclick, erelease)
        self.canvas.draw()

    _EDIT_MAP = {1: "None", 2: "New Segment", 3: "Delete Segment",
                 4: "Move Segment", 5: "Label Interactive"}

    def _on_edit_type_toggled(self, btn_id, checked):
        if not checked:
            return
        value = self._EDIT_MAP.get(btn_id, "None")
        self.app_state.edit_type = value
        cursor = Qt.CursorShape.CrossCursor if value != "None" else Qt.CursorShape.ArrowCursor
        self.canvas.setCursor(cursor)
        if value == "None" and self.app_state.selected_syllable_index is not None:
            if self.app_state.ax2.texts:
                self.app_state.ax2.texts[self.app_state.selected_syllable_index].set_color('black')
            self.app_state.selected_syllable_index = None
            self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _populate_experiments(self):
        bird = self.bird_combo.currentText()
        if not bird:
            return
        exps = sorted(get_directories(os.path.join(self.app_state.config['rec_data'], bird)))
        set_combo_items(self.experiment_combo, exps, exps[0] if exps else None)

    def _populate_days(self):
        bird = self.bird_combo.currentText()
        exp = self.experiment_combo.currentText()
        if not bird or not exp:
            return
        days = sorted(get_directories(
            os.path.join(self.app_state.config['rec_data'], bird, exp)))
        set_combo_items(self.day_combo, days, days[0] if days else None)

    def _set_data_dir_from_combos(self):
        self.app_state.data_dir = os.path.join(
            self.app_state.config['rec_data'],
            self.bird_combo.currentText(),
            self.experiment_combo.currentText(),
            self.day_combo.currentText())

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------
    def closeEvent(self, event):
        s = self.app_state
        with s.thread_lock:
            active = len(s.active_threads)
        if active > 0:
            reply = QMessageBox.question(
                self, "Active Threads",
                f"{active} thread(s) still running. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            s.shutdown_all_threads()

        s.save_state()
        logger.info("Application state saved")

        # Timeout safety net
        def _force():
            time.sleep(3.0)
            os._exit(1)
        threading.Thread(target=_force, daemon=True).start()

        event.accept()
        QApplication.instance().quit()


def main():
    app = QApplication(sys.argv)
    window = MooveMainWindow()
    window.resize(1200, 600)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

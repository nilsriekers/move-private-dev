# utils/clustering_utils.py
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import threading
import warnings
import evfuncs
from matplotlib import cm
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from scipy import interpolate
from scipy.signal import spectrogram
from sklearn.cluster import KMeans
from umap import UMAP

from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout

from moove.qt_helpers import invoke_in_main_thread, show_info

warnings.filterwarnings('ignore')


def start_create_cluster_dataset_thread(app_state, dataset_name, use_selected_files, selection, batch_file, bird, experiment, day, parent):
    """Start a thread to create a cluster dataset based on selected files and criteria."""
    from moove.utils import get_files_for_day, get_files_for_experiment, get_files_for_bird, filter_segmented_files

    if selection == "current_day":
        files = get_files_for_day(app_state, bird, experiment, day, batch_file)
    elif selection == "current_experiment":
        files = get_files_for_experiment(app_state, bird, experiment, batch_file)
    elif selection == "current_bird":
        files = get_files_for_bird(app_state, bird, batch_file)

    if use_selected_files:
        files = filter_segmented_files(files)

    app_state.logger.debug(
        "Creating training dataset with parameters: Use selected files: %s, Selection: %s, Batch file: %s",
        use_selected_files, selection, batch_file
    )

    if len(dataset_name) < 1:
        show_info(parent, "Error", "Dataset name not valid! A dataset name needs to contain at least one character.")
    else:
        win = app_state.cluster_window
        progressbar = win.progressbar
        progressbar.setMaximum(len(files))
        progressbar.setValue(0)
        progressbar.show()

        def thread_wrapper():
            current_thread = threading.current_thread()
            try:
                create_cluster_dataset(app_state, dataset_name, progressbar, len(files), files, parent)
            finally:
                app_state.remove_thread(current_thread)

        thread = threading.Thread(target=thread_wrapper, name="CreateClusterDatasetThread")
        app_state.add_thread(thread)
        thread.start()


def create_cluster_dataset(app_state, dataset_name, progressbar, max_value, all_files, parent):
    """Generate and save a cluster dataset, tracking progress with a progress bar."""
    from moove.utils import get_display_data, seconds_to_index, decibel, plot_data

    original_data_dir = app_state.data_dir
    original_song_files = app_state.song_files.copy() if app_state.song_files else []
    original_current_file_index = app_state.current_file_index

    if dataset_name:
        going_prod_df = pd.DataFrame(columns=['file', 'onset_no', 'cluster_flattend_spectrogram', 'label'])
        entry_no = 0

    invoke_in_main_thread(progressbar.hide)

    def _show_looking():
        if hasattr(app_state.cluster_window, 'status_label'):
            app_state.cluster_window.status_label.setText("Looking for segments...")
            app_state.cluster_window.status_label.show()
    invoke_in_main_thread(_show_looking)

    def get_onset_offset_info(file_path):
        notmat_file = file_path + ".not.mat"
        if os.path.exists(notmat_file):
            notmat_dict = evfuncs.load_notmat(notmat_file)
            return {"onsets": notmat_dict.get("onsets", []), "offsets": notmat_dict.get("offsets", [])}
        return {"onsets": [], "offsets": []}

    num_segs = 0
    for file_path in all_files:
        info = get_onset_offset_info(file_path)
        if len(info["onsets"]) > 0 and len(info["offsets"]) > 0:
            num_segs += min(len(info["onsets"]), len(info["offsets"]))

    if num_segs < 10:
        invoke_in_main_thread(lambda: (
            app_state.cluster_window.status_label.hide() if hasattr(app_state.cluster_window, 'status_label') else None,
            show_info(parent, "Error", "Not enough segments given. Need at least 10 segments to form clusters.")))
        return

    def _hide_show_progress():
        if hasattr(app_state.cluster_window, 'status_label'):
            app_state.cluster_window.status_label.hide()
        progressbar.show()
    invoke_in_main_thread(_hide_show_progress)

    for i in range(max_value):
        invoke_in_main_thread(progressbar.setValue, i)
        file_i = all_files[i]
        file_path = {"file_name": os.path.basename(file_i), "file_path": os.path.join(os.getcwd(), file_i)}
        display_dict = get_display_data(file_path, app_state.config)
        app_state.data_dir = os.path.dirname(file_i)

        sampling_rate = int(display_dict["sampling_rate"])
        rawsong = display_dict["song_data"]

        freq_cutoffs = tuple(map(int, app_state.spec_params['freq_cutoffs'].get().split(',')))
        onsets, offsets = display_dict["onsets"], display_dict["offsets"]

        if dataset_name:
            nperseg = int(app_state.spec_params['nperseg'].get())
            noverlap = int(app_state.spec_params['noverlap'].get())
            nfft = int(app_state.spec_params['nfft'].get())

            for syllable_no, (onset, offset) in enumerate(zip(onsets, offsets)):
                entry_no += 1
                onset_index = int(seconds_to_index(onset, sampling_rate))
                offset_index = int(seconds_to_index(offset, sampling_rate))
                cutted_raw_song = rawsong[onset_index:offset_index]
                f, t, Sxx_cluster = spectrogram(cutted_raw_song, fs=sampling_rate, nperseg=nperseg, noverlap=noverlap, nfft=nfft)

                Sxx_cluster = Sxx_cluster[(f >= freq_cutoffs[0]) & (f <= freq_cutoffs[1]), :]

                original_shape = Sxx_cluster.shape
                x_old = np.linspace(0, 1, original_shape[1])
                x_new = np.linspace(0, 1, 40)
                f_i = interpolate.interp1d(x_old, Sxx_cluster, kind='linear', axis=1)
                Sxx_cluster = f_i(x_new)
                Sxx_cluster = decibel(Sxx_cluster)

                going_prod_df.loc[entry_no] = [file_i, syllable_no, Sxx_cluster.flatten(), "x"]

    if dataset_name:
        file_path = os.path.join(app_state.config['global_dir'], 'cluster_data', f'{dataset_name}_clus.pkl')
        going_prod_df.to_pickle(file_path)
        app_state.update_cluster_datasets_combobox()

    app_state.data_dir = original_data_dir
    app_state.song_files = original_song_files
    app_state.current_file_index = original_current_file_index

    invoke_in_main_thread(progressbar.setValue, max_value)
    invoke_in_main_thread(progressbar.hide)
    invoke_in_main_thread(lambda: show_info(
        parent, "Info", f"Cluster dataset '{dataset_name}' created successfully!"))


def start_clustering_thread(parent, app_state, dataset_name_entry):
    """Start the clustering process in a separate thread."""
    dataset_name = dataset_name_entry
    if dataset_name == "Select Cluster Dataset":
        show_info(parent, "Error", "Selected cluster dataset not valid! Perhaps you forgot to pick a dataset?")
        return
    else:
        show_info(parent, "Info", "Clustering started. This may take a while, please wait!")

    def thread_wrapper():
        current_thread = threading.current_thread()
        try:
            run_clustering(parent, app_state, dataset_name)
        finally:
            app_state.remove_thread(current_thread)

    thread = threading.Thread(target=thread_wrapper, name="ClusteringThread")
    app_state.add_thread(thread)
    thread.start()


def run_clustering(parent, app_state, dataset_name):
    """Run the clustering process using UMAP and KMeans."""
    dataset_name_pkl = f"{dataset_name}.pkl"
    n_syllables = int(app_state.umap_k_means_params['n_clusters'].get())
    n_neighbors = int(app_state.umap_k_means_params['n_neighbors'].get())
    min_dist = float(app_state.umap_k_means_params['min_dist'].get())

    def _show_running():
        if hasattr(app_state.cluster_window, 'status_label'):
            app_state.cluster_window.status_label.setText("Running...")
            app_state.cluster_window.status_label.show()
    invoke_in_main_thread(_show_running)

    dataset_path = os.path.join(app_state.config['global_dir'], 'cluster_data', dataset_name_pkl)
    if not os.path.exists(dataset_path):
        app_state.logger.error("Dataset %s not found in cluster_data folder.", dataset_name_pkl)
        return

    df = pd.read_pickle(dataset_path)
    spectrogram_feature_array = np.array([np.array(x) for x in df['cluster_flattend_spectrogram'].values])

    umap_model = UMAP(n_neighbors=n_neighbors, min_dist=min_dist, n_components=2, metric='euclidean', random_state=42)
    low_dimensional_data = umap_model.fit_transform(spectrogram_feature_array)

    kmeans = KMeans(n_clusters=n_syllables, random_state=42)
    labels = kmeans.fit_predict(low_dimensional_data)

    label_mapping = {i: chr(97 + i) for i in range(n_syllables)}
    alphabet_labels = [label_mapping[label] for label in labels]
    df['clustered_label'] = alphabet_labels

    df['UMAP1'] = low_dimensional_data[:, 0]
    df['UMAP2'] = low_dimensional_data[:, 1]

    output_path = os.path.join(app_state.config['global_dir'], 'cluster_data', dataset_name_pkl)
    df.to_pickle(output_path)

    invoke_in_main_thread(plot_clusters, parent, app_state, low_dimensional_data, alphabet_labels, output_path)

    def _hide_running():
        if hasattr(app_state.cluster_window, 'status_label'):
            app_state.cluster_window.status_label.hide()
    invoke_in_main_thread(_hide_running)

    app_state.logger.debug("Clustering complete. Results saved to %s", output_path)
    invoke_in_main_thread(lambda: show_info(
        parent, "Info", f"Clustering complete! Results saved to {output_path}"))


def plot_clusters(parent, app_state, low_dimensional_data, labels, output_path):
    """Plot and save the clustering results in a new dialog window."""
    unique_labels = sorted(set(labels))
    label_mapping = {label: idx for idx, label in enumerate(unique_labels)}
    numeric_labels = [label_mapping[label] for label in labels]

    dlg = QDialog(parent)
    dlg.setWindowTitle("Cluster Plot")
    dlg.resize(800, 600)
    layout = QVBoxLayout(dlg)

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.subplots_adjust(left=0.124, bottom=0.138, top=0.912, right=0.842, wspace=0.2, hspace=0.2)
    scatter = ax.scatter(low_dimensional_data[:, 0], low_dimensional_data[:, 1],
                         c=numeric_labels, s=5, cmap=cm.get_cmap('jet'))

    handles, _ = scatter.legend_elements()
    legend = ax.legend(handles, unique_labels, title="Labels", loc='center left', bbox_to_anchor=(1.02, 0.5))
    ax.add_artist(legend)
    ax.set_title("UMAP Clustering")
    ax.set_xlabel("UMAP1")
    ax.set_ylabel("UMAP2")

    plot_path = output_path.replace('_clus.pkl', '_clusters.png')
    plt.savefig(plot_path)
    app_state.logger.debug("Cluster plot saved to %s", plot_path)

    canvas = FigureCanvasQTAgg(fig)
    toolbar = NavigationToolbar2QT(canvas, dlg)
    layout.addWidget(toolbar)
    layout.addWidget(canvas)

    dlg.show()


def replace_labels_from_df(app_state, dataset_name, parent=None):
    """Replace labels in the dataset based on clustering results."""
    from moove.utils.file_utils import get_display_data
    from moove.utils.movefuncs_utils import save_notmat
    from moove.utils.plot_utils import plot_data

    if dataset_name == "Select Cluster Dataset":
        show_info(parent, "Error", "Selected cluster dataset not valid! Perhaps you forgot to pick a dataset?")
        return
    else:
        show_info(parent, "Info", "Replacement of syllables started. This may take a while, please wait!")

    original_data_dir = app_state.data_dir
    original_song_files = app_state.song_files.copy() if app_state.song_files else []
    original_current_file_index = app_state.current_file_index

    dataset_path = os.path.join(app_state.config['global_dir'], 'cluster_data', f'{dataset_name}.pkl')
    df = pd.read_pickle(dataset_path)
    files = df['file'].unique()

    app_state.logger.debug("Starting replacement of syllables with dataset %s", dataset_name)

    win = app_state.cluster_window
    progressbar = win.progressbar
    progressbar.setMaximum(len(files))
    progressbar.setValue(0)
    progressbar.show()

    for i, file in enumerate(files):
        try:
            invoke_in_main_thread(progressbar.setValue, i)
            if 'clustered_label' not in df.columns:
                raise KeyError("Dataset has not been clustered yet. Please cluster the dataset first before replacing labels.")
            labels = df.loc[df['file'] == file]['clustered_label'].astype(str).str.cat(sep='')

            display_dict = get_display_data({"file_name": os.path.basename(file), "file_path": file}, app_state.config)
            display_dict["labels"] = labels

            app_state.data_dir = os.path.dirname(file)
            save_path = os.path.join(app_state.data_dir, f"{display_dict['file_name']}.not.mat")
            app_state.logger.debug("Saving labels to %s", save_path)
            save_notmat(save_path, display_dict)

        except Exception as e:
            app_state.logger.error(f"File {file} could not be processed correctly: {e}. Check manually.")
            return

    app_state.data_dir = original_data_dir
    app_state.song_files = original_song_files
    app_state.current_file_index = original_current_file_index
    invoke_in_main_thread(progressbar.setValue, len(files))

    invoke_in_main_thread(progressbar.hide)
    invoke_in_main_thread(app_state.reset_edit_type)
    invoke_in_main_thread(plot_data, app_state)
    invoke_in_main_thread(lambda: show_info(
        parent, "Info", "Replacement of syllables complete!"))

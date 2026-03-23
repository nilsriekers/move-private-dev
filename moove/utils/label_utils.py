# utils/label_utils.py
import os
import pandas as pd
import pickle
import threading
import torch
import torch.nn.functional as F
import evfuncs
import re
from scipy.signal import spectrogram

from PyQt6.QtWidgets import QApplication

from moove.qt_helpers import invoke_in_main_thread, show_info


def load_classification_checkmarks(all_files):
    """Check whether files have been manually checked as being classified"""
    unclass_files = []
    for file in all_files:
        recfile_path = os.path.splitext(file)[0] + ".rec"
        if not os.path.exists(recfile_path):
            # Missing recfile should not block relabeling.
            unclass_files.append(file)
            continue
        with open(recfile_path, "r") as f:
            content = f.read()

        hand_segmented_pattern = r"Hand Classified = (\d+)"
        hand_segmented_match = re.search(hand_segmented_pattern, content)

        if not hand_segmented_match or hand_segmented_match.group(1) == '0':
            unclass_files.append(file)

    return unclass_files


def start_create_classification_training_dataset(app_state, dataset_name, use_selected_files, selection, batch_file,
                                                 bird, experiment, day, parent):
    """Initialize the creation of a classification training dataset in a new thread."""
    from moove.utils import get_files_for_day, get_files_for_experiment, get_files_for_bird, filter_classified_files

    win = app_state.training_window
    if hasattr(win, 'status_label'):
        win.status_label.setText("Looking for files...")
        win.status_label.show()
        QApplication.processEvents()

    if selection == "current_day":
        files = get_files_for_day(app_state, bird, experiment, day, batch_file)
    elif selection == "current_experiment":
        files = get_files_for_experiment(app_state, bird, experiment, batch_file)
    elif selection == "current_bird":
        files = get_files_for_bird(app_state, bird, batch_file)

    if use_selected_files:
        files = filter_classified_files(files)

    if hasattr(win, 'status_label'):
        win.status_label.hide()
        QApplication.processEvents()

    dataset_name = str(dataset_name)
    if len(dataset_name) < 1:
        show_info(parent, "Error", "Dataset name not valid! "
                                   "A dataset name needs to contain at least one character.")
    else:
        progressbar = win.progressbar
        progressbar.setMaximum(len(files))
        progressbar.setValue(0)
        progressbar.show()

        def thread_wrapper():
            current_thread = threading.current_thread()
            try:
                create_classification_training_dataset(app_state, progressbar, dataset_name, files, parent)
            finally:
                app_state.remove_thread(current_thread)

        thread = threading.Thread(target=thread_wrapper, name="CreateClassDatasetThread")
        app_state.add_thread(thread)
        thread.start()


def create_classification_training_dataset(app_state, progressbar, dataset_name, files, parent):
    """Create a classification training dataset based on selected files and parameters."""
    from moove.utils import get_display_data, seconds_to_index

    if len(files) == 0:
        invoke_in_main_thread(lambda: show_info(
            parent, "Error", "Not enough files given! You need at least 1 file to create a dataset."))
        return

    input_length_str = app_state.spec_params['input_length'].get()
    input_length, chunk_size = map(int, input_length_str.split(','))
    nperseg = int(app_state.spec_params['nperseg'].get())
    noverlap = int(app_state.spec_params['noverlap'].get())
    nfft = int(app_state.spec_params['nfft'].get())
    freq_cutoffs = tuple(map(int, app_state.spec_params['freq_cutoffs'].get().split(',')))
    input_array_size = input_length * chunk_size

    going_prod_df = pd.DataFrame(columns=['file', 'onset_no', 'taf_unflattend_spectrogram', 'label'])
    entry_no = 0

    invoke_in_main_thread(progressbar.hide)

    def _show_looking():
        if hasattr(app_state.training_window, 'status_label'):
            app_state.training_window.status_label.setText("Looking for syllables...")
            app_state.training_window.status_label.show()

    invoke_in_main_thread(_show_looking)

    def get_onsets(file_path):
        notmat_file = file_path + ".not.mat"
        if os.path.exists(notmat_file):
            notmat_dict = evfuncs.load_notmat(notmat_file)
            return notmat_dict.get("onsets", [])
        return []

    num_onsets = 0
    for file_i in files:
        working_dir = os.getcwd()
        file_path = os.path.join(working_dir, file_i)
        onsets = get_onsets(file_path)
        if len(onsets) > 0:
            num_onsets += len(onsets)

    if num_onsets == 0:
        invoke_in_main_thread(lambda: (
            app_state.training_window.status_label.hide() if hasattr(app_state.training_window, 'status_label')
            else None,
            show_info(parent, "Error", "No syllable onsets found in the given files.")))
        return

    def _hide_show_progress():
        if hasattr(app_state.training_window, 'status_label'):
            app_state.training_window.status_label.hide()
        progressbar.show()

    invoke_in_main_thread(_hide_show_progress)

    for i, file_i in enumerate(files):
        invoke_in_main_thread(lambda: QApplication.processEvents())
        working_dir = os.getcwd()
        file_path = os.path.join(working_dir, file_i)
        file_data = get_display_data({"file_name": os.path.basename(file_path), "file_path": file_path},
                                     app_state.config)
        sampling_rate = int(file_data["sampling_rate"])
        rawsong, onsets, labels = file_data["song_data"], file_data["onsets"], file_data["labels"]

        if len(onsets) > 0:
            invoke_in_main_thread(progressbar.setValue, i)
            for syllable_no, onset in enumerate(onsets):
                entry_no += 1
                onset_index = int(seconds_to_index(onset, sampling_rate))
                cutted_raw_song = rawsong[onset_index:onset_index + input_array_size]

                f, t, Sxx_taf = spectrogram(cutted_raw_song, fs=sampling_rate, nperseg=nperseg,
                                            noverlap=noverlap, nfft=nfft)
                if Sxx_taf.ndim == 2:
                    Sxx_taf = Sxx_taf[(f >= freq_cutoffs[0]) & (f <= freq_cutoffs[1]), :]
                else:
                    app_state.logger.warning(f"Warning: Sxx_taf is {Sxx_taf.ndim}-dimensional for file {file_i}, "
                                             f"skipping this entry.")
                    continue

                going_prod_df.loc[entry_no] = [file_i, syllable_no, Sxx_taf, labels[syllable_no]]

    metadata = {
        'input_length': input_length_str,
        'nperseg': nperseg,
        'noverlap': noverlap,
        'nfft': nfft,
        'lowcut': freq_cutoffs[0],
        'highcut': freq_cutoffs[1],
    }

    save_path = os.path.join(app_state.config['global_dir'], 'training_data', f'{dataset_name}_class.pkl')
    with open(save_path, 'wb') as f:
        pickle.dump({'dataframe': going_prod_df, 'metadata': metadata}, f)

    app_state.update_classification_datasets_combobox()
    invoke_in_main_thread(progressbar.setValue, len(files))
    invoke_in_main_thread(progressbar.hide)

    invoke_in_main_thread(lambda: show_info(
        parent, "Info", "Classification training dataset has been created successfully!"))

    first_index = going_prod_df.index[0]
    shape_first_entry = pd.DataFrame(going_prod_df.loc[first_index, 'taf_unflattend_spectrogram']).shape
    app_state.logger.debug(f"The shape of the first entry in 'taf_unflattend_spectrogram' is {shape_first_entry}")


def normalize_spectrogram(spectrogram_data):
    """Normalize the spectrogram to zero mean and unit variance."""
    mean, std = spectrogram_data.mean(), spectrogram_data.std()
    return (spectrogram_data - mean) / std if std != 0 else spectrogram_data


def start_classify_files_thread(app_state, model_name, selection, checkbox_ow, batch_file, bird, experiment, day):
    """Start the classification process for selected files in a new thread."""
    from moove.utils import get_files_for_day, get_files_for_experiment, get_files_for_bird, get_file_data_by_index

    if selection == "current_day":
        files = get_files_for_day(app_state, bird, experiment, day, batch_file)
    elif selection == "current_experiment":
        files = get_files_for_experiment(app_state, bird, experiment, batch_file)
    elif selection == "current_bird":
        files = get_files_for_bird(app_state, bird, batch_file)
    elif selection == "current_file":
        files = [get_file_data_by_index(app_state.data_dir,
                                        app_state.song_files,
                                        app_state.current_file_index,
                                        app_state)["file_path"]]
    from IPython import embed; embed()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        checkpoint = torch.load(os.path.join(app_state.config['global_dir'], 'trained_models', f'{model_name}.pth'),
                                map_location=device)
    except:
        print(os.path.join(app_state.config['global_dir'], 'trained_models', f'{model_name}.pth'))
        show_info(app_state.relabel_window, "Error",
                  "Selected classification model doesn't exist or is not valid! "
                  "Perhaps you forgot to pick a model?")
        return
    model, metadata = checkpoint['model'], checkpoint['metadata']

    model.to(device).eval()

    total_selected = len(files)
    if not checkbox_ow:
        files = load_classification_checkmarks(files)
    skipped_preclassified = total_selected - len(files)

    if len(files) == 0:
        if skipped_preclassified > 0:
            show_info(app_state.relabel_window, "Info", f"No files available for relabeling. "
                                                        f"Skipped {skipped_preclassified} already classified file(s).")
        else:
            show_info(app_state.relabel_window, "Info", "No files available for relabeling.")
        return

    win = app_state.relabel_window
    progressbar = win.progressbar
    progressbar.setMaximum(len(files))
    progressbar.setValue(0)
    progressbar.show()

    def thread_wrapper():
        current_thread = threading.current_thread()
        try:
            ml_classify_file(app_state, progressbar, len(files), files, model, metadata, device,
                             total_selected=total_selected, skipped_preclassified=skipped_preclassified)
        finally:
            app_state.remove_thread(current_thread)

    thread = threading.Thread(target=thread_wrapper, name="ClassifyFilesThread")
    app_state.add_thread(thread)
    thread.start()


def ml_classify_file(app_state, progressbar, max_value, all_files, model, metadata, device,
                     total_selected=None, skipped_preclassified=0):
    """Perform classification on each file and update labels."""
    from moove.utils import get_display_data, plot_data, save_notmat, seconds_to_index

    original_data_dir = app_state.data_dir
    original_song_files = app_state.song_files.copy() if app_state.song_files else []
    original_current_file_index = app_state.current_file_index

    input_length, chunk_size = map(int, metadata['input_length'].split(','))
    nperseg, noverlap, nfft = int(metadata['nperseg']), int(metadata['noverlap']), int(metadata['nfft'])
    lowcut, highcut, int_to_label = int(metadata['lowcut']), int(metadata['highcut']), metadata['int_to_label']
    input_array_size = input_length * chunk_size
    processed_count = 0
    failed_count = 0
    skipped_no_segments = 0

    for i, file_i in enumerate(all_files):
        try:
            invoke_in_main_thread(progressbar.setValue, i)
            file_data = get_display_data({"file_name": os.path.basename(file_i), "file_path": file_i},
                                         app_state.config)
            sampling_rate, rawsong, onsets = (int(file_data["sampling_rate"]), file_data["song_data"],
                                              file_data["onsets"])
            app_state.data_dir = os.path.dirname(file_i)

            if onsets is None or len(onsets) == 0:
                skipped_no_segments += 1
                app_state.logger.warning("Skipping relabeling for '%s': no segments found.", file_i)
                continue

            labels = []

            for onset in onsets:
                onset_index = int(seconds_to_index(onset, sampling_rate))
                cutted_raw_song = rawsong[onset_index:onset_index + input_array_size]

                f, _, Sxx_taf = spectrogram(cutted_raw_song, fs=sampling_rate, nperseg=nperseg,
                                            noverlap=noverlap, nfft=nfft)
                Sxx_taf = Sxx_taf[(f >= lowcut) & (f <= highcut), :]
                Sxx_normalized = normalize_spectrogram(Sxx_taf)

                input_data = torch.tensor(Sxx_normalized).float().unsqueeze(0).unsqueeze(0).to(device)
                input_tensor = F.pad(input_data, (0, 1, 0, 1))

                with torch.no_grad():
                    output = model(input_tensor)
                    predicted_class = torch.argmax(output).item()
                labels.append(int_to_label[predicted_class])

            file_data["labels"] = ''.join(labels)
            save_notmat(os.path.join(app_state.data_dir, f"{file_data['file_name']}.not.mat"), file_data)
            processed_count += 1

        except Exception as e:
            app_state.logger.error(f"File {file_i} could not be processed correctly: {e}. Check manually.")
            failed_count += 1
            continue

    app_state.data_dir = original_data_dir
    app_state.song_files = original_song_files
    app_state.current_file_index = original_current_file_index

    invoke_in_main_thread(progressbar.setValue, len(all_files))

    invoke_in_main_thread(app_state.reset_edit_type)
    invoke_in_main_thread(plot_data, app_state)
    invoke_in_main_thread(progressbar.hide)

    if total_selected is None:
        total_selected = len(all_files)
    final_skipped = max(total_selected - processed_count - failed_count - skipped_no_segments, 0)

    summary = (
        "Relabeling completed.\n"
        f"Selected: {total_selected}\n"
        f"Processed: {processed_count}\n"
        f"Failed: {failed_count}\n"
        f"Skipped (no segments): {skipped_no_segments}\n"
        f"Skipped (total): {final_skipped}"
    )
    invoke_in_main_thread(lambda: show_info(
        app_state.relabel_window, "Info", summary))

.. _moovegui:

MooveGUI
========

The MooveGUI will let you work with your data, train networks on your segments and thereby classify the syllables in your songs. The MooveGUI can be started via Windows PowerShell using the command **moovegui.exe**.

|image12|

.. _setting-the-config-1:

Setting the config
------------------

Once you recorded data using MooveTaf, the folder **.moove** will be created, which contains your recorded data and trained models (see also 2.1. Baseline recordings). This folder also contains your moove_config.ini file, which can be opened and edited using any text editor program. In the section [GUI], highlighted in blue here, you can set parameters for the MooveGUI (Fig 14). It’s recommended to first start and look at the GUI for once and then come back to setting up the parameters as desired. The main window of the GUI is described in more detail in 3.2. Main window.

.. figure:: _static/images/image27.png
   :alt: A screenshot of a computer program AI-generated content may be incorrect.
   :width: 4.58397in
   :height: 3.19836in

   Figure 14: Config settings for the MooveGUI

The parameters that can be set in the config are described in the table below (Table 2).

.. table:: Table 2: Config settings for the MooveGUI

   +--------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | **Parameter**      | **Default Value** | **Description**                                                                                                                                                                               |
   +====================+===================+===============================================================================================================================================================================================+
   | upper_spec_plot    | 12500             | Upper frequency limit of the spectrogram shown in the main window of the GUI                                                                                                                  |
   +--------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | lower_spec_plot    | 500               | Lower frequency limit of the spectrogram shown in the main window of the GUI                                                                                                                  |
   +--------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | vmin_range_slider  | -140              | Lower limit of the sliders to adjust the visual parameters of the spectrogram                                                                                                                 |
   +--------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | vmax_range_slider  | -10               | Lower limit of the sliders to adjust the visual parameters of the spectrogram                                                                                                                 |
   +--------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | spec_nperseg       | 1024              | Defines the length of each segment for the STFT (short-time fourier transform). Shorter values lead to a better time, but a poorer frequency resolution.                                      |
   +--------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | spec_noverlap      | 896               | Specifies the number of points to overlap between segments in the STFT. The smaller, the less continuous the frequency information is displayed.                                              |
   +--------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | spec_nfft          | 1024              | Sets the number of points for the FFT (fast fourier transform) computation, determining the frequency resolution. Smaller values lead to a lower frequency resolution, calculation is faster. |
   +--------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | performance        | fast              | Defines how the spectrogram in the GUI is calculated. fast: more bleeding (imshow) vs slow: more details but slower (pcolomesh)                                                               |
   +--------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Main window
-----------

With the first-time start, an example file containing a labeled song bout will open (bout_1.wav) (Fig 15). The upper plot of the GUI shows the **spectrogram** of the song file (Fig 15, ①) and the lower plot the corresponding **amplitude trace** (Fig 15, ②). The axis in between contains syllable **labels** (Fig 15, ③) and will be empty if data has not been labeled yet. On the right you can find a slider to adjust the visual parameters of your spectrogram. The minimum and maximum range can be set in the config (see 3.1. Setting the config) and when adjusted manually the current slider settings will be saved when closing the GUI.

.. figure:: _static/images/image28.png
   :alt: Ein Bild, das Text, Screenshot, Display, Software enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 6.26806in
   :height: 3.69792in

   Figure 15: Main window of the MooveGUI

The top of the GUI contains a **navigation bar** (Fig 15, ④)(Fig 16), representing the current working path in your recorded data (*rec_data*), meaning bird folder (*bird_x*), experiment folder (*experiment_a*), day folder (*day_1*) and song file (*bout_1.wav*). In addition, the most-right drop-down menu shows the current batch file you’re working on (by default *batch.txt*).

.. figure:: _static/images/image29.png
   :width: 6.26806in
   :height: 0.42639in

   Figure 16: Navigation bar in the main window

The bottom row of the GUI contains multiple functional buttons to work on the current file (Fig 17). The **update** button ‘⟳‘ (Fig 17, ①) refreshes the GUI applying any changes performed on data folders and .rec files and updates each batch file. In case you are recording with MooveTaf on the same computer while working in the GUI, you can also press update to load your recently recorded files. The ‘\ **Previous**\ ’ and ‘\ **Next**\ ’ buttons (Fig 17, ②) enable switching between song files of one day. In case the file you are loading next contains a lot of data, the loading process might take a few seconds. The arrow buttons ‘\ **<**\ ’ and ‘\ **>**\ ’ (Fig 17, ③) let you move within the song file along the x-axis, which is especially helpful when zoomed in.

|Ein Bild, das Text, Screenshot, Display, Software enthält. KI-generierte Inhalte können fehlerhaft sein.|

Figure 17: Bottom row of the main window containing functional buttons

**Zooming** can be performed on either the spectrogram or the amplitude trace plot by dragging your cursor and will be signaled by a red box (Fig 18). A rather unspecific zoom into the data can be performed using the ‘\ **Zoom**\ ’ button, while ‘\ **Unzoom**\ ’ moves back to default, showing the whole file (Fig 17, ④). Note that ‘Zoom’ reduces the x-axis range by 30%, staying around the center of your current axis.

.. figure:: _static/images/image31.png
   :width: 6.25532in
   :height: 1.49541in

   Figure 18: Zooming

Once you zoomed in, you can ‘\ **Crop**\ ’ (Fig 17, ⑤) your file to the currently shown x-axis range. Before cropping up the area, you will be asked to confirm the operation, as this will **delete** any excess data. The file names will not be changed but the title in the .rec file will show the date when the file was changed.

In case you want to delete the current file (for example noise files), the ‘\ **Delete**\ ’ button (Fig 17, ⑥) will give you the option to either remove its entry from the current batch (blue box) or remove its .wav-file, .rec-file and .not.mat-file from the current folder (red box)(Fig 19). **Note that this option will remove the file completely from your disk!**

.. figure:: _static/images/image32.png
   :alt: Ein Bild, das Text, Screenshot, Display, Software enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 2.36927in
   :height: 1.64026in

   Figure 19: File delete options

The GUI will move on to the next file. In case you deleted the file from your disk, to remove the file entry from all your batch-files, simply press the **update** button. If you are working on the default batch file batch.txt, deleting the file 'from batch only’ will not delete it permanently from this batch, as restarting the GUI will refill the batch.txt file with every existing .wav file in the folder. When working on the batch.txt file, only the option ‘Delete file from disk’ will permanently delete it from this batch file. In any other batch file removal from the batch will be permanent.

The ‘\ **Play’** button will play back the sound of the current file (Fig 17, ⑦). This playback process cannot be stopped, so if you want to listen to a specific part of a long sound file, consider zooming in on the relevant section first. It will only play the data currently shown.

The buttons ‘\ **Resegment**\ ’, ‘\ **Relabel**\ ’, ‘\ **Training**\ ’ and ‘\ **Cluster**\ ’, as well as the options below (Fig 17, ⑧ ⑨ ⑩ ⑪), are used to train networks and classify syllables and will be explained in detail in the following chapters, including the usage of the upper right check boxes in the main window.

o

It is highly recommended to close the GUI using the ‘X’ in the upper right corner, as this will save all your current settings, including the current file number and slider settings. If any processes are still running in the background the MooveGUI will ask you if you are sure to close despite the running threads. However, after using the DashGUI (Chapter 3.4.3.) and closing the DashGUI via the ‘Close Dash GUI’ button in the Cluster Window, MooveGUI has still pending threads open and the confirmation window opens.

|A screenshot of a computer error message AI-generated content may be incorrect.|

In case you ever encounter an error when starting the GUI, such that it won’t open at all, head to your .moove folder and delete the app_state.json file. This should only be done if needed, as the index of the file you’re currently working on, as well as the slider settings will be set to default. However, all your immediate changes to a file, such as onset/ offset modification etc., will still be saved!

Syllable segmentation
----------------------

Segmenting a file
~~~~~~~~~~~~~~~~~

In the first step of the data preprocessing pipeline, the individual syllables in each bout of the raw audio data need to be segmented. The ‘\ **Resegment’** button in the main window of the GUI (Fig 17, ⑧) will open the *Resegmentation window*. On the left side of the window (red box), the segmentation method provided by *evfuncs* (Nicholson, 2021) is implemented (Fig 20). The four radio buttons *Current File, Current Day, Current Experiment and Current Bird* let you decide which files the segmentation method should be applied to. This is done relative to the currently selected file. Selecting the *Current Day* button will use all the files in the directory of the currently selected day, selecting the *Current Experiment* or *Current Bird* button ensures that all files in the respective subdirectories are used. For every selection, the respective **batch files** will become visible in the drop-down menu on the right (blue box). By default, *All files* from the respective directory will be used. Choosing a specific batch file in the menu will only feed files from this batch into the dataset. With that, you have the option to load specific files from multiple days or experiments. You can also perform segmentation solely on the *Current File*.

.. figure:: _static/images/image34.png
   :alt: Ein Bild, das Text, Screenshot, Zahl, Schrift enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 6in
   :height: 5.02083in

   Figure 20: Resegmentation window, segmenting files using evfuncs

For the segmentation process, you can define five parameters that are explained in the table below (Table 3). Each parameter has a given default value. Pressing the button ‘\ **Segment**\ ’ will start the segmentation process with the given parameters on the selected file(s), indicated by a green progress bar at the bottom of the window. This will determine syllable onsets and offsets in the raw audio data.

.. table:: Table 3: Resegmentation parameters for using evfuncs

   +-------------------------+----------------------+------------------------------------------------------------------------------------+
   | **Parameter**           | **Default Value**    | **Description**                                                                    |
   +=========================+======================+====================================================================================+
   | Threshold               | 10 [Decibel]         | Defines the threshold for detecting amplitude peaks as part of a syllable segment. |
   +-------------------------+----------------------+------------------------------------------------------------------------------------+
   | Min Syllable Duration   | 0.03 [seconds]       | Sets the minimum duration of a syllable that a syllable segment must have.         |
   +-------------------------+----------------------+------------------------------------------------------------------------------------+
   | Min Silent Duration     | 0.005 [seconds]      | Sets the minimum silence between two syllables to be counted as separate units.    |
   +-------------------------+----------------------+------------------------------------------------------------------------------------+
   | Frequency Cutoffs       | (500, 10000) [Hertz] | Determines the lower and upper cutoff frequencies of the bandpass filter.          |
   +-------------------------+----------------------+------------------------------------------------------------------------------------+
   | Smoothing Window        | 2 [milliseconds]     | Defines the size of the time window for smoothing the signal.                      |
   +-------------------------+----------------------+------------------------------------------------------------------------------------+

Once the process is done, you will be informed, and the *Resegmentation window* will close. The syllable onsets and offsets assigned by the algorithm will become visible in the amplitude trace of the main window (Fig 21). Each segment will be labeled ‘x’ by default, visible in the middle plot. Furthermore, onset and offset times will be added to the .not.mat-file of each song file the segmentation has been performed on.

.. figure:: _static/images/image35.png
   :alt: Ein Bild, das Text, Screenshot, Display, Reihe enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 6.2679in
   :height: 1.78681in

   Figure 21: Segmentation of a file

The algorithm-driven segmentation might not be entirely accurate; thus, you can adjust your segments using the *segmentation bar* (Fig 17, ⑫). The options **New Segment** (shortcut “n”), **Delete Segment** (shortcut “d”) and **Move Segment** (shortcut “m”) are implemented as a group of radio buttons on the lower control bar of the GUI. Each option of the bar can be accessed via a shortcut, by simply pressing the respective button on the keyboard. Switching to that option will become visible in the bar. The option **Label Interactive** is part of the classification process and will be explained later.

|image13|

If the **New Segment** option is selected, a syllable segment can be added with a left click for the onset and a right click for the offset in the area of the amplitude diagram. This segment is then temporarily labelled with the placeholder value ‘x’. Selecting the **Delete Segment** option allows you to delete an existing syllable segment in the amplitude diagram by clicking on it. You can also click on the corresponding label to delete it. The **Move Segment** option allows the user to left-click on the marker of an existing onset or offset point in the amplitude diagram. The marker will be highlighted in red. A right-click on the desired position will move it to this new position. You can mark files for which he has manually verified the segmentation using the **Segmented** checkbox in the upper right corner of the main window (Fig 15, ⑤). This will in the following steps give you the option to specifically train a network based on previous segmentation. This information will be saved in the corresponding .\ *rec* file of the current song file.

|Ein Bild, das Text, Screenshot, Display, Diagramm enthält. KI-generierte Inhalte können fehlerhaft sein.|\ |image14|

Create a Segmentation Training Dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As soon as enough bouts have been segmented, the segmentation network can be trained. The training network is recommended to be an iterative process. Therefore, few bouts are first segmented manually, and the segmentation network is trained. The trained network can then be used to segment a bout that has not been segmented yet. Even if the segmentation of this bout is not yet perfect, the corresponding bout can then be corrected more quickly by hand and included in the set of bouts for the training dataset. By that, you can train the network on more and more hand-corrected segmented files. To create a training dataset out of your segmented files, press the ‘\ **Training’** button (Fig.15, ⑩) in the GUI main window to open the *Training window*.

.. figure:: _static/images/image37.png
   :alt: Ein Bild, das Text, Screenshot, Zahl, Schrift enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 5.85525in
   :height: 5.45499in

   Figure 22: Creating a segmentation training dataset

The left part of the window is dedicated to the segmentation network, with the upper part enabling the creation of a training dataset (Fig 22, red box). With the upper four buttons you can choose which files to feed into the dataset. The options *Current Day*, *Current Experiment* and *Current Bird* will use all files in the respective subdirectories. For every selection, the respective **batch files** will become visible in the drop-down menu on the right (blue box). By default, *All files* from the respective directory will be used. Choosing a specific batch file in the menu will only feed files from this batch into the dataset. With that, you have the option to load specific files from multiple days or experiments. The option *Use Segmented Files Only* creates a dataset only containing the files in which the *segmentation checkmark* has been ticked (see above). This gives you the option to only feed files into the dataset that have already been manually checked or corrected. You must assign a name to the dataset in the *Training Dataset Name* field, the suffix *\_seg* will be added automatically. The *Chunk Size* field below defines the step size of how many audio samples are fed to the segmentation network during inference (default value = “64”). This enables the segmentation network a fast detection of onsets, as the duration of each audio chunk is about 1.45ms using a sampling rate of 44.1kHz. The input field named *Hist Size* specifies how many previous audio chunks are added during the inference of a new audio chunk in the segmentation network (default value = 3). The checkbox *Overlap Chunks* determines whether successive sequences of chunks should overlap in the training dataset. If selected, each new sequence is created containing chunks of the previous sequence. This will enlarge the training dataset as more overlapping data points are generated from the audio data. If the parameter is not selected, the sequences are created without overlapping so that each sequence is independent of the previous one. To avoid data leakage, this option should only be set if you feed **at least** **7** segmented files into the network. You cannot create empty datasets. Pressing the button **Create Training Dataset** will start the process, indicated as ‘\ *Looking for Segments*\ ’ and followed by a green progress bar at the bottom of the window. Once the dataset is created you will be informed, and the *Training window* will close. With that, the content of the dataset, *Chunk Size* and *Hist Size* will be saved to a *.pkl* file in the folder *training_data*.

Train the Segmentation Network
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once a segmentation training dataset is created, the segmentation network can be trained via the *Training window* (Fig 23, red box).

.. figure:: _static/images/image37.png
   :alt: Ein Bild, das Text, Screenshot, Zahl, Schrift enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 5.85525in
   :height: 5.45499in

   Figure 23: Training of the segmentation network

In the drop-down menu *Select Training Dataset* you can choose between your previously created training datasets. The parameters that can be set to train the network are explained in the table below (Table 4).

Note that we do not recommend downsampling if you’re especially interested in ‘repeats’ or if your dataset contains syllables that only occur very rarely.

.. table:: Table 4: Parameters for training the segmentation network

   +----------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | **Parameter**              | **Default Value** | **Description**                                                                                                                                                                    |
   +============================+===================+====================================================================================================================================================================================+
   | Downsampling               | True              | Balances the dataset by downsampling each label to have an equal number of samples.                                                                                                |
   +----------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Epochs                     | 1000              | Specifies the number of epochs for training the neural network.                                                                                                                    |
   +----------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Batch Size                 | 64                | Defines the number of samples that will be propagated through the network at once during training.                                                                                 |
   +----------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Learning Rate              | 0.001             | Controls the step size during the optimization process.                                                                                                                            |
   +----------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Early Stopping Patience    | 5                 | Sets the number of epochs without improvement of the validation data after which the training is terminated automatically. Higher early stopping patience can lead to overfitting. |
   +----------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

The *Start Training* button will train the segmentation network on the files from the selected training dataset. The training window will indicate the status of the training at the bottom, starting with ‘\ *Checking files*\ ’ for usability, switching to ‘\ *Training in Progress’* once you confirmed the start by pressing ‘\ *Ok*\ ’ and finally informing you when the training is finished, closing the *Training window*. The training progress can be observed in the terminal, where the current iteration of training (epoch) and the current accuracy of the network is shown (Fig 24).

.. figure:: _static/images/image38.png
   :alt: Ein Bild, das Screenshot, Muster, Stoff, Kunst enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 6.26806in
   :height: 2.43403in

   Figure 24: Iteration of training the network

The trained model can be found as a .\ *pth* file in the *trained_models* directory, as well as *\_mean.pt* and *\_std.pt*.

To train a network, at least **8 segments** must be defined in the given files. Furthermore, if the dataset consists of at least **7 segmented files**, the data will be split between files to form the training data, validation data and test data set. Splitting data by files prevents data leakage and provides more reliable accuracy results. However, you can still train a network on less than 7 files, for example if you have very long song files containing multiple bouts and segments. The GUI will ask you whether you want to continue with only a few files.

|Ein Bild, das Text, Elektronik, Screenshot, Display enthält. KI-generierte Inhalte können fehlerhaft sein.|

Pressing **Continue with few files** will train a network on these files (if they contain at least 8 segments) by not splitting between files. Therefore, training data, validation data and test data sets will contain segments from the same file. This is in general not recommended and accuracy values can be less reliable. Pressing **Cancel** will bring you back to the *training window.*

Resegment using the Trained Network
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once you have trained your segmentation network, you can use it to segment files. For that purpose, open the *Resegmentation window* using the **Resegment** button in the main window. On the right half, the trained network can now be parameterized and applied (Fig 25, red box). Again, the options *Current File,* *Current Day*, *Current Experiment* and *Current Bird* let you choose which files to resegment. For every selection, the respective **batch files** will become visible in the drop-down menu on the right (Fig 25, blue box). By default, *All files* from the respective directory will be used. Choosing a specific batch file in the menu will only feed files from this batch into the dataset. With that, you have the option to load specific files from multiple days or experiments. With the tickbox *Overwrite Already Segmented Files* you can decide whether files that have already been manually segmented (and marked as *Segmented*, see above) should be overwritten and segmented by the network. Ticking the box will enable resegmentation of these files. In the drop-down menu *Select Trained Segmentation Model* you can select the desired trained segmentation model. Its content is generated from all saved segmentation models in the *trained_models* directory.

.. figure:: _static/images/image34.png
   :alt: Ein Bild, das Text, Screenshot, Zahl, Schrift enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 5.32253in
   :height: 4.45392in

   Figure 25: Resegment using the training segmentation network

The resegmentation parameters can be adjusted below and are explained in the following table (Table 5). Eventually, pressing the **Segment** button at the bottom of the window will start the resegmentation process of the selected files, indicated by a green progress bar at the bottom of the window. Once all files are resegmented, you will be informed and the *Resegmentation window* will close.

.. table:: Table 5: Parameters for resegmenting using a trained network

   +---------------------+--------------------+--------------------------------------------------------------------------------------+
   | **Parameter**       | **Default Value**  | **Description**                                                                      |
   +=====================+====================+======================================================================================+
   | Decision Threshold  | 0.5 [%]            | Defines a probability threshold for detecting a syllable segment.                    |
   +---------------------+--------------------+--------------------------------------------------------------------------------------+
   | Onset Window Size   | 5 [chunks]         | Specifies the size of the sliding window used to detect onsets.                      |
   +---------------------+--------------------+--------------------------------------------------------------------------------------+
   | N Onset True        | 3 [chunks]         | Sets the number of *True* detections within the sliding window.                      |
   +---------------------+--------------------+--------------------------------------------------------------------------------------+
   | Offset Window Size  | 5 [chunks]         | Specifies the size of the sliding window used to detect offsets.                     |
   +---------------------+--------------------+--------------------------------------------------------------------------------------+
   | N Offset False      | 4 [chunks]         | Sets the number of *False* detections within the sliding window.                     |
   +---------------------+--------------------+--------------------------------------------------------------------------------------+
   | Min Syllable Length | 0.03 [seconds]     | Specifies the minimum duration of a syllable that a syllable segment must have.      |
   +---------------------+--------------------+--------------------------------------------------------------------------------------+
   | Min Silent Duration |    0.005 [seconds] | Specifies the minimum silence between two syllables to be counted as separate units. |
   +---------------------+--------------------+--------------------------------------------------------------------------------------+

Label Clustering
----------------

Create a Cluster Training Dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To obtain the syllable labels for the training dataset of the classification network, the dimensionality reduction method UMAP is used together with a clustering algorithm. The input for UMAP consists of the individual spectrograms of the identified syllable segments. For this purpose, a cluster dataset containing the spectrograms of the syllable segments needs to be created, which can be done in the *Cluster window*, available via the **Cluster** button in the main window (Fig 17, 11).

|Ein Bild, das Text, Screenshot, Zahl, Schrift enthält. KI-generierte Inhalte können fehlerhaft sein.|

Figure 26: Creating a cluster training dataset

In the upper part of the window (Fig 26, red box), the options *Current File, Current Day, Current Experiment* and *Current Bird* define the files the clusters will be created from. For every selection, the respective **batch files** will become visible in the drop-down menu on the right (Fig 26, blue box). By default, *All files* from the respective directory will be used. Choosing a specific batch file in the menu will only feed files from this batch into the dataset. With that, you have the option to load specific files from multiple days or experiments. The checkbox **Use segmented files only** targets only files that have already been manually segmented (and marked as *Segmented*, see above). You must assign a name in the *Cluster Dataset Name* field, the suffix *\_clus* will be added automatically. The adjustable parameters will be used in the spectrogram calculation and are described in the table below.

.. table:: Table 6: Parameters for creating a cluster dataset

   +-------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | **Parameter**     | **Default Value** | **Description**                                                                                                                                                                               |
   +===================+===================+===============================================================================================================================================================================================+
   | Nperseg           | 64                | Defines the length of each segment for the STFT (short-time fourier transform). Shorter values lead to a better time, but a poorer frequency resolution.                                      |
   +-------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Noverlap          | 32                | Specifies the number of points to overlap between segments in the STFT. The smaller, the less continuous the frequency information is displayed.                                              |
   +-------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | NFFT              | 128               | Sets the number of points for the FFT (fast fourier transform) computation, determining the frequency resolution. Smaller values lead to a lower frequency resolution, calculation is faster. |
   +-------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Frequency Cutoffs | 0,22050 [Hertz]   | Defines the lower and upper cutoff frequency for filtering the spectrogram.                                                                                                                   |
   +-------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Pressing the button Create Cluster Dataset will start the process, indicated by a green process bar at the bottom of the *Cluster window*. Once the clustering is done, you will be informed, and the *Cluster window* will close. The dataset will be saved as *.pkl* file in the *cluster_data* folder.

Cluster Syllables
~~~~~~~~~~~~~~~~~~

Once the cluster dataset is created, the dimensionality reduction using UMAP can be started. For that, the created dataset can be selected in the lower part of the *Cluster window* (Fig 27, red box).

.. figure:: _static/images/image40.png
   :alt: Ein Bild, das Text, Screenshot, Zahl, Schrift enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 4.1875in
   :height: 6.21875in

   Figure 27: Clustering of syllables

Below, the input parameters for the UMAP algorithm and the following k-Means algorithm can be set (Table 7). The button **Cluster Syllables** will start the process, indicated by the ‘\ *Running*\ ’ label at the bottom of the window.

.. table:: Table 7: Parameters for clustering syllables

   +---------------+-------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | **Parameter** | **Default Value** | **Description**                                                                                                                                             |
   +===============+===================+=============================================================================================================================================================+
   | N neighbors   | 15                | Determines the number of nearest neighbors *k* when constructing the high-dimensional graph.                                                                |
   +---------------+-------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Min dist      | 0.1               | Controls the minimum distance between points in the low-dimensional space. A smaller value leads to denser clusters.                                        |
   +---------------+-------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | N Syllables   | 10                | Defines the number of syllable clusters to be formed for the k-Means algorithm. Re-adjust if the number of clusters created is not the yellow from the egg. |
   +---------------+-------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+

Once the clustering is completed, the results will be saved to the .\ *pkl* file, together with a same-named .\ *png* file of the 2D UMAP space containing the syllable clusters. An interactive version of the UMAP clustering can be opened with the button **Open Dash GUI**, which will start in a separate thread in your browser.

.. figure:: _static/images/image41.png
   :alt: Ein Bild, das Text, Screenshot, Karte, Diagramm enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 5.83074in
   :height: 5.06495in

   Figure 28: Dash GUI containing your syllable clusters

Dash GUI
~~~~~~~~

Each colored cluster in the space represents one classified syllable type, each dot represents one syllable. The clusters will be labeled with letters, starting at ‘\ *a*\ ’. The Dash GUI offers multiple ways to interact with the data and to reassign the cluster membership of the data points as desired. In the tool bar located in the upper right corner (Fig 28, red box), you can activate the **zoom** tool (Fig 29, 2) to closely inspect the data, **move** around (Fig 29, 3) the plot or **zoom in and out** (Fig 29, 6+7) more directly. The **autoscale** button (Fig 29, 8) will move the plot to your clusters position and **reset axes** (Fig 29, 9) will reset the plot. The **save** button (Fig 29, 1) will save the plot as a .\ *png* file.Also, **double clicking** the plot will zoom out, autoscale to your clusters position and remove any existing selection boxes. To relabel specific data points, the option **Box Select** (Fig 29, 4) lets you draw a box around a specific set of dots, and **Lasso Select** (Fig 29, 5) lets you draw a free form.

|image15|

Figure 29: Options in the Dash GUI

Once you selected points, you can relabel these points directly by typing the new label into the *Label for selected points* field at the left bottom of the Dash window (Fig 28, orange box). Pressing the **Apply** button will change the label of the selected points and depending on the letter distance to the other syllables, the color space is adjusted, possibly leading to a different color mapping than before. Furthermore, you can change all dots from one label at once, by typing the current label of the cluster in the *Change all labels from* filed, and the new desired label in the *to:* field next to it. Pressing **Change All** will change the label of this cluster. In the lower right corner, the buttons **Increase Point Size** and **Decrease Point Size** give you the option to change the dot size for better visibility. When you applied your desired changes, press the **Save** button in the middle bottom part of the Dash GUI to overwrite your previous cluster data. Saving the data will be indicated by a message showing up in the MooveGUI. Once you’re done, press the **Close Dash GUI** button in the *Cluster window* of the MooveGUI. This will shut down the Dash server and you can then close the browser window. The Dash GUI **must be closed** using the **Close Dash GUI** button before it can be reopened, as the server will not be available otherwise.

Finally, you can apply your newly acquired syllable labels to your data by pressing the button **Replace Labels** in the *Cluster window*. This will replace all previous placeholder labels ‘x’ (or other labels) in the *.not.mat* files that have been fed into the dataset (as defined in *Create a Cluster Training Dataset*) and the new labels will appear in the GUI.

Syllable classification
-----------------------

Create a Classification Training Dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Although the classification by the process with UMAP, k-Means and a following manual adjustment of the cluster memberships is very accurate, individual syllables can be classified incorrectly. You can semi-manually review all files and correct any mislabelled syllables using the *Label Interactive* option in the main window (Fig 17, 12). To do so, clicking on the label you want to change will highlight it in red, and typing on your keyboard will replace it. Valid label characters are basic letters and numbers (no capital letters and special characters). After relabeling one syllable, the highlight jumps to the next syllable, enabling continuous relabeling till the end of the file. Corrected labels get automatically saved in the *.not.mat* file of the corresponding bout. Analogous to the procedure for the segmentation network, you can use the **Classified** checkbox in the top right corner (5, see above) to mark these files. This information will be saved in the corresponding .\ *rec* file of the current song file. Note that while you are in the *Label interactive* mode, using shortcuts to switch modes is not possible, as the keys will be used for relabelling.

Once you all labels are correct, a training dataset can be created in the right upper part of the *training window* (Fig 17, 10)(Fig 30, red box). With the upper four buttons you can choose which files to feed into the dataset. The options *Current Day*, *Current Experiment* and *Current Bird* will jump to the respective folder direction and load all batch files found in those. For every selection, the respective **batch files** will become visible in the drop-down menu on the right (blue box). By default, *All files* from the respective directory will be used. Choosing a specific batch file in the menu will only feed files from this batch into the dataset. With that, you have the option to load specific files from multiple days or experiments. The option *Use Classified Files Only* creates a dataset only containing the files in which the *classification checkmark* has been ticked (see above). This gives you the option to only feed files into the dataset that have already been manually checked or corrected. You must assign a name to the dataset in the *Training Dataset Name* field, the suffix *\_class* will be added automatically.

|image16|

Figure 30: Creating a classification training dataset

The training dataset for the classification network is generated from the spectrogram data of the individual syllable segments and their corresponding syllable label. For the classification network, only a fixed time interval after a detected onset is used as input (*N Input Chunks/Size*). This parameter can be set below among others, as described in the table below (Table 8). You cannot create empty datasets.

.. table:: Table 8: Parameters for creating a classification training dataset

   +---------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | **Parameter**       | **Default Value** | **Description**                                                                                                                                                                               |
   +=====================+===================+===============================================================================================================================================================================================+
   | N Input Chunks/Size | 21,64             | Length of time interval after onset that is used as input for classification (~30.48 ms at 44.1kHz)                                                                                           |
   +---------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Nperseg             | 64                | Defines the length of each segment for the STFT (short-time fourier transform). Shorter values lead to a better time, but a poorer frequency resolution.                                      |
   +---------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Noverlap            | 32                | Specifies the number of points to overlap between segments in the STFT. The smaller, the less continuous the frequency information is displayed.                                              |
   +---------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | NFFT                | 128               | Sets the number of points for the FFT (fast fourier transform) computation, determining the frequency resolution. Smaller values lead to a lower frequency resolution, calculation is faster. |
   +---------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Frequency Cutoffs   | 0,22050 [Hertz]   | Defines the lower and upper cutoff frequency for filtering the spectrogram.                                                                                                                   |
   +---------------------+-------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Pressing the button **Create Training Dataset** will start the process, indicated as ‘\ *Looking for Syllables’* and followed by a green progress bar at the bottom of the window. Once the dataset is created you will be informed, and the *Training window* will close. With that, the content of the dataset will be saved to a .\ *pkl* file in the *training_data* folder.

Training the Classification Network
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once a classification training dataset is created, the classification network can be trained via the *Training window* (Fig 31, red box).

.. figure:: _static/images/image43.png
   :alt: Ein Bild, das Text, Screenshot, Zahl, Schrift enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 5.77936in
   :height: 5.3843in

   Figure 31: Training the classification network

In the drop-down menu *Select Training Dataset* you can choose between your previously created training datasets. The parameters that can be set to train the network are explained in the table below.

We do not recommend downsampling if you’re especially interested in ‘repeats’ or if your dataset contains syllables that only occur very rarely.

.. table:: Table 9: Parameters for training the classification network

   +-------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | **Parameter**           | **Default Value** | **Description**                                                                                                                                                                    |
   +=========================+===================+====================================================================================================================================================================================+
   | Downsampling            | True              | Balances the dataset by downsampling each label to have an equal number of samples.                                                                                                |
   +-------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Epochs                  | 1000              | Specifies the number of epochs for training the neural network.                                                                                                                    |
   +-------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Batch Size              | 64                | Defines the number of samples that will be propagated through the network at once during training.                                                                                 |
   +-------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Learning Rate           | 0.001             | Controls the step size during the optimization process.                                                                                                                            |
   +-------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Early Stopping Patience | 5                 | Sets the number of epochs without improvement of the validation data after which the training is terminated automatically. Higher early stopping patience can lead to overfitting. |
   +-------------------------+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

The *Start Training* button will train the classification network on the files from the selected training dataset. The start of the training requires confirmation via pressing the ‘\ *OK*\ ’ button. The training window will indicate the status of the training at the bottom, starting with ‘\ *Checking files*\ ’ for usability, switching to ‘\ *Training in Progress’* once the training has started and finally informing you when the training is finished and closing the *Training window*. The trained model can be found as a .\ *pth* file in the *trained_models* directory, together with a .\ *svg* file containing the classification matrix. This matrix shows the performance of the network as the accuracy of the predictions for each type of syllable on the test subset.

.. figure:: _static/images/image44.jpg
   :alt: Ein Bild, das Text, Screenshot, Zahl, parallel enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 4.12631in
   :height: 3.31276in

   Figure 32: Example classification matrix

To train a network, at least **6 syllables per syllable type** must be defined in the given files. Furthermore, if the dataset consists of at least **7 classified files**, the data will be split between files to form the training data, validation data and test data set. Splitting data by files prevents data leakage and provides more reliable accuracy results. However, you can still train a network on less than 7 files, for example if you have very long song files containing multiple bouts and syllables. The GUI will ask you whether you want to continue with only a few files.

|Ein Bild, das Text, Elektronik, Screenshot, Display enthält. KI-generierte Inhalte können fehlerhaft sein.|

Pressing **Continue with few files** will train a network on these files (if they contain at least 6 syllables per syllable type) by not splitting between files. Therefore, training data, validation data and test data sets will contain syllables from the same file. This is in general not recommended and accuracy values can be less reliable. Pressing **Cancel** will bring you back to the *training window.*

Relabel Data
~~~~~~~~~~~~

Lastly, you can apply your trained classification network on already labeled data by opening the *Relabel window* using the **Relabel** button in the main window (Fig 17, 9)(Fig 33). Again, the four upper buttons define which files should be relabeled by going into the respective subdirectories, including the selection of a specific batch file (blue box). By default, *All Files* of your selection will be used. With the tickbox *Overwrite Already Segmented Files* you can decide whether files that have already been manually classified (and marked as *Classified*, see above) should be overwritten and classified by the network. Ticking the box will enable relabeling of these files. In the drop-down menu *Select Trained Classification Model* you can select the desired trained classification model. Its content is generated from all saved classification models in the *trained_models* directory. When pressing the **Relabel** button, the replacement of labels will be started indicated by a green progress bar at the bottom of the *Relabel* window. Once all labels are replaced, you will be informed and the *Relabel window* will be closed.

.. figure:: _static/images/image45.png
   :alt: Ein Bild, das Text, Screenshot, Schrift, Display enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 2.84999in
   :height: 2.21193in

   Figure 33: Relabel data using the classification network

.. |A screenshot of a computer error message AI-generated content may be incorrect.| image:: _static/images/image33.png
   :width: 2.80247in
   :height: 1.61481in
.. |Ein Bild, das Text, Elektronik, Screenshot, Display enthält. KI-generierte Inhalte können fehlerhaft sein.| image:: _static/images/image39.png
   :width: 3.09734in
   :height: 1.68812in
.. |Ein Bild, das Text, Screenshot, Display, Diagramm enthält. KI-generierte Inhalte können fehlerhaft sein.| image:: _static/images/image36.png
   :width: 2.19167in
   :height: 0.33472in
.. |Ein Bild, das Text, Screenshot, Display, Software enthält. KI-generierte Inhalte können fehlerhaft sein.| image:: _static/images/image30.png
   :width: 6.25278in
   :height: 0.625in
.. |Ein Bild, das Text, Screenshot, Zahl, Schrift enthält. KI-generierte Inhalte können fehlerhaft sein.| image:: _static/images/image40.png
   :width: 4.1875in
   :height: 6.21875in
.. |image12| image:: _static/images/image26.png
   :width: 6.26806in
   :height: 1.25625in
.. |image13| image:: _static/images/image30.png
   :width: 6.25277in
   :height: 0.23958in
.. |image14| image:: _static/images/image28.png
   :width: 2.24583in
   :height: 0.32708in
.. |image15| image:: _static/images/image42.png
   :width: 3.03958in
   :height: 0.44028in
.. |image16| image:: _static/images/image43.png
   :width: 4.87272in
   :height: 4.53963in

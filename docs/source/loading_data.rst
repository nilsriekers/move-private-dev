.. _loading-data:

Loading previously recorded data
================================

In case you previously recorded song data with EvTAF (Tumer & Brainard, 2007), or with any other program producing either
``.wav`` or ``.cbin`` files, they can be loaded into the MooveGUI as well. The only requirement is a respective ``.rec`` and ``.not.mat`` file for each song file.

Furthermore, the ``.rec`` file needs to be slightly modified to be processed correctly. The lines including the parameters **Hand Segmented** and **Hand Classified** (see section *REC file and Feedback Information*) 
need to be added. 
This can be done easily with a self-written python script, inserting the two lines at the specific positions. If you are unsure about how to do this, feel free to contact us.

Eventually, if not done so before, move the data folder into your *rec_data* folder in ``.moove`` (pay attention to the correct folder structure, see section *MooveTAF*) and start the MooveGUI. 
Note that in order to show feedback and catch trials correctly, the info lines in the ``.rec`` files must be formatted identically to the ones created by MooveTaf (see section *REC file and Feedback Information*).

As your old files will presumably contain different dB-values, you might want to adjust the slider values to correctly display the spectrogram (see section *MooveGUI*).


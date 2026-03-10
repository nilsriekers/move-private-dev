.. _faq:

FAQ
===

What if my segmentation looks ugly?
-----------------------------------

Case: Repeats
~~~~~~~~~~~~~

Offline segmentation
^^^^^^^^^^^^^^^^^^^^

Figure 38: Example cases for repeat segmentation.

For that, you first have to hand-segment the repeats in the correct manner, create a dataset and train a network using the *training* window (3.3 Train the segmentation network) on ‘\ **Segmented files only**\ ’ (Fig 39, red box). Ensure that downsampling is **NOT activated** to capture every single repeat syllable. Adjusting the parameter Batch Size would allow you to change the number of audio chunks, but decreasing could easily lead to incorrect segmentation.

.. figure:: _static/images/image37.png
   :alt: Ein Bild, das Text, Screenshot, Zahl, Schrift enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 3.64977in
   :height: 3.40028in

   Figure 39: Training window

Once the network is trained, you can adjust the parameters for onset and offset detection parameters as described above when resegmenting your files (3.3 Resegment using the trained network). Also, adjusting the *min syllable length* and *min silent duration* can increase segmentation accuracy. Always make sure to **NOT tick the box saying ‘Overwrite already segmented files’** to preserve your hand-corrected data.

.. figure:: _static/images/image34.png
   :alt: Ein Bild, das Text, Screenshot, Zahl, Schrift enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 3.73128in
   :height: 3.12236in

   Figure 40: Resegmentation window

Once all parameters are adjusted, the repeat syllables should be segmented correctly. In this example case, parameters were set as follows.

|image17|

.. figure:: _static/images/image54.png
   :alt: Ein Bild, das Text, Screenshot, Majorelle Blue, Reihe enthält. KI-generierte Inhalte können fehlerhaft sein.
   :width: 5.85849in
   :height: 3.40039in

   Figure 41: Example case for repeat segmentation.

Online classification
^^^^^^^^^^^^^^^^^^^^^

Online classification of syllables is per default performed within 30ms after syllable onset. In case you want to perform online classification on such very short syllables, you can reduce this time window. For that, you can change the size of audio chunks processed at once, as well as the number of input chunks (Fig 39, blue box). Per default, audio chunks have a size of 64 and 21 input chunks are processed. With a sampling frequency of 44100Hz and therefore a chunk duration of 1.45ms, the online classification for one syllable takes 1.45ms x 21 = 30.45ms. Adjusting these parameters can decrease this time but might reduce accuracy. Onsets and offsets of syllables shorter than 30ms will still be detected correctly with default parameters.

I can’t find my .moove folder, where is it?
-------------------------------------------

Per default, your .moove folder will be saved directly in your user folder. However, folders with names starting with a ‘.’ are per default hidden under Linux and MacOS. On MacOS, they can be made visible pressing CMD + shift + . while in your user folder, on Linux it can be done using Ctrl + H. The folder location can be moved as described in *2. MooveTAF*.

I want to use my trained models on a Linux computer, but they are in a .zip folder?
-----------------------------------------------------------------------------------

On Linux, when copying the models, they will appear as a .zip folder. However, you can simply extract the files, which will leave you with a folder you can ignore and the desired *model.pth* files. The path to these two files can then be put into the config for online classification.

6.4. Why does my data look like this?

|image18|

If you can’t recognize your song nicely in the GUI, or you don’t see anything in the spectrogram at all, you most likely have to adjust your sliders, as the dB-values will be incompatible with the default values. This can be done in the config-file (see 3. Setting the config). Especially cbin-files will need some adjustments, we had the best results with sliders between +40 and +100. If you can’t find any values that work for your data, feel free to contact us.

.. |image17| image:: _static/images/image53.png
   :width: 2.36244in
   :height: 1.56604in
.. |image18| image:: _static/images/image55.png
   :width: 3.90075in
   :height: 2.062in

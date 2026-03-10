.. _faq:

FAQ
===

Installation & setup
--------------------

Which Python version should I use?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Moove supports Python 3.9 through 3.12.  We recommend **Python 3.11**
as it has been tested most extensively.

Do I still need Tkinter?
~~~~~~~~~~~~~~~~~~~~~~~~

No.  Moove now uses **PyQt6** for its GUI.  The previous dependency on
Tkinter (and the related packages ``ttkbootstrap`` / ``ttkwidgets``) has
been removed.  If you see old instructions mentioning ``python3-tk`` or
``import tkinter``, you can safely ignore them.

I get "No module named sounddevice" or a PortAudio error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``sounddevice`` requires the **PortAudio** C library at runtime.

- **Windows**: PortAudio is bundled with the pip package -- a simple
  ``pip install sounddevice`` should be enough.
- **macOS**: Install PortAudio via Homebrew first:
  ``brew install portaudio``
- **Linux**: Install the development package:
  ``sudo apt install portaudio19-dev``

After installing the system library, reinstall sounddevice:
``pip install --force-reinstall sounddevice``.

How do I enable ASIO on Windows?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set the environment variable ``SD_ENABLE_ASIO=1`` before starting Moove.
In PowerShell:

.. code-block:: powershell

   $env:SD_ENABLE_ASIO = "1"
   moovegui

See :ref:`asio-setup` in the Installation chapter for more details,
including the legacy manual DLL-replacement method.

NumPy 2.x -- is it supported?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Moove no longer pins an upper bound on NumPy.  In most cases NumPy 2.x
works fine, but some edge cases (especially around integer-type
behaviour changes in NumPy 2.0) may surface.  If you encounter
unexpected errors, try pinning NumPy < 2:

.. code-block:: bash

   pip install "numpy<2"

Poetry errors during installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Moove has migrated from Poetry to **uv** / **hatchling**.  If you cloned
an older version of the repository that still uses ``poetry.lock``, pull
the latest changes and use ``uv sync`` instead.  For pip installations,
nothing changes -- ``pip install moove`` continues to work as before.


Using MooveGUI
--------------

What if my segmentation looks ugly?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Case: Repeats
^^^^^^^^^^^^^

Offline segmentation
""""""""""""""""""""

.. figure:: _static/images/image37.png
   :alt: Training window
   :width: 3.64977in

   Figure: Training window settings.

For repeat segmentation, first hand-segment the repeats correctly, then
create a dataset and train a network using the *Training* window (see
*Train the segmentation network*) on **Segmented files only**.  Ensure
that downsampling is **not activated** to capture every single repeat
syllable.

Once the network is trained, adjust the onset/offset detection
parameters when resegmenting your files.  The *min syllable length* and
*min silent duration* parameters can improve accuracy.  Always make sure
to **not** tick "Overwrite already segmented files" to preserve your
hand-corrected data.

.. figure:: _static/images/image34.png
   :alt: Resegmentation window
   :width: 3.73128in

   Figure: Resegmentation window.

Example parameters for repeat segmentation:

.. image:: _static/images/image53.png
   :width: 2.36244in

.. figure:: _static/images/image54.png
   :alt: Example repeat segmentation
   :width: 5.85849in

   Figure: Correctly segmented repeats after parameter adjustment.

Online classification
"""""""""""""""""""""

Online classification of syllables is performed within 30 ms after
syllable onset by default.  You can reduce this window for very short
syllables by changing the audio chunk size and number of input chunks in
the Training window.  With default parameters (chunk size 64 at
44.1 kHz, 21 input chunks) the classification latency is
1.45 ms × 21 ≈ 30 ms.  Adjusting these parameters can decrease
latency but may reduce accuracy.

I can't find my .moove folder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``.moove`` folder is created in your home directory on first start.
Folders beginning with ``.`` are hidden by default on Linux and macOS:

- **macOS**: Press ``Cmd + Shift + .`` in Finder
- **Linux**: Press ``Ctrl + H`` in your file manager

The folder location can be changed -- see *MooveTAF* for details.

I want to use trained models on Linux but they appear as .zip
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When copying model files from Windows to Linux they may appear as
``.zip`` archives.  Simply extract them; the resulting ``.pth`` files
can be used directly in the config.

My spectrogram looks wrong or is empty
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: _static/images/image55.png
   :width: 3.90075in

If the spectrogram is not visible or the song is hard to recognise, the
dB slider range is likely incompatible with your data.  Adjust the vmin/vmax
sliders on the right side of the GUI, or set initial values in the
config file (see *Setting the config*).  For ``.cbin`` files, slider
values between +40 and +100 often work well.

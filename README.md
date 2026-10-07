# Looming Test

A Windows application for presenting visual looming stimuli to mice and logging trial timing to CSV.

> **Status:** Review / Test Version  
> This software is currently under validation. Please verify its behavior in your experimental setup before using it for data collection.

## Overview

Looming Test is a custom Windows application designed to present visual looming stimuli in mouse behavioral experiments.

The stimulus design was based on the visual-looming shadow protocol described by Daviu et al. (2020).

The application provides:

- Presentation of a visual looming stimulus
- Physical-size calibration using a 10-cm calibration bar
- Trial and session control
- Mouse ID entry
- CSV event logging
- Software hotkey synchronization with Bandicam

## Requirements

- Windows PC
- A stimulus display connected as an extended monitor
- Bandicam, when video recording synchronization is required
- A ruler for physical-size calibration

## Experimental Setup

Before starting:

1. Set Windows to **Extend** display mode.
2. In Windows display settings, place the stimulus monitor to the **right of the PC display**.
3. Open Bandicam and set the **Record/Stop hotkey to F12**.
4. Select the CSV output folder using **SELECT CSV FOLDER**.
5. Perform the 10-cm physical-size calibration.
6. Enter the **Mouse ID** before starting recording.

## Display Calibration

The application uses a 10-cm calibration bar to adjust the physical size of the stimulus.

1. Display the 10-cm calibration bar.
2. Measure the displayed bar with a ruler.
3. Enter the measured value into the application.
4. Click **APPLY & SAVE**.
5. Confirm that the final displayed length is **10.0 cm**.

Repeat the calibration whenever the monitor or display configuration is changed.

Different monitor sizes and resolutions can be accommodated using this calibration procedure.

If the distance between the stimulus monitor and the test floor is changed, the programmed stimulus size should be reconsidered.

## Basic Operation

| Key / Button | Action |
|---|---|
| **F9 / START RECORDING / TIME 0** | Start Bandicam recording and define the application's Time 0 |
| **SPACE / TRIGGER LOOMING** | Present one looming stimulus |
| **Ctrl + R / NEW SESSION / RESET** | Start a new session and reset the trial count and Time 0 |
| **ESC** | Quit the application |
| **STOP BANDICAM RECORDING** | Send F12 to stop Bandicam recording |

## Current Stimulus Parameters

The current version uses the following settings:

- Maximum: **5 trials per session**
- One trigger presents one looming stimulus
- Background: **gray (RGB 128, 128, 128)**
- The stimulus disk is centered on the stimulus display

For the current setup with a monitor-to-test-floor distance of **25.5 cm**, the disk diameter is set to approximately:

**1.7 cm → 17.0 cm**

This was scaled from the **2 cm → 20 cm** stimulus described by Daviu et al. (2020) for a 30-cm monitor height, using a distance ratio of 0.85.

### Stimulus sequence

1. Small disk: **3 s**
2. Expansion: **2 s**
3. Large disk: **3 s**
4. Return to gray screen

## CSV Output

The application records information including:

- Mouse ID
- Session ID
- Trial number
- Event
- Application video time
- Date and time
- Calibration scale
- Configured monitor-to-floor distance
- Programmed disk diameters

Looming onset and end are logged for each trial.

## Important Notes

Bandicam synchronization is performed using software hotkeys.

**The application is not hardware-synchronized or frame-locked to the video recording.**

Users should verify that the timing accuracy is sufficient for their behavioral analysis before experimental use.

This version should currently be treated as a **review / test version**. Please check for unexpected behavior before using it for experimental data collection.

## Repository Structure

```text
Looming-Test/
├── src/       # Python source code
├── docs/      # User guides and documentation
├── assets/    # Application assets and icon
├── .gitignore
└── README.md

```

## Documentation

Detailed English and Japanese user guides are available in the `docs` directory.

## Reference

The visual looming stimulus design was based on:

Daviu, N., Fuzesi, T., Rosenegger, D. G., Peringod, G., Simone, K., & Bains, J. S. (2020).  
Visual-looming Shadow Task with in-vivo Calcium Activity Monitoring to Assess Defensive Behaviors in Mice.  
*Bio-protocol, 10*(22), e3826.  
DOI: 10.21769/BioProtoc.3826

The original protocol also refers to the `kpc-simone/shadow-graphics` repository for Python code used to create the visual stimulus.

## Citation

Citation information for this software will be added upon public release.

## License

A software license has not yet been assigned.

Please do not redistribute or reuse the software until the licensing terms are specified.

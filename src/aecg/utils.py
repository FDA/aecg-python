""" Utility functions for annotated ECG HL7 XML tools

This submodule provides utility functions such as basic printing and plotting.


See authors, license and disclaimer at the top level directory of this project.

"""

import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from enum import Enum
from matplotlib import figure


# Python logging ==============================================================
logger = logging.getLogger(__name__)


class ECG_plot_layout(Enum):
    """Supported plot layouts

    Args:
        Enum: Type of plot layout
    """

    #: Leads stacked vertically
    STACKED = 1

    #: Leads organized in 3 x 4 matrix with full lead II at the bottom
    THREExFOURxRHYTHM = 2

    #: Leads superimposed on top of each other (a.k.a., butterfly plot)
    SUPERIMPOSED = 3


def plot_aecg(rhythm_data: pd.DataFrame,
              anns_df: pd.DataFrame = None,
              ecgl_plot_layout: ECG_plot_layout = ECG_plot_layout.STACKED,
              fig: figure.Figure = None,
              dpi: int = 300,
              textsize: int = 6,
              ecg_linewidth: float = 0.3,
              plot_grid: bool = True,
              grid_color: str = "#a88332",
              v_offset: float = 1.5,
              xmin: float = 0.0, xmax: float = 10000.0,
              ymin: float = -1.5, ymax: float = 1.5,
              x_margin: float = 280,
              for_gui: bool = True) -> figure.Figure:
    """Plots the `rhythm_data` waveform and `anns_df` annotations

    Args:
        rhythm_data (pd.DataFrame): aECG waveform as returned by
            :any:`Aecg.rhythm_as_df` or :any:`Aecg.derived_as_df`.
        anns_df (pd.DataFrame, optional): aECG annotations. For example,
            as returned by pd.DataFrame(the_aecg.DERIVEDANNS[0].anns) where
            the_aecg is an :any:`Aecg` object. Defaults to None.
        ecgl_plot_layout (ECG_plot_layout, optional): Plot layout. Defaults to
            ECG_plot_layout.STACKED.
        fig (figure.Figure, optional): Figure containing the plot. Defaults to
            None.
        dpi (int, optional): Plot resolution in dots per inch (dpi). Defaults
            to 300.
        textsize (int, optional): Default text fontsize. Defaults to 6.
        ecg_linewidth (float, optional): Line width for the ECG waveform.
            Defaults to 0.3.
        plot_grid (bool, optional): Indicates whether to plot the standard ECG
            grid. Defaults to True.
        grid_color (str, optional): Color of the ECG grid. Defaults to
            "#a88332".
        v_offset (float, optional): Vertical offset between leads in mV.
            Defaults to 1.5.
        xmin (float, optional): X axis minimum value in ms. Defaults to 0.0.
        xmax (float, optional): X axis maximum value in ms. This value may be
            adjusted automatically when maintaining aspect ratio. Defaults to
            10000.0.
        ymin (float, optional): Y axis minimum value in mV. Defaults to -1.5.
        ymax (float, optional): Y axis maximum value in mV. This value may be
            adjusted automatically when maintaining aspect ratio. Defaults to
            1.5.
        x_margin (float, optional): Margin on the X axis in ms. Defaults to
            280.
        for_gui (bool, optional): Indicates whether to plot is generated for
            a graphical user interface. If true, the figure will be closed
            before returning the object so a canvas will be needed to render it
            . Otherwise, the figure will be return immediately. Defaults to
            True.

    Returns:
        figure.Figure: Plot of the aECG waveforms and its annotations
    """
    if ecgl_plot_layout == ECG_plot_layout.STACKED:
        fig = plot_stdleads_stacked(rhythm_data=rhythm_data, anns_df=anns_df,
                                    fig=fig, dpi=dpi, textsize=textsize,
                                    ecg_linewidth=ecg_linewidth,
                                    plot_grid=plot_grid, grid_color=grid_color,
                                    v_offset=v_offset,
                                    xmin=xmin, xmax=xmax,
                                    ymin=ymin, ymax=ymax,
                                    x_margin=x_margin,
                                    for_gui=for_gui)
    elif ecgl_plot_layout == ECG_plot_layout.THREExFOURxRHYTHM:
        # Plot 3x4 always up to 10 s only
        xmax = xmin + 10000.0
        fig = plot_stdleads_matrix(rhythm_data=rhythm_data, anns_df=anns_df,
                                   fig=fig, dpi=dpi, textsize=textsize,
                                   ecg_linewidth=ecg_linewidth,
                                   plot_grid=plot_grid, grid_color=grid_color,
                                   v_offset=v_offset,
                                   xmin=xmin, xmax=xmax,
                                   ymin=ymin, ymax=ymax,
                                   x_margin=x_margin,
                                   for_gui=for_gui)
    elif ecgl_plot_layout == ECG_plot_layout.SUPERIMPOSED:
        fig = plot_stdleads_stacked(rhythm_data=rhythm_data, anns_df=anns_df,
                                    fig=fig, dpi=dpi, textsize=textsize,
                                    ecg_linewidth=ecg_linewidth,
                                    plot_grid=plot_grid, grid_color=grid_color,
                                    v_offset=0,
                                    xmin=xmin, xmax=xmax,
                                    ymin=ymin-1.5, ymax=ymax+1.5,
                                    x_margin=x_margin,
                                    for_gui=for_gui)
    return fig


def plot_stdleads_stacked(rhythm_data: pd.DataFrame,
                          anns_df: pd.DataFrame = None,
                          fig: figure.Figure = None,
                          dpi: int = 300,
                          textsize: int = 6,
                          ecg_linewidth: float = 0.3,
                          plot_grid: bool = True,
                          grid_color: str = "#a88332",
                          v_offset: float = 1.5,
                          xmin: float = 0.0, xmax: float = 10000.0,
                          ymin: float = -1.5, ymax: float = 1.5,
                          x_margin: float = 280,
                          for_gui: bool = True) -> figure.Figure:
    """Plots the waveform and annotations in a stacked or superimposed layout

    Args:
        rhythm_data (pd.DataFrame): aECG waveform as returned by
            :any:`Aecg.rhythm_as_df` or :any:`Aecg.derived_as_df`.
        anns_df (pd.DataFrame, optional): aECG annotations. For example,
            as returned by pd.DataFrame(the_aecg.DERIVEDANNS[0].anns) where
            the_aecg is an :any:`Aecg` object. Defaults to None.
        fig (figure.Figure, optional): Figure containing the plot. Defaults to
            None.
        dpi (int, optional): Plot resolution in dots per inch (dpi). Defaults
            to 300.
        textsize (int, optional): Default text fontsize. Defaults to 6.
        ecg_linewidth (float, optional): Line width for the ECG waveform.
            Defaults to 0.3.
        plot_grid (bool, optional): Indicates whether to plot the standard ECG
            grid. Defaults to True.
        grid_color (str, optional): Color of the ECG grid. Defaults to
            "#a88332".
        v_offset (float, optional): Vertical offset between leads in mV. Set to
            0 For a superimposed layout. Defaults to 1.5.
        xmin (float, optional): X axis minimum value in ms. Defaults to 0.0.
        xmax (float, optional): X axis maximum value in ms. This value may be
            adjusted automatically when maintaining aspect ratio. Defaults to
            10000.0.
        ymin (float, optional): Y axis minimum value in mV. Defaults to -1.5.
        ymax (float, optional): Y axis maximum value in mV. This value may be
            adjusted automatically when maintaining aspect ratio. Defaults to
            1.5.
        x_margin (float, optional): Margin on the X axis in ms. Defaults to
            280.
        for_gui (bool, optional): Indicates whether to plot is generated for
            a graphical user interface. If true, the figure will be closed
            before returning the object so a canvas will be needed to render it
            . Otherwise, the figure will be return immediately. Defaults to
            True.

    Returns:
        figure.Figure: Plot of the aECG waveforms and its annotations
    """
    # Compute maximum height range based on number of leads
    ecg_ymin = min(ymin, -min(12, (rhythm_data.shape[1]-1))*v_offset)
    ecg_ymax = max(v_offset, ymax)
    # Compute image size
    ecg_width = (xmax - xmin + x_margin)/40.0  # mm (25 mm/s -> 1 mm x 0.04s)
    ecg_height = (ecg_ymax - ecg_ymin)*10.0  # mm ( 10 mm/mV -> 1 mm x 0.1 mV)
    ecg_w_in = ecg_width/25.4  # inches
    ecg_h_in = ecg_height/25.4  # inches
    # Figure size
    if fig is None:
        fig = plt.figure()
    else:
        fig.clear()
    fig.set_size_inches(ecg_w_in, ecg_h_in)
    fig.set_dpi(dpi)
    fig.set_facecolor('w')
    fig.set_edgecolor('k')

    ax1 = fig.add_axes([0, 0, 1, 1], frameon=False)

    # ecg grid
    if plot_grid:
        grid_major_x = np.arange(xmin, xmax + x_margin, 200.0)
        grid_minor_x = np.arange(xmin, xmax + x_margin, 40.0)
        for xc in grid_major_x:
            ax1.axvline(x=xc, color=grid_color, linewidth=0.5)
        for xc in grid_minor_x:
            ax1.axvline(x=xc, color=grid_color, linewidth=0.2)
        numleads = min(12, len(rhythm_data.columns) - 1)
        grid_major_y = np.arange(min(ymin, -numleads * v_offset),
                                 max(v_offset, ymax), 0.5)
        grid_minor_y = np.arange(min(ymin, -numleads * v_offset),
                                 max(v_offset, ymax), 0.1)
        for yc in grid_major_y:
            ax1.axhline(y=yc, color=grid_color, linewidth=0.5)
        for yc in grid_minor_y:
            ax1.axhline(y=yc, color=grid_color, linewidth=0.1)

    # Plot leads stacked with lead I on top and V6 at the bottom
    idx = 0
    lead_zero = 0
    ecglibann_voffset = {"RPEAK": 1.0, "PON": 0.7,
                         "QON": 0.4, "QOFF": 0.7,
                         "TOFF": 0.4}
    for lead in ["I", "II", "III", "aVR", "aVL", "aVF",
                 "V1", "V2", "V3", "V4", "V5", "V6"]:
        if lead in rhythm_data.columns:
            lead_zero = - idx * v_offset
            # ecg calibration pulse
            ax1.plot([40, 80, 80, 280, 280, 320],
                     [lead_zero, lead_zero, lead_zero + 1,
                         lead_zero + 1, lead_zero, lead_zero],
                     color='black', linewidth=0.5)
            # lead name
            ax1.text(x_margin + 80, lead_zero + 0.55, lead, size=textsize)
            ax1.plot(rhythm_data.TIME[rhythm_data[lead].notna()] + x_margin,
                     rhythm_data[lead][rhythm_data[lead].notna()
                                       ].values + lead_zero,
                     color='black', linewidth=ecg_linewidth)
            lead_start_time = rhythm_data.TIME[
                rhythm_data[lead].notna()].values[0] + x_margin
            # Plot global annotations
            if anns_df is not None:
                if anns_df.shape[0] > 0:
                    ann_voffset = 1.0
                    for j, ann in anns_df[
                                    anns_df["LEADNAM"] == lead].iterrows():
                        # Annotation type
                        if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                            ann_voffset = ecglibann_voffset[
                                ann["ECGLIBANNTYPE"]]
                        else:
                            ann_voffset = ann_voffset - 0.3
                            if ann_voffset < 0.0:
                                ann_voffset = 1.0
                        ax1.text(ann["TIME"] + lead_start_time,
                                 lead_zero + ann_voffset, ann["ECGLIBANNTYPE"],
                                 size=textsize-1, color="blue")
                        # Annotation vertical line
                        ann_x = ann["TIME"] + lead_start_time,
                        ax1.plot([ann_x, ann_x],
                                 [lead_zero-1.0, lead_zero+1.0],
                                 color="blue", linewidth=0.5)
            idx = idx + 1
    # Plot global
    if anns_df is not None:
        if anns_df.shape[0] > 0:
            for idx, ann in anns_df[anns_df["LEADNAM"] == "GLOBAL"].iterrows():
                # Annotation type
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ax1.text(ann["TIME"] + xmin + x_margin,
                         lead_zero - ann_voffset, ann["ECGLIBANNTYPE"],
                         size=textsize-1, color="red")
                # Annotation vertical line
                ax1.axvline(x=ann["TIME"] + x_margin,
                            color="red", linewidth=0.5, linestyle=":")

    # Turn off tick labels
    ax1.set_xticks([])
    ax1.set_yticks([])
    # Set figure width and height
    ax1.set_xlim(xmin, xmax + x_margin)
    ax1.set_ylim(ecg_ymin, ecg_ymax)
    if for_gui:
        # Close plt
        plt.close()

    return fig


def plot_stdleads_matrix(rhythm_data: pd.DataFrame,
                         anns_df: pd.DataFrame = None,
                         fig: figure.Figure = None,
                         dpi: int = 300,
                         textsize: int = 6,
                         ecg_linewidth: float = 0.6,
                         plot_grid: bool = True,
                         grid_color: str = "#a88332",
                         v_offset: float = 1.5,
                         xmin: float = 0.0, xmax: float = 10000.0,
                         ymin: float = -1.5, ymax: float = 1.5,
                         x_margin: float = 280,
                         for_gui: bool = True) -> figure.Figure:
    """Plots the waveform and annotations in a 3x4 + lead II layout

    Args:
        rhythm_data (pd.DataFrame): aECG waveform as returned by
            :any:`Aecg.rhythm_as_df` or :any:`Aecg.derived_as_df`.
        anns_df (pd.DataFrame, optional): aECG annotations. For example,
            as returned by pd.DataFrame(the_aecg.DERIVEDANNS[0].anns) where
            the_aecg is an :any:`Aecg` object. Defaults to None.
        fig (figure.Figure, optional): Figure containing the plot. Defaults to
            None.
        dpi (int, optional): Plot resolution in dots per inch (dpi). Defaults
            to 300.
        textsize (int, optional): Default text fontsize. Defaults to 6.
        ecg_linewidth (float, optional): Line width for the ECG waveform.
            Defaults to 0.3.
        plot_grid (bool, optional): Indicates whether to plot the standard ECG
            grid. Defaults to True.
        grid_color (str, optional): Color of the ECG grid. Defaults to
            "#a88332".
        v_offset (float, optional): Vertical offset between leads in mV.
            Defaults to 1.5.
        xmin (float, optional): X axis minimum value in ms. Defaults to 0.0.
        xmax (float, optional): X axis maximum value in ms. This value may be
            adjusted automatically when maintaining aspect ratio. Defaults to
            10000.0.
        ymin (float, optional): Y axis minimum value in mV. Defaults to -1.5.
        ymax (float, optional): Y axis maximum value in mV. This value may be
            adjusted automatically when maintaining aspect ratio. Defaults to
            1.5.
        x_margin (float, optional): Margin on the X axis in ms. Defaults to
            280.
        for_gui (bool, optional): Indicates whether to plot is generated for
            a graphical user interface. If true, the figure will be closed
            before returning the object so a canvas will be needed to render it
            . Otherwise, the figure will be return immediately. Defaults to
            True

    Returns:
        figure.Figure: Plot of the aECG waveforms and its annotations
    """
    # Add offsets to the leads to match desired 3x4 layout
    h_offset = 2500
    column_padding = 50

    # Check if standard leads are present and, if not, populate with np.nan
    for lead in ["I", "II", "III", "aVR", "aVL", "aVF",
                 "V1", "V2", "V3", "V4", "V5", "V6"]:
        if lead not in rhythm_data.columns:
            rhythm_data[lead] = np.nan

    beat_plot_col1 = rhythm_data[rhythm_data.TIME < (
        h_offset - column_padding)][["TIME", "I", "II", "III"]].copy()

    beat_plot_col2 = rhythm_data[(rhythm_data.TIME >= h_offset) &
                                 (rhythm_data.TIME <
                                 (2 * h_offset - column_padding))][
                                     ["TIME", "aVR", "aVF", "aVL"]].copy()

    beat_plot_col3 = rhythm_data[(rhythm_data.TIME >= (2 * h_offset)) &
                                 (rhythm_data.TIME <
                                 (3 * h_offset - column_padding))][
                                     ["TIME", "V1", "V2", "V3"]].copy()

    beat_plot_col4 = rhythm_data[(rhythm_data.TIME >= (3 * h_offset)) &
                                 (rhythm_data.TIME <
                                 (4 * h_offset - column_padding))][
                                     ["TIME", "V4", "V5", "V6"]].copy()
    beat_plot = pd.concat(
        [beat_plot_col1, beat_plot_col2, beat_plot_col3, beat_plot_col4])

    anns_matrix = None
    anns_matrix_col1 = None
    anns_matrix_col2 = None
    anns_matrix_col3 = None
    anns_matrix_col4 = None
    if anns_df is not None:
        if anns_df.shape[0] > 0:
            anns_matrix_col1 = anns_df[anns_df.TIME < (
                h_offset - column_padding)].copy()

            anns_matrix_col2 = anns_df[(anns_df.TIME >= h_offset) &
                                       (anns_df.TIME <
                                       (2 * h_offset - column_padding))].copy()

            anns_matrix_col3 = anns_df[(anns_df.TIME >= (2 * h_offset)) &
                                       (anns_df.TIME <
                                       (3 * h_offset - column_padding))].copy()

            anns_matrix_col4 = anns_df[(anns_df.TIME >= (3 * h_offset)) &
                                       (anns_df.TIME <
                                       (4 * h_offset - column_padding))].copy()
            anns_matrix = pd.concat([anns_matrix_col1, anns_matrix_col2,
                                     anns_matrix_col3, anns_matrix_col4])

    # Compute maximum height range based on number of leads
    ecg_ymin = min(ymin, -4*v_offset)
    ecg_ymax = max(v_offset, ymax)
    # Compute image size
    ecg_width = (xmax - xmin + x_margin) / 40.0  # mm (25 mm/s -> 1 mm x 0.04s)
    # mm ( 10 mm/mV -> 1 mm x 0.1 mV)
    ecg_height = (ecg_ymax - ecg_ymin) * 10.0
    ecg_w_in = ecg_width / 25.4  # inches
    ecg_h_in = ecg_height / 25.4  # inches
    # Figure size
    if fig is None:
        fig = plt.figure(dpi=dpi)
    else:
        fig.clear()
    fig.set_size_inches(ecg_w_in, ecg_h_in)
    fig.set_dpi(dpi)
    fig.set_facecolor('w')
    fig.set_edgecolor('k')

    ax1 = fig.add_axes([0, 0, 1, 1], frameon=False)

    # ecg grid
    if plot_grid:
        grid_major_x = np.arange(0, xmax + x_margin, 200)
        grid_minor_x = np.arange(0, xmax + x_margin, 40)
        for xc in grid_major_x:
            ax1.axvline(x=xc, color=grid_color, linewidth=0.5)
        for xc in grid_minor_x:
            ax1.axvline(x=xc, color=grid_color, linewidth=0.2)
        grid_major_y = np.arange(-4 * v_offset, v_offset, 0.5)
        grid_minor_y = np.arange(-4 * v_offset, v_offset, 0.1)
        for yc in grid_major_y:
            ax1.axhline(y=yc, color=grid_color, linewidth=0.5)
        for yc in grid_minor_y:
            ax1.axhline(y=yc, color=grid_color, linewidth=0.2)

    ecglibann_voffset = {"RPEAK": 1.0, "PON": 0.7,
                         "QON": 0.4, "QOFF": 0.7,
                         "TOFF": 0.4}
    # First column
    # ecg calibration pulse
    lead_zero = 0.0
    ax1.plot([40, 80, 80, 280, 280, 320],
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead I
    tmp = plt.text(x_margin + 80, 0.55, 'I', size=textsize)
    if "I" in rhythm_data.columns:
        ax1.plot(beat_plot.TIME[beat_plot.I.notna()] + x_margin,
                 beat_plot.I[beat_plot.I.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.I.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.I.notna()].values[-1] + x_margin
        if anns_matrix_col1 is not None:
            for idx, ann in anns_matrix_col1[
                    anns_matrix_col1["LEADNAM"] == "I"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x <= col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")

    # ecg calibration pulse
    lead_zero = - v_offset
    ax1.plot([40, 80, 80, 280, 280, 320],
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead II
    ax1.text(x_margin + 80, 0.55 + lead_zero, 'II', size=textsize)
    if "II" in rhythm_data.columns:
        beat_plot.II = beat_plot.II + lead_zero
        ax1.plot(beat_plot.TIME[beat_plot.II.notna()] + x_margin,
                 beat_plot.II[beat_plot.II.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.II.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.II.notna()].values[-1] + x_margin
        if anns_matrix_col1 is not None:
            for idx, ann in anns_matrix_col1[
                    anns_matrix_col1["LEADNAM"] == "II"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x < col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")

    # ecg calibration pulse
    lead_zero = - 2 * v_offset
    ax1.plot([40, 80, 80, 280, 280, 320],
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead III
    ax1.text(x_margin + 80, 0.55 + lead_zero, 'III', size=textsize)
    if "III" in rhythm_data.columns:
        beat_plot.III = beat_plot.III + lead_zero
        ax1.plot(beat_plot.TIME[beat_plot.III.notna()] + x_margin,
                 beat_plot.III[beat_plot.III.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.III.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.III.notna()].values[-1] + x_margin
        if anns_matrix_col1 is not None:
            for idx, ann in anns_matrix_col1[
                    anns_matrix_col1["LEADNAM"] == "III"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x <= col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")

    # Second column
    # ecg calibration pulse
    lead_zero = 0
    ax1.plot(np.array([40, 80, 80, 280, 280, 320]) + h_offset,
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead aVR
    ax1.text(h_offset + x_margin + 80, 0.55, 'aVR', size=textsize)
    if "aVR" in rhythm_data.columns and\
            len(beat_plot.TIME[beat_plot.aVR.notna()]) > 0:
        ax1.plot(beat_plot.TIME[beat_plot.aVR.notna()] + x_margin,
                 beat_plot.aVR[beat_plot.aVR.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.aVR.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.aVR.notna()].values[-1] + x_margin
        if anns_matrix_col2 is not None:
            for idx, ann in anns_matrix_col2[
                    anns_matrix_col2["LEADNAM"] == "aVR"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x <= col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")

    # ecg calibration pulse
    lead_zero = - v_offset
    ax1.plot(np.array([40, 80, 80, 280, 280, 320]) + h_offset,
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead aVL
    ax1.text(h_offset + x_margin + 80, 0.55 + lead_zero, 'aVL', size=textsize)
    if "aVL" in rhythm_data.columns and\
            len(beat_plot.TIME[beat_plot.aVL.notna()]) > 0:
        beat_plot.aVL = beat_plot.aVL + lead_zero
        ax1.plot(beat_plot.TIME[beat_plot.aVL.notna()] + x_margin,
                 beat_plot.aVL[beat_plot.aVL.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.aVL.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.aVL.notna()].values[-1] + x_margin
        if anns_matrix_col2 is not None:
            for idx, ann in anns_matrix_col2[
                    anns_matrix_col2["LEADNAM"] == "aVL"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x <= col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")

    lead_zero = - 2 * v_offset
    ax1.plot(np.array([40, 80, 80, 280, 280, 320]) + h_offset,
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead aVF
    ax1.text(h_offset + x_margin + 80, 0.55 + lead_zero, 'aVF', size=textsize)
    if "aVF" in rhythm_data.columns and\
            len(beat_plot.TIME[beat_plot.aVF.notna()]) > 0:
        beat_plot.aVF = beat_plot.aVF + lead_zero
        ax1.plot(beat_plot.TIME[beat_plot.aVF.notna()] + x_margin,
                 beat_plot.aVF[beat_plot.aVF.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.aVF.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.aVF.notna()].values[-1] + x_margin
        if anns_matrix_col2 is not None:
            for idx, ann in anns_matrix_col2[
                    anns_matrix_col2["LEADNAM"] == "aVF"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x <= col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")

    # Third column
    # ecg calibration pulse
    lead_zero = 0
    ax1.plot(np.array([40, 80, 80, 280, 280, 320]) + 2*h_offset,
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead V1
    ax1.text(2 * h_offset + x_margin + 80, 0.55, 'V1', size=textsize)
    if "V1" in rhythm_data.columns and\
            len(beat_plot.TIME[beat_plot.V1.notna()]) > 0:
        ax1.plot(beat_plot.TIME[beat_plot.V1.notna()] + x_margin,
                 beat_plot.V1[beat_plot.V1.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.V1.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.V1.notna()].values[-1] + x_margin
        if anns_matrix_col3 is not None:
            for idx, ann in anns_matrix_col3[
                    anns_matrix_col3["LEADNAM"] == "V1"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x <= col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")

    # ecg calibration pulse
    lead_zero = - v_offset
    ax1.plot(np.array([40, 80, 80, 280, 280, 320]) + 2*h_offset,
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead V2
    ax1.text(2 * h_offset + x_margin + 80, 0.55 +
             lead_zero, 'V2', size=textsize)
    if "V2" in rhythm_data.columns and\
            len(beat_plot.TIME[beat_plot.V2.notna()]) > 0:
        beat_plot.V2 = beat_plot.V2 + lead_zero
        ax1.plot(beat_plot.TIME[beat_plot.V2.notna()] + x_margin,
                 beat_plot.V2[beat_plot.V2.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.V2.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.V2.notna()].values[-1] + x_margin
        if anns_matrix_col3 is not None:
            for idx, ann in anns_matrix_col3[
                    anns_matrix_col3["LEADNAM"] == "V2"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x <= col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")

    # ecg calibration pulse
    lead_zero = - 2 * v_offset
    ax1.plot(np.array([40, 80, 80, 280, 280, 320]) + 2*h_offset,
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead V3
    ax1.text(2 * h_offset + x_margin + 80, 0.55 +
             lead_zero, 'V3', size=textsize)
    if "V3" in rhythm_data.columns and\
            len(beat_plot.TIME[beat_plot.V3.notna()]) > 0:
        beat_plot.V3 = beat_plot.V3 + lead_zero
        ax1.plot(beat_plot.TIME[beat_plot.V3.notna()] + x_margin,
                 beat_plot.V3[beat_plot.V3.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.V3.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.V3.notna()].values[-1] + x_margin
        if anns_matrix_col3 is not None:
            for idx, ann in anns_matrix_col3[
                    anns_matrix_col3["LEADNAM"] == "V3"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x <= col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")

    # Fourth column
    # ecg calibration pulse
    lead_zero = 0
    ax1.plot(np.array([40, 80, 80, 280, 280, 320]) + 3*h_offset,
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead V4
    ax1.text(3 * h_offset + x_margin + 80, 0.55, 'V4', size=textsize)
    if "V4" in rhythm_data.columns and\
            len(beat_plot.TIME[beat_plot.V4.notna()]) > 0:
        ax1.plot(beat_plot.TIME[beat_plot.V4.notna()] + x_margin,
                 beat_plot.V4[beat_plot.V4.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.V4.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.V4.notna()].values[-1] + x_margin
        if anns_matrix_col4 is not None:
            for idx, ann in anns_matrix_col4[
                    anns_matrix_col4["LEADNAM"] == "V4"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x <= col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")

    # ecg calibration pulse
    lead_zero = - v_offset
    ax1.plot(np.array([40, 80, 80, 280, 280, 320]) + 3*h_offset,
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead V5
    ax1.text(3 * h_offset + x_margin + 80, 0.55 +
             lead_zero, 'V5', size=textsize)
    if "V5" in rhythm_data.columns and\
            len(beat_plot.TIME[beat_plot.V5.notna()]) > 0:
        beat_plot.V5 = beat_plot.V5 + lead_zero
        ax1.plot(beat_plot.TIME[beat_plot.V5.notna()] + x_margin,
                 beat_plot.V5[beat_plot.V5.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.V5.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.V5.notna()].values[-1] + x_margin
        if anns_matrix_col4 is not None:
            for idx, ann in anns_matrix_col4[
                    anns_matrix_col4["LEADNAM"] == "V5"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x <= col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")

    # ecg calibration pulse
    lead_zero = - 2 * v_offset
    ax1.plot(np.array([40, 80, 80, 280, 280, 320]) + 3*h_offset,
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    # Lead V6
    ax1.text(3 * h_offset + x_margin + 80, 0.55 +
             lead_zero, 'V6', size=textsize)
    if "V6" in rhythm_data.columns and\
            len(beat_plot.TIME[beat_plot.V6.notna()]) > 0:
        beat_plot.V6 = beat_plot.V6 + lead_zero
        ax1.plot(beat_plot.TIME[beat_plot.V6.notna()] + x_margin,
                 beat_plot.V6[beat_plot.V6.notna()], color='black',
                 linewidth=ecg_linewidth)
        lead_start_time = beat_plot.TIME[
            beat_plot.V6.notna()].values[0] + x_margin
        col_end = beat_plot.TIME[
            beat_plot.V6.notna()].values[-1] + x_margin
        if anns_matrix_col4 is not None:
            for idx, ann in anns_matrix_col4[
                    anns_matrix_col4["LEADNAM"] == "V6"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                ann_x = ann["TIME"] + lead_start_time
                if ann_x <= col_end:
                    ax1.plot([ann_x, ann_x], [lead_zero-1.0, lead_zero+1.0],
                             color="blue", linewidth=0.5)
                    ax1.text(ann_x,
                             lead_zero + ann_voffset,
                             ann["ECGLIBANNTYPE"],
                             size=textsize-1, color="blue")
    # Rhythm strip
    # ecg calibration pulse
    lead_zero = - 0.5 - 3 * v_offset
    ax1.plot(np.array([40, 80, 80, 280, 280, 320]),
             [lead_zero, lead_zero, lead_zero + 1,
                 lead_zero + 1, lead_zero, lead_zero],
             color='black', linewidth=0.5)
    ax1.text(x_margin + 80, lead_zero + 0.55, 'II', size=textsize)
    if "II" in rhythm_data.columns:
        ax1.plot(rhythm_data.TIME + x_margin, rhythm_data.II + lead_zero,
                 color='black', linewidth=ecg_linewidth)
        lead_start_time = rhythm_data.TIME[
            rhythm_data.II.notna()].values[0] + x_margin
        col_end = rhythm_data.TIME[
            rhythm_data.II.notna()].values[-1] + x_margin
        if anns_df is not None:
            if anns_df.shape[0] > 0:
                for idx, ann in anns_df[anns_df["LEADNAM"] == "II"].iterrows():
                    ann_voffset = 1.0
                    if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                        ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                    ann_x = ann["TIME"] + lead_start_time
                    if ann_x <= col_end:
                        ax1.plot([ann_x, ann_x],
                                 [lead_zero-1.0, lead_zero+1.0],
                                 color="blue", linewidth=0.5)
                        ax1.text(ann_x,
                                 lead_zero + ann_voffset,
                                 ann["ECGLIBANNTYPE"],
                                 size=textsize-1, color="blue")
    # Plot global annotations
    if anns_matrix is not None:
        if anns_matrix.shape[0] > 0:
            for idx, ann in anns_matrix[
                    anns_matrix["LEADNAM"] == "GLOBAL"].iterrows():
                ann_voffset = 1.0
                if ann["ECGLIBANNTYPE"] in ecglibann_voffset.keys():
                    ann_voffset = ecglibann_voffset[ann["ECGLIBANNTYPE"]]
                # Columns
                ann_x = ann["TIME"] + xmin + x_margin
                ax1.plot([ann_x, ann_x], [-0.5 - 2 * v_offset, ymax-0.5],
                         color="red", linewidth=0.5, linestyle=":")
                # Lead II strip at the bottom
                ax1.plot([ann_x, ann_x], [-1.0 - 3 * v_offset, 1.0 - 0.5 -
                                          3 * v_offset], color="red",
                         linewidth=0.5, linestyle=":")
                ax1.text(ann_x,
                         - 3 * v_offset - ann_voffset,
                         ann["ECGLIBANNTYPE"],
                         size=textsize-1, color="red")

    # Turn off tick labels
    ax1.set_xticks([])
    ax1.set_yticks([])
    # Set figure width and height
    ax1.set_xlim(xmin, xmax + x_margin)
    ax1.set_ylim(ecg_ymin, ecg_ymax)
    if for_gui:
        # Close plt
        tmp = plt.close()

    return fig


def ratio_of_missing_samples(waveform_data: pd.DataFrame) -> float:
    """Returns the ration of missing samples in a waveform

    Calculates the total number of samples as well as the number of samples
    reported as np.nan values (i.e., missing) and returns the ration of missing
    over the total number of samples.

    Args:
        waveform_data (pd.DataFrame): Waveform data like the one returned by
            :any:`Aecg.rhythm_as_df`

    Returns:
        float: ration of number of missing over the total number of samples
    """
    total_samples = (waveform_data.shape[1] - 1) * waveform_data.shape[0]
    not_nans = waveform_data.drop(columns=["TIME"]).count().sum()
    num_nans = total_samples - not_nans
    missing_ratio = num_nans / total_samples

    return missing_ratio

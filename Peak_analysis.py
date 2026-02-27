
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 30 20:02:19 2024

@author: Barrett
"""
#import all libraries
import matplotlib
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog, messagebox
import pyabf
import numpy as np
from draggable_line import DraggableLine
import matplotlib.pyplot as plt
from matplotlib.widgets import *
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
import pandas as pd
import os
import sys


def select_and_check_abf_file():
    # Creates a windows directory box asking the user to select a file, only accepts ABF file types
    file_path = filedialog.askopenfilename(title='Select ABF File', filetypes=[("ABF files", "*.abf")])
    
    # Error handling when selecting files
    if not file_path:  # Check if no file was selected
        print("No file selected.")  # Inform the user that no file was selected
        return None  # Exit the function and return None since no file was selected
    
    if not file_path.endswith('.abf'):  # Check if the selected file does not end with '.abf'
        print("Invalid file type. Please select an ABF file.")  # Inform the user that the selected file is not an ABF file
        return None  # Exit the function and return None since the file type is incorrect
    
    else:  # If a file was selected and it is an ABF file
        print("ABF file selected:", file_path)  # Inform the user of the selected file's path
        # Returns the file selected and saves it to path
        return file_path  # Return the path of the selected ABF file

def load_abf_file(file_path):
    try:
        # Attempt to load the ABF file using the pyABF library
        abf = pyabf.ABF(file_path)
        # If successful, print a confirmation message including the number of sweeps in the file
        print(f"File loaded successfully with pyABF. Number of sweeps: {abf.sweepCount}")
        # Return the loaded ABF object
        return abf
    except OSError as e:  # Handle the case where the file is not found
        print(f"File not found: {e}")  # Print an error message with details
    except pyabf.ABFError as e:  # Handle specific errors related to the pyABF library
        print(f"Error loading ABF file with pyabf: {e}")  # Print an error message with details
    except Exception as e:  # Handle any other exceptions that may occur
        print(f"Failed to load the file with pyABF: {e}")  # Print a general error message with details
        return None  # Return None to indicate that loading the file failed


# Function to normalise force data by slice dimensions
def get_slice_width():
    # Creates interactive dialog box with error handling for incorrect formatting
    while True:
        width = simpledialog.askstring("Enter Width", "Enter the slice width (in millimeters):")
        # If user presses cancel or entered an empty string, a box is created, asking for confirmation
        if width is None or not width.strip():  # Check if the input is empty or None
            if messagebox.askyesno("Cancel Operation", "No width entered. Do you want to cancel the operation?"):
                # Exits the function with None to signify cancellation
                return None  
            else:
                # If the user decides not to cancel, it prompts again
                continue  

        try:
            # Checks if input is in a simple decimal or integer format
            if '.' in width:  # Checks to see if there's a decimal point in the input
                # This allows decimal numbers but not others e.g.scientific notation to be processed
                float_parts = width.split('.')  # Split the input into parts
                if len(float_parts) == 2 and float_parts[0].isdigit() and float_parts[1].isdigit():
                    width = float(width)  # Convert to float if both parts are digits
                else:
                    raise ValueError("Invalid decimal format.")  # Raise an error for invalid format
            else:
                # Checks that it is in an integer format
                if width.isdigit():  # If statemet to see if the input is all digits
                    width = float(width)  # Converts to the value to float
                else:
                    raise ValueError("Invalid integer format.")  # Raise an error for invalid format

            # Checks if the entered value is positive
            if width > 0:
                # Confirmation statement of the entered width
                print(f"Width entered: {width} mm")
                return width  # Return the valid width value
            # If the number is not positive stops processing and provides an error message
            else:  
                messagebox.showerror("Invalid Input", "Please enter a positive number for the slice width.")
        # If a conversion to float fails (meaning it's not a valid float), another error message
        except ValueError:  
            messagebox.showerror("Invalid Input", "Invalid input. Please enter a valid positive number for the slice width.")

class PlotDataWithTag:
    def __init__(self, abf, tag_correction_factor = 2.0, sweep=0, channel=0, file_name="", specific_time=None, updated_tags=list()):
        self.abf = abf
        self.slice_width = 3.33333333333333
        self.cross_sectional_area = self.slice_width * 0.3
        self.tag_correction_factor = tag_correction_factor
        self.sweep = sweep
        self.channel = channel
        self.file_name = file_name
        self.specific_time = specific_time
        self.x_sensitivity = 0.0008
        self.y_sensitivity = self.x_sensitivity * 3
        self.updated_tags = updated_tags

        plt.close('all')  # Close all existing plots to start fresh
        self.fig, self.ax = plt.subplots(figsize=(15, 5))  # Create a new figure and axes with a specific size
        self.set_slice_ax = plt.axes([0.85, 0.19, 0.1, 0.05])  # Define button position
        self.set_slice_button = Button(self.set_slice_ax, 'Set Slice Width')  # Create button
        self.set_slice_button.on_clicked(self.set_slice_width)

        self.reset_tags_ax = plt.axes([0.85, 0.13, 0.14, 0.05])  # Define button position
        self.reset_tags_button = Button(self.reset_tags_ax, 'Reset Tags to Original Position')  # Create button
        self.reset_tags_button.on_clicked(self.reset_tags)

        self.tag_calibration_ax = plt.axes([0.85, 0.07, 0.14, 0.05])  # Define button position
        self.tag_calibration_button = Button(self.tag_calibration_ax, 'Calibrate Tag Timepoints')  # Create button
        self.tag_calibration_button.on_clicked(self.tag_calibration)

        self.confirm_timepoint_ax = plt.axes([0.85, 0.01, 0.14, 0.05])  # Define button position
        self.confirm_timepoint_button = Button(self.confirm_timepoint_ax, 'Confirm Analysis Timepoints')  # Create button
        self.confirm_timepoint_button.on_clicked(self.confirm_timepoints)

        # Connect the scroll and mouse drag events
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.fig.canvas.mpl_connect('button_press_event', self.on_button_press)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)

        self.update_plot()
        plt.show()

    def on_button_press(self, event):
        if event.button == 2:  # Scroll button pressed
            self.prev_x = event.x
            self.prev_y = event.y

    def on_motion(self, event):
        if event.button == 2 and self.prev_x is not None and self.prev_y is not None:
            dx = event.x - self.prev_x
            dy = event.y - self.prev_y
            self.prev_x = event.x
            self.prev_y = event.y

            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]
            xlim_new = (xlim[0] - dx * x_range * self.x_sensitivity, xlim[1] - dx * x_range * self.x_sensitivity)
            ylim_new = (ylim[0] - dy * y_range * self.y_sensitivity, ylim[1] - dy * y_range * self.y_sensitivity)

            self.ax.set_xlim(xlim_new)
            self.ax.set_ylim(ylim_new)
            self.fig.canvas.draw()

    def on_scroll(self, event):
        # Zoom in or out based on scroll direction
        if event.button == 'up':
            scale_factor = 1.1  # Zoom in factor
        elif event.button == 'down':
            scale_factor = 0.9  # Zoom out factor
        else:
            return

        # Get current limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()

        # Calculate new limits
        x_center = event.xdata
        y_center = event.ydata

        if x_center is None or y_center is None:
            # If the mouse is outside the axes, ignore the event
            return

        if event.key == 'control':
            new_ylim = [(y - y_center) * scale_factor + y_center for y in ylim]
            self.ax.set_ylim(new_ylim)
            
        else:
            new_xlim = [(x - x_center) * scale_factor + x_center for x in xlim]
            self.ax.set_xlim(new_xlim)

        # Redraw the plot
        self.fig.canvas.draw()

    def reset_tags(self, event):
        self.updated_tags = list()
        self.update_plot()

    def update_plot(self):
        self.ax.clear()
        self.abf.setSweep(sweepNumber=self.sweep, channel=self.channel)  # Set the sweep and channel for the ABF file

        if self.channel == 0:
            data = self.abf.sweepY / self.cross_sectional_area  # Normalize force data by cross-sectional area
            ylabel = 'Normalized Force (mN/mm²)'  # Set the y-axis label for force data
        else:
            data = self.abf.sweepY  # Use voltage data directly
            ylabel = 'Voltage (V)'  # Set the y-axis label for voltage data

        self.ax.plot(self.abf.sweepX, data, label=ylabel)  # Plot the data with the appropriate label
        self.ax.autoscale(enable=True, axis='x', tight=True)  # Enable autoscaling for the x-axis
        self.ax.set_ylim([data.min() - 1 if data.min() != data.max() else 0, data.max() + 1])  # Set y-axis limits

        if len(self.updated_tags) == 0:
            try:
                original_tags = [t * self.tag_correction_factor for t in self.abf.tagTimesSec]  # Apply the correction factor to tag times
                self.updated_tags = list(original_tags)  # Create a list to store updated tag positions

                print(f"Original tag positions: {original_tags}")  # Print the original tag positions for reference
            except TypeError as e:
                print(f"TypeError in tag correction: {e}")  # Handle TypeError if the correction fails
                return


        tag_lines = []  # List to store draggable line objects

        for tagIndex, corrected_tag_time in enumerate(self.updated_tags):
            """
            Create draggable lines and associated text labels for each tag.

            Parameters:
            tagIndex (int): The index of the tag.
            corrected_tag_time (float): The corrected time position for the tag.
            """
            if corrected_tag_time > self.abf.sweepX[-1]:
                corrected_tag_time = self.abf.sweepX[-1]
            elif corrected_tag_time < self.abf.sweepX[0]:
                corrected_tag_time = self.abf.sweepX[0]
            line = self.ax.axvline(x=corrected_tag_time, color='red', linestyle='-', label=f'Tag {tagIndex + 1} at {corrected_tag_time:.3f}s: {self.abf.tagComments[tagIndex]}')
            # Create a vertical line at the corrected tag time

            text = self.ax.text(corrected_tag_time, (data.min() + data.max()) / 2, f'{tagIndex + 1}', 
                            horizontalalignment='center', verticalalignment='center', color='black', fontsize=10, rotation=0)
            # Create a text label at the tag position

            draggable_line = DraggableLine(line, text, self.update_tag_position, tagIndex, self.abf.tagComments, [self.abf.sweepX[0], self.abf.sweepX[-1]])  # Initialize a draggable line object
            tag_lines.append(draggable_line)  # Add the draggable line to the list

        # Add titles, labels, legend, and grid to the plot
        self.ax.set_xlabel("Time (seconds)")  # Set the x-axis label
        self.ax.set_ylabel(ylabel)  # Set the y-axis label
        self.ax.set_title(self.file_name)  # Set the title of the plot
        self.ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=8.5)  # Add a legend
        self.ax.grid(True)  # Enable the grid
        
        plt.tight_layout()  # Adjust layout to fit elements within the figure area
        self.fig.canvas.draw() 

    def set_slice_width(self, event):
        """
        Set the slice width interactively.
        """
        slice_width_temp = get_slice_width()  # Call the function to get slice width interactively
        if slice_width_temp is None:
            return
        self.slice_width = slice_width_temp
        self.cross_sectional_area = slice_width_temp * 0.3
        self.update_plot() 

    def tag_calibration(self, event):
        tag_correction_factor = get_tag_correction_factor()
        if tag_correction_factor:
            self.tag_correction_factor = tag_correction_factor
            self.updated_tags = list()
            self.update_plot()

    def update_tag_position(self, new_position, index):
        """
        Update the position of a tag.

        Parameters:
        new_position (float): The new x-position of the tag.
        index (int): The index of the tag to update.
        """
        self.updated_tags[index] = new_position  # Update the position in the list

    def confirm_timepoints(self, event):
        confirm_result = confirm_tag_positions()
        if confirm_result:
            print("Tag Positions are correct!")
            timepoints = get_timepoints(self.abf, self.tag_correction_factor, self.updated_tags)
            if not timepoints:
                messagebox.showinfo("Information", "No timepoints provided.")
            else:
                data_arrays = process_abf_data(self.abf, timepoints, self.cross_sectional_area)
                
                if data_arrays:
                    csv_file = 'peak_statistics.csv'
                    with open(csv_file, 'w', newline='') as file:
                        writer = pd.DataFrame(columns=['Timepoint', 'Time to Peak', 'Time to 50% Decay', 'Time to 90% Decay', 'Tau', 'Active Force', 'Passive Force', 'Amplitude'])
                        writer.to_csv(file, index=False)
                    for i, dataset in enumerate(data_arrays):
                        print(f"Processing dataset {i+1}")
                        initialized_data = initialize_dataset()
                        initialized_data.update(dataset)
                        necessary_keys = ['force_peaks', 'voltage_peaks', 'passive_force', 'amplitude', 'peak_times', 'time_to_50_decay', 'time_to_90_decay', 'tau']
                        for key in necessary_keys:
                            if key not in initialized_data:
                                initialized_data[key] = [] if isinstance(initialized_data[key], list) else None
                        time = initialized_data['time']
                        force = initialized_data['force']
                        voltage = initialized_data['voltage']
                        data_rate = self.abf.dataRate
                        while True:
                            initialized_data['force_peaks'] = interactive_peak_detection(time, force, 'Detected Force Peaks')
                            initialized_data['voltage_peaks'] = interactive_peak_detection(time, voltage, 'Detected Voltage Peaks', is_voltage=True)
                            initialized_data['passive_force'] = calculating_passive_force(force, initialized_data['voltage_peaks'])
                            initialized_data['amplitude'] = calculating_amplitude(force, initialized_data['force_peaks'], initialized_data['passive_force'])
                            initialized_data['peak_times'] = calculating_time_to_peak(time, initialized_data['voltage_peaks'], initialized_data['force_peaks'])
                            initialized_data['time_to_50_decay'], initialized_data['time_to_90_decay'] = calculating_decay(time, force, initialized_data['force_peaks'], initialized_data['passive_force'])
                            initialized_data['tau'] = calculating_tau(time, force, initialized_data['force_peaks'], initialized_data['passive_force'], initialized_data['voltage_peaks'], data_rate)
                            fig = plot_data_with_annotations(initialized_data, decay_func, data_rate)
                            if confirm_plot():
                                if fig:
                                    plt.close(fig)
                                break
                        export_peak_statistics(initialized_data, f"Timepoint {i + 1}", csv_file)
                    summary_csv = 'summary_statistics.csv'
                    generate_summary_statistics(csv_file, summary_csv)
            

# Function for confirming tag positions
def confirm_tag_positions():
    # Create the root window for the tkinter application
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    # Display a message box asking the user to confirm the tag positions
    result = messagebox.askyesno("Confirm Tag Positions", "Are the tag positions correct?")
    
    # Destroy the root window to close the tkinter application
    root.destroy()
    
    # Return the result of the message box (True if 'Yes' is selected, False if 'No' is selected)
    return result

# Function for getting the tag correction factor from the user
def get_tag_correction_factor():
    while True:
        # Create the root window for the tkinter application
        root = tk.Tk()
        root.withdraw()  # Hide the root window

        # Display a dialog to ask the user for the tag correction factor
        correction_factor = simpledialog.askfloat(
            "Tag Correction Factor", 
            "Enter the tag correction factor:", 
            initialvalue=2.0,  # Provide an initial value of 2.0
            parent=root
        )
        
        # Destroy the root window to close the tkinter application
        root.destroy()

        # Check if the entered correction factor is valid (not None and positive)
        if correction_factor is not None and correction_factor > 0:
            return correction_factor  # Return the valid correction factor
        elif correction_factor is None: 
            return False
        else:
            # Show an error message if the input is invalid
            messagebox.showerror("Invalid Input", "Please enter a valid positive number for the tag correction factor.")


# Functions for determining the timepoints to use for later analysis

def get_timepoints(abf, tag_correction_factor=2.0, updated_tags = list()):
    plt.close()
    dialog = tk.Toplevel()
    dialog.title("Confirm Analysis Timepoints")
    dialog.configure(background='white')
    dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent the dialog from being closed
    style = ttk.Style()
    style.configure('TLabel', background='white', foreground='black', font=('Arial', 10))
    style.configure('TEntry', foreground='black', font=('Arial', 10))
    style.configure('TButton', background='lightblue', foreground='black', font=('Arial', 10))
    
    # Define the headers for the dialog table
    labels = ["Tag Number", "Tag Comment", "Tag Timepoint (s)", "Start of Analysis (s)", "Duration of Analysis (s)"]
    for i, label in enumerate(labels):
        ttk.Label(dialog, text=label).grid(row=0, column=i)

    entries = []
    for i, tag_time in enumerate(abf.tagTimesSec):
        corrected_tag_time = tag_time * tag_correction_factor
        row = i + 1
        # var_start = tk.StringVar(value=f"{corrected_tag_time:.3f}")
        var_start = tk.StringVar(value=f"{updated_tags[i]:.3f}")
        var_duration = tk.StringVar(value="7.0")
        entry = {'start': var_start, 'duration': var_duration}
        entries.append(entry)
        ttk.Label(dialog, text=str(i + 1)).grid(row=row, column=0)
        ttk.Label(dialog, text=abf.tagComments[i]).grid(row=row, column=1)
        # ttk.Label(dialog, text=f"{corrected_tag_time:.3f} s").grid(row=row, column=2)
        ttk.Label(dialog, text=f"{updated_tags[i]:.3f} s").grid(row=row, column=2)
        ttk.Entry(dialog, textvariable=var_start).grid(row=row, column=3)
        ttk.Entry(dialog, textvariable=var_duration).grid(row=row, column=4)

    result = None

    def on_submit():
        nonlocal result
        result = []
        overlaps = False
        for entry in entries:
            start = float(entry['start'].get())
            duration = float(entry['duration'].get())
            if start and duration and duration > 0:
                result.append((start, duration))
        print("Number of timepoints imported for Data Processing:", len(result))  # Debug: Print number of timepoints

        # Check for overlaps
        for i in range(len(result) - 1):
            start1, duration1 = result[i]
            start2, duration2 = result[i + 1]
            end1 = start1 + duration1
            if end1 > start2:
                overlaps = True
                print(f"Overlap detected between tag {i + 1} and tag {i + 2}")  # Debug: Print overlap details

        if overlaps:
            if not messagebox.askyesno("Overlap Warning", "There are overlaps between some timepoints. Do you want to proceed?"):
                result = None
                print("User chose to readjust tags due to overlaps.")  # Debug: User opted to readjust tags
                return

        plt.close('all')
        dialog.destroy()

    def on_cancel():
        print("Operation Cancelled by User")  # Debug: Print cancellation message
        dialog.withdraw()
        PlotDataWithTag(abf, tag_correction_factor, updated_tags=updated_tags)
        # sys.exit(0)

    def on_reset():
        # Reset tags to original positions
        for i, tag_time in enumerate(abf.tagTimesSec):
            # corrected_tag_time = tag_time * tag_correction_factor
            corrected_tag_time = updated_tags[i]
            entries[i]['start'].set(f"{corrected_tag_time:.3f}")
        print("Tags reset to original positions.")  # Debug: Print reset confirmation

    ttk.Button(dialog, text="Submit", command=on_submit).grid(row=len(abf.tagTimesSec) + 1, column=3)
    ttk.Button(dialog, text="Cancel", command=on_cancel).grid(row=len(abf.tagTimesSec) + 1, column=4)
    ttk.Button(dialog, text="Reset Tags", command=on_reset).grid(row=len(abf.tagTimesSec) + 1, column=5)
    dialog.wait_window()
    return result


# Function for processing the data within the file at the timepoints that have been created
def process_abf_data(abf, timepoints, cross_sectional_area):
    # Perform a single sweep count validity check at the beginning
    if abf.sweepCount <= 0:
        print(f"Invalid sweep count: {abf.sweepCount}. Using sweep 0.")
        sweep = 0  # Default to sweep 0 if the sweep count is invalid
    else:
        sweep = 0  # Default to the first sweep (sweep 0)

    all_data = []  # List to hold processed data

    for start_time, duration in timepoints:  # Iterate through each timepoint
        start_point = int(start_time * abf.dataRate)  # Calculate start index in samples
        end_point = int((start_time + duration) * abf.dataRate)  # Calculate end index in samples

        # Ensure the indices are within the valid range
        if start_point < 0 or end_point > len(abf.sweepY):
            print(f"Invalid time range: {start_time} to {start_time + duration}")
            continue  # Skip to the next timepoint if the range is invalid

        # Create a time array for the duration of the analysis
        time_array = np.linspace(start_time, start_time + duration, num=end_point - start_point)
        force_data = []  # Initialize an empty list for force data
        voltage_data = []  # Initialize an empty list for voltage data

        for channel in range(abf.channelCount):  # Iterate through each channel
            abf.setSweep(sweepNumber=sweep, channel=channel)  # Set the sweep number and channel
            data_segment = abf.sweepY[start_point:end_point]  # Extract the data segment for the current time range

            if channel == 0:  # For channel 0 (force data)
                force_data = data_segment / cross_sectional_area  # Normalize force data by cross-sectional area
            elif channel == 1:  # For channel 1 (voltage data)
                voltage_data = data_segment  # Use raw voltage data

        # Append the processed data to all_data list
        all_data.append({
            'time': time_array,  # Array of time values for the current analysis window
            'force': force_data,  # Array of normalized force values corresponding to the time array
            'voltage': voltage_data,  # Array of voltage values corresponding to the time array
            'start_time': start_time,  # Start time of the current analysis window
            'end_time': start_time + duration  # End time of the current analysis window
        })

    # Validate that all data arrays have the same length
    valid_data = []  # List to hold only valid datasets
    for data in all_data:
        if len(data['time']) == len(data['force']) == len(data['voltage']):
            valid_data.append(data)  # Add to valid_data if all arrays are of the same length
        else:
            print("Data alignment issue detected. Skipping dataset.")
            print(f"Time length: {len(data['time'])}, Force length: {len(data['force'])}, Voltage length: {len(data['voltage'])}")

    # Print the start and end times of all valid datasets
    for data in valid_data:
        print(f"Start: {data['start_time']}, End: {data['end_time']}")
    print("Number of Timepoints successfully processed:", len(valid_data))

    return valid_data  # Return only the valid datasets




# Function for creating an interactive dialog box that determines force peaks
def peak_parameters_dialog(y_min, y_max, initial_height, initial_distance, initial_prominence):
    root = tk.Tk()  # Create the root window for the tkinter application
    # Hide the main window
    root.withdraw()  # Hide the root window

    # Prompt the user to enter the minimum height of peaks with an initial value
    height = simpledialog.askfloat(
        "Height", 
        "Enter minimum height of peaks:", 
        initialvalue=initial_height, 
        parent=root
    )
    
    # Prompt the user to enter the minimum distance between peaks with an initial value
    distance = simpledialog.askinteger(
        "Distance", 
        "Enter minimum number of samples between peaks:", 
        initialvalue=initial_distance, 
        parent=root
    )
    
    # Prompt the user to enter the minimum prominence of peaks with an initial value
    prominence = simpledialog.askfloat(
        "Prominence", 
        "Enter minimum vertical distance to its neighboring samples:", 
        initialvalue=initial_prominence, 
        parent=root
    )
    
    root.destroy()  # Destroy the root window to close the tkinter application
    
    # Return the entered values
    return height, distance, prominence


# Interactive confirmation message box to proceed or not with the force and voltage peaks
def confirm_peaks_dialog(time, peaks, is_voltage):
    # Determine the data type based on the is_voltage flag
    data_type = "voltage" if is_voltage else "force"
    
    # Create a confirmation message with the data type
    message = f"Confirm that the detected {data_type} peaks are correct."
    
    # Display a message box asking the user to confirm the detected peaks
    return messagebox.askyesno("Confirm Peaks", message)


# Dynamic box that determines the peak detection using the range of the graph limits 
def interactive_peak_detection(time, data, title, is_voltage=False):
    y_min, y_max = min(data), max(data)  # Calculate the minimum and maximum values of the data
    # Height parameter set to 75% of the y-axis limit
    height = 0.75 * y_max
    # Distance set to 500ms between peaks
    distance = 500
    # Sets prominence value by subtracting y lower limit from upper, and divides by half
    prominence = (y_max - y_min) / 2

    # While loop to allow the user to reset parameters of peak detection and reloads graph and peak detection function
    while True:
        peaks, _ = find_peaks(data, height=height, distance=distance, prominence=prominence)  # Detect peaks in the data
        plot_data_with_peaks(time, data, peaks, title, is_voltage)  # Plot the data with detected peaks

        if confirm_peaks_dialog(time, peaks, is_voltage):  # Ask the user to confirm the detected peaks
            # Close the plot after confirmation
            plt.close('all')
            return peaks  # Return the confirmed peaks
        else:
            # Prompt the user to adjust peak detection parameters if not confirmed
            height, distance, prominence = peak_parameters_dialog(y_min, y_max, height, distance, prominence)


# Function for plotting peaks for both force and voltage
def plot_data_with_peaks(time, data, peaks, title, is_voltage):
    plt.figure()  # Create a new figure
    color = 'g' if is_voltage else 'b'  # Set the color based on whether the data is voltage or force
    ylabel = 'Voltage (V)' if is_voltage else 'Normalized Force (mN/mm²)'  # Set the y-axis label based on the data type

    plt.plot(time, data, color+'-', label=ylabel)  # Plot the data with time on the x-axis and data on the y-axis
    if len(peaks) > 0:  # Check if there are any detected peaks
        plt.plot(time[peaks], data[peaks], 'rx', label='Peaks')  # Plot the detected peaks as red 'x' markers

    plt.xlabel('Time (s)')  # Set the x-axis label
    plt.ylabel(ylabel)  # Set the y-axis label
    # Adjust the title to include the specific time range of the current data
    plt.title(f"{title} from {time[0]} to {time[-1]} seconds")
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1))  # Place the legend outside the plot area
    plt.tight_layout()  # Adjust the layout to fit all elements
    plt.show()  # Display the plot


#########################All calculation functions for determining peak behaviour##########################################
# Function that determines the tau /decay 
def decay_func(t, a, tau, c):
    # Calculate the exponential decay function
    # t: time variable
    # a: initial amplitude
    # tau: time constant, which defines the rate of decay
    # c: constant offset
    return a * np.exp(-t / tau) + c  # Return the computed decay value for each time point t


# Function for calculating passive force using force data occurring at the voltage peak
def calculating_passive_force(force, voltage_peaks):
    passive_force = []  # Initialize an empty list to store passive force values
    
    for peak_index in voltage_peaks:  # Iterate through each index in voltage_peaks
        # Use the force value at the exact timepoint of the voltage peak
        passive_force_value = force[peak_index]  # Get the force value at the peak index
        passive_force.append(passive_force_value)  # Append the force value to the passive_force list
    
    return np.array(passive_force)  # Convert the list to a numpy array and return it
  

# Function for calculating the amplitude which is the difference between the passive and active force
def calculating_amplitude(force, force_peaks, passive_force):
    print("Number of ms in force data:", len(force))  # Print the length of the force data array
    print("Timepoint of force peaks:", force_peaks)  # Print the indices of the force peaks
    print("Number of passive force values measured:", len(passive_force))  # Print the number of passive force values
    
    # Creates an empty array for population
    amplitudes = []  # Initialize an empty list to store amplitude values
    
    # Iterates through force peaks
    for i, peak in enumerate(force_peaks):
        if peak >= len(force):  # Error handling if peak index is out of bounds for force array
            print(f"IndexError: Peak index {peak} out of bounds for force array.")
            continue
        
        # Ensure index i does not exceed length of passive_force
        if i < len(passive_force):
            # Calculation of the amplitude
            amplitude_value = force[peak] - passive_force[i]  # Calculate the amplitude value
            # Appends the value
            amplitudes.append(amplitude_value)  # Append the amplitude value to the list
        else:
            # Error handling if no passive force value available for peak
            print(f"No passive force available for peak at index {i}")
            amplitudes.append(None)  # Append None to the list if no passive force value is available
    
    return np.array(amplitudes)  # Convert the list to a numpy array and return it


# Function for calculating time to peak
def calculating_time_to_peak(time, voltage_peaks, force_peaks):
    time_to_peak = []  # Initialize an empty list to store time-to-peak values
    
    # Iterates through each voltage peak
    for voltage_peak in voltage_peaks:
        # Finds the closest subsequent force peak
        subsequent_force_peaks = [fp for fp in force_peaks if fp > voltage_peak]
        
        # Ensures there is at least one subsequent force peak
        if subsequent_force_peaks:
            # Get the first subsequent force peak
            closest_force_peak = subsequent_force_peaks[0]
            # Calculates the time difference in milliseconds and ensure it's non-negative
            time_difference = time[closest_force_peak] - time[voltage_peak]
            # Converts the value to ms and rounds it
            time_to_peak.append(np.round(time_difference * 1000).astype(int))
        else:
            # If no subsequent force peak, does not add it to the list
            continue
    return np.array(time_to_peak)  # Convert the list to a numpy array and return it


# Function to calculate the time to 50 and 90% decay times
def calculating_decay(time, force, force_peaks, passive_force):
    # Creates empty lists to store the decay times
    time_to_50_decay = []
    time_to_90_decay = []
    
    # Iterates through the force peaks
    for i, peak in enumerate(force_peaks):
        peak_force = force[peak]  # Get the force value at the peak
        amplitude = peak_force - passive_force[i]  # Calculate the amplitude
        
        # Creates a target for force decay values
        target_50 = passive_force[i] + amplitude * 0.5  # 50% decay target
        target_90 = passive_force[i] + amplitude * 0.1  # 90% decay target
        
        # Determines the force values after the peak
        decay_region = force[peak:]
        # Determines the corresponding time values 
        time_region = time[peak:]
        
        # Find indices where decay reaches 50% and 90%
        idx_50 = np.where(decay_region <= target_50)[0]
        idx_90 = np.where(decay_region <= target_90)[0]
        
        if idx_50.size > 0:  # If there are indices where the force drops below 50%
            decay_time_50 = time_region[idx_50[0]] - time[peak]  # Calculate the time to 50% decay
            # Converts the value to milliseconds
            time_to_50_decay.append(np.round(decay_time_50 * 1000).astype(int))
        else:
            # If no decay to 50% found within the dataset, doesn't append a value
            time_to_50_decay.append(None)
        
        if idx_90.size > 0:  # If there are indices where the force drops below 90%
            decay_time_90 = time_region[idx_90[0]] - time[peak]  # Calculate the time to 90% decay
            # Again a conversion to milliseconds
            time_to_90_decay.append(np.round(decay_time_90 * 1000).astype(int))
        else:
            # Again, if no decay to 90% found within the dataset, doesn't append data to the list
            time_to_90_decay.append(None)
    
    # Returns the time point values in ms for time to 50% and 90% decay as arrays
    return np.array(time_to_50_decay), np.array(time_to_90_decay)


# Function to determine tau for fitting exponential decay to graphs
def calculating_tau(time, force, force_peaks, passive_force, voltage_peaks, data_rate):
    # Creates an empty list for tau
    tau = []

    # Iterates through the force peaks and checks for any data out of bounds
    for i, peak in enumerate(force_peaks):
        if peak >= len(force):
            print(f"Peak index {peak} out of bounds for force array.")
            tau.append(None)
            continue

        # Finds where the force first drops below 50% of the peak amplitude after the peak to determine where the decay starts
        decay_start_indices = np.where(force[peak:] <= passive_force[i] + 0.5 * (force[peak] - passive_force[i]))[0]
        if not decay_start_indices.size:
            # Confirmation statement if no 50% decay found
            print(f"No 50% decay found for peak at index {peak}")
            tau.append(None)
            continue
        
        # Adjusts the index relative to the full force array
        decay_start_index = decay_start_indices[0] + peak
        
        # Define the end index based on the next voltage peak or the specified duration (500 milliseconds)
        next_voltage_peak_indices = [vp for vp in voltage_peaks if vp > peak]
        if next_voltage_peak_indices:
            next_voltage_peak = next_voltage_peak_indices[0]
            end_index = min(next_voltage_peak, decay_start_index + int(0.500 * data_rate))
        else:
            end_index = decay_start_index + int(0.500 * data_rate)
        
        # Ensures that the end index does not exceed the length of the force array
        end_index = min(end_index, len(force) - 1)
        
        # Extracts the relevant time and force data for fitting the curve
        decay_time = time[decay_start_index:end_index] - time[decay_start_index]
        decay_force = force[decay_start_index:end_index]
        
        # Confirmation print statement
        print(f"Start of decay in ms: {decay_start_index}, End of decay in ms: {end_index}, Decay duration in ms: {len(decay_force)}")
        
        # Fits the decay curve using the original decay function
        initial_guess = (decay_force[0], 0.2, passive_force[i])
        try:
            popt, _ = curve_fit(decay_func, decay_time, decay_force, p0=initial_guess)
            tau.append(popt[1])  # Append the tau value (decay constant) to the list
        except Exception as e:
            # Print error statement if curve fitting cannot occur and states where
            print(f"Error fitting curve for peak at index {i}: {e}")
            tau.append(None)
    
    # Returns the tau values as an array for later use
    return np.array(tau)


# Function for plotting all data and analysis onto specific timepoints for user view and confirmation
def plot_data_with_annotations(data, decay_func, data_rate):
    # Extract relevant data from the input dictionary
    time = data['time']
    force = data['force']
    voltage = data['voltage']
    force_peaks = data['force_peaks']
    voltage_peaks = data['voltage_peaks']
    decay_50_durations = data['time_to_50_decay']
    decay_90_durations = data['time_to_90_decay']
    tau = data['tau']

    # Create a new figure and a set of subplots with a specific size
    fig, ax1 = plt.subplots(figsize=(15, 6))
    # Create a second y-axis that shares the same x-axis
    ax2 = ax1.twinx()
    # Set the title of the plot
    plt.title(f"Data from {min(time)} to {max(time)} seconds")
    
    # Set labels for the y-axes
    ax1.set_ylabel("Normalized force - mN/mm²")
    ax2.set_ylabel("Voltage (V)")
    # Set the x-axis label
    plt.xlabel('Time (s)')
    
    # Plot force data on the first y-axis
    ax1.plot(time, force, 'b-', label='Force')
    # Plot voltage data on the second y-axis
    ax2.plot(time, voltage, 'y-', label='Voltage')

    # Set the limits for the x-axis and y-axes
    ax1.set_xlim(min(time), max(time))
    ax1.set_ylim(min(force), 1.1 * max(force))
    ax2.set_ylim(min(voltage), 1.1 * max(voltage))

    # Plot force peaks as red dots
    ax1.scatter(time[force_peaks], force[force_peaks], color='red', label='Force Peaks')
    # Plot voltage peaks as orange dots
    ax2.scatter(time[voltage_peaks], voltage[voltage_peaks], color='orange', label='Voltage Peaks')

    for i, peak_index in enumerate(force_peaks):  # Iterate through each force peak
        if tau[i] is not None:  # Check if tau value is available for the current peak
            peak_time = time[peak_index]  # Get the time of the current peak
            # Find the start index for the decay region
            decay_start_index = np.where(time >= peak_time + decay_50_durations[i] / 1000)[0][0]
            
            # Find the next voltage peak that occurs after the current force peak
            next_voltage_peak_indices = [vp for vp in voltage_peaks if vp > peak_index]
            if next_voltage_peak_indices:
                next_voltage_peak = next_voltage_peak_indices[0]  # Get the next voltage peak index
                end_index = min(next_voltage_peak, decay_start_index + int(0.500 * data_rate))  # Determine the end index for the decay region
            else:
                end_index = decay_start_index + int(0.500 * data_rate)  # Default end index if no next voltage peak

            # Ensure the end index does not exceed the length of the force array
            end_index = min(end_index, len(force) - 1)
            # Extract the time values for the decay region
            decay_time = time[decay_start_index:end_index] - time[decay_start_index]
            # Extract the force values for the decay region
            decay_force = force[decay_start_index:end_index]

            # Print debugging information about the decay region
            print(f"Plotting tau for force peak {i} at index {peak_index}, decay start index: {decay_start_index}, end index: {end_index}")

            if len(decay_time) > 1 and len(decay_force) > 1:  # Check if there are enough data points for curve fitting
                initial_guess = (decay_force.max(), tau[i], force.min())  # Set initial guess for curve fitting
                bounds = ([0, 0.1 * tau[i], min(force)], [3 * decay_force.max(), 10 * tau[i], max(force)])  # Set bounds for curve fitting
                try:
                    popt, _ = curve_fit(decay_func, decay_time, decay_force, p0=initial_guess, bounds=bounds)  # Perform curve fitting
                    fitted_curve = decay_func(decay_time, *popt)  # Get the fitted curve values
                    # Plot the fitted curve on the first y-axis
                    ax1.plot(time[decay_start_index:end_index], fitted_curve, color='magenta', linestyle='-', linewidth=3, label='Tau/line of best fit' if i == 0 else "")
                except Exception as e:  # Handle any exceptions during curve fitting
                    print(f"Error fitting curve at peak index {i}: {e}")

    def calculate_and_plot_decay_times(peak_times, decay_durations, color, label):
        # Helper function to calculate and plot decay times
        for peak_time, duration in zip(peak_times, decay_durations):
            if duration is not None:  # Check if duration is available
                decay_time = peak_time + duration / 1000.0  # Calculate the decay time in seconds
                decay_index = (np.abs(time - decay_time)).argmin()  # Find the closest index to the decay time
                if decay_index < len(time):  # Ensure the index is within bounds
                    # Plot the decay point on the first y-axis
                    ax1.scatter(time[decay_index], force[decay_index], s=100, color=color, marker='x', label=label if peak_time == peak_times[0] else "")
            else:
                print(f"No decay recorded for {label}: Force peak occurs at {peak_time}s")  # Print message if no decay duration is recorded


    # Calculate and plot the decay times to 50% decay
    peak_times_50 = [time[idx] for idx in force_peaks if idx < len(time)]  # Extract peak times that are within the time range
    calculate_and_plot_decay_times(peak_times_50, decay_50_durations, 'green', 'Time to 50% Decay')  # Plot 50% decay times
    
    # Calculate and plot the decay times to 90% decay
    peak_times_90 = [time[idx] for idx in force_peaks if idx < len(time)]  # Extract peak times that are within the time range
    calculate_and_plot_decay_times(peak_times_90, decay_90_durations, 'purple', 'Time to 90% Decay')  # Plot 90% decay times
    
    # Add legends to the plot for the first and second y-axes
    ax1.legend(loc='upper left', bbox_to_anchor=(1.05, 1))  # Position legend for force data
    ax2.legend(loc='upper left', bbox_to_anchor=(1.05, 0.78))  # Position legend for voltage data
    
    # Adjust the layout to fit all elements within the figure
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    # Display the plot
    plt.show()
    return fig  # Return the figure object



# Function used to determine whether the overall graph is correct and analysis looks correct
def confirm_plot():
    root = tk.Tk()  # Create the root window for the tkinter application
    root.withdraw()  # Hide the root window

    # Display a message box asking the user to confirm if they are satisfied with the plot
    result = messagebox.askyesno("Confirm Plot", "Are you satisfied with the plot?")
    
    root.destroy()  # Destroy the root window to close the tkinter application

    return result  # Return the result of the message box (True if 'Yes' is selected, False if 'No' is selected)


# Function for preparing the analysed outputs from each of the peaks within the timepoint for later exportation
def peak_analysis(data_arrays, decay_func, data_rate):
    for i, data in enumerate(data_arrays):  # Iterate through each dataset in the list
        print(f"Processing dataset {i+1}/{len(data_arrays)}")  # Print the progress
        
        if 'force_peaks' not in data:  # Check if 'force_peaks' is missing in the current dataset
            print(f"Data at index {i} is missing 'force_peaks': {list(data.keys())}")  # Print a warning message
            continue  # Skip to the next dataset

        # Calculate passive force using voltage peaks
        passive_force = calculating_passive_force(data['force'], data['voltage_peaks'])
        # Calculate amplitude of the peaks
        amplitude = calculating_amplitude(data['force'], data['force_peaks'], passive_force)
        # Calculate the time to peak from voltage peaks to force peaks
        peak_times = calculating_time_to_peak(data['time'], data['voltage_peaks'], data['force_peaks'])
        # Calculate the time to 50% and 90% decay
        decay_50, decay_90 = calculating_decay(data['time'], data['force'], data['force_peaks'], passive_force)
        # Calculate tau values for the decay
        tau_values = calculating_tau(data['time'], data['force'], data['force_peaks'], passive_force, data['voltage_peaks'], data_rate)

        # Update the dataset with calculated values
        data.update({
            'passive_force': passive_force,
            'amplitude': amplitude,
            'peak_times': peak_times,
            'time_to_50_decay': decay_50,
            'time_to_90_decay': decay_90,
            'tau': tau_values
        })

        # Export the statistics for each peak within each timepoint
        export_peak_statistics(data, f"Timepoint {i + 1}")
        print("Statistics exported.")  # Print confirmation that statistics have been exported


# Function for exporting the statistical values for each peak within the timepoint
def export_peak_statistics(data, timepoint_identifier, file_path='peak_statistics.csv'):
    # Determines which keys are essential for the statistical output to occur and are valid
    required_keys = ['peak_times', 'time_to_50_decay', 'time_to_90_decay', 'tau', 'force_peaks', 'passive_force', 'amplitude']
    for key in required_keys:
        # Error handling for where any statistical parameter has not been exported
        if key not in data:
            print(f"{key} key missing, unable to export statistics for", timepoint_identifier)
            return

    # Print the data being exported for the given timepoint identifier
    print(f"Exporting data for {timepoint_identifier}")
    for key in required_keys:
        print(f"{key}: {data[key]}")

    # Ensures that the max length for each key is limited by the length of the data in question
    max_length = max(
        len(data['peak_times']),
        len(data['time_to_50_decay']),
        len(data['time_to_90_decay']),
        len(data['tau']),
        len(data['force'][data['force_peaks']]),
        len(data['passive_force']),
        len(data['amplitude'])
    )

    # Creates a fill function to prevent array misalignment which would prevent exportation of arrays
    fill_values = {
        'peak_times': None,
        'time_to_50_decay': None,
        'time_to_90_decay': None,
        'tau': None,
        'force': 0,
        'passive_force': None,
        'amplitude': None
    }

    def ensure_length(lst, length, fill_value):
        # Ensure the list has the specified length by padding with the fill value if necessary
        if lst is None:
            lst = [fill_value] * length
        else:
            lst = list(lst)
        if len(lst) < length:
            lst.extend([fill_value] * (length - len(lst)))
        return lst

    # Ensure all arrays have the same length
    peak_times = ensure_length(data['peak_times'], max_length, fill_values['peak_times'])
    time_to_50_decay = ensure_length(data['time_to_50_decay'], max_length, fill_values['time_to_50_decay'])
    time_to_90_decay = ensure_length(data['time_to_90_decay'], max_length, fill_values['time_to_90_decay'])
    tau = ensure_length(data['tau'], max_length, fill_values['tau'])
    active_force = ensure_length(list(data['force'][data['force_peaks']]), max_length, fill_values['force'])
    passive_force = ensure_length(data['passive_force'], max_length, fill_values['passive_force'])
    amplitude = ensure_length(data['amplitude'], max_length, fill_values['amplitude'])

    # Creates a pandas DataFrame to arrange the data in the correct format for exportation
    statistics = pd.DataFrame({
        'Timepoints': [timepoint_identifier] * max_length,
        'Time to Peak': peak_times,
        'Time to 50% Decay': time_to_50_decay,
        'Time to 90% Decay': time_to_90_decay,
        'Tau': tau,
        'Active Force': active_force,
        'Passive Force': passive_force,
        'Amplitude': amplitude
    })

    # Attempts to create a file and save it to a path
    try:
        directory = os.path.dirname(file_path)  # Extract the directory from the file path
        if directory and not os.path.exists(directory):  # Check if the directory exists
            os.makedirs(directory)  # Create the directory if it does not exist

        # Save the DataFrame to a CSV file, appending if the file exists
        statistics.to_csv(file_path, index=False, mode='a', header=not os.path.exists(file_path))
        abs_file_path = os.path.abspath(file_path)  # Get the absolute file path
        # Confirmation statement that the statistics have been written to the CSV file
        print(f"Exported peak statistics to '{abs_file_path}'.")
    except Exception as e:
        # Print error and confirmation statements if there is an issue writing the file to path
        print(f"Error exporting to CSV: {e}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Attempted file path: {file_path}")

def initialize_dataset():
    # Return a dictionary initialized to store various types of data related to the analysis
    return {
        'time': [],               # List to store time data
        'force': [],              # List to store force data
        'voltage': [],            # List to store voltage data
        'start_time': None,       # Placeholder for analysis start time
        'end_time': None,         # Placeholder for analysis end time
        'force_peaks': [],        # List to store indices of force peaks
        'voltage_peaks': [],      # List to store indices of voltage peaks
        'passive_force': [],      # List to store calculated passive forces
        'amplitude': [],          # List to store calculated amplitudes
        'peak_times': [],         # List to store times at which peaks occur
        'time_to_50_decay': [],   # List to store times to 50% decay
        'time_to_90_decay': [],   # List to store times to 90% decay
        'tau': []                 # List to store decay constants (tau values)
    }

# Function to create a .csv file that runs statistical analysis for the peaks within the timepoints and averages them
def generate_summary_statistics(original_csv, summary_csv):
    # Reads the original CSV file into a DataFrame
    df = pd.read_csv(original_csv)
    # Drop/removes rows with NaN values, as any peaks with incomplete data shouldn't be used for statistical analysis
    df = df.dropna()
    
    # Creates a numerical column from 'Timepoint' for sorting
    df['Timepoint_Number'] = df['Timepoint'].apply(lambda x: int(x.split(' ')[1]))
    # Sorts the DataFrame by this new column to ensure correct numerical order
    df.sort_values('Timepoint_Number', inplace=True)
    
    # Groups the data by 'Timepoint' after sorting
    grouped = df.groupby('Timepoint')
    # Calculates the summary statistics
    summary = grouped.agg({
        'Time to Peak': ['mean', 'sem', 'count'],  # Calculate mean, standard error of the mean, and count
        'Time to 50% Decay': ['mean', 'sem', 'count'],  # Calculate mean, standard error of the mean, and count
        'Time to 90% Decay': ['mean', 'sem', 'count'],  # Calculate mean, standard error of the mean, and count
        'Tau': ['mean', 'sem', 'count'],  # Calculate mean, standard error of the mean, and count
        'Active Force': ['mean', 'sem', 'count'],  # Calculate mean, standard error of the mean, and count
        'Passive Force': ['mean', 'sem', 'count'],  # Calculate mean, standard error of the mean, and count
        'Amplitude': ['mean', 'sem', 'count']  # Calculate mean, standard error of the mean, and count
    })
    
    # Flattens the multi-level columns
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    
    # Resets index to turn 'Timepoint' into a column again for the final CSV
    summary.reset_index(inplace=True)
    
    # Ensures Timepoint_Number is still available for sorting
    if 'Timepoint_Number' not in summary:
        summary['Timepoint_Number'] = summary['Timepoint'].apply(lambda x: int(x.split(' ')[1]))
    
    # Sorts the summary DataFrame again by 'Timepoint_Number' to ensure the correct, numerical order of the timepoints in the final output
    summary.sort_values('Timepoint_Number', inplace=True)
    
    # Removes the helper column before saving
    summary.drop('Timepoint_Number', axis=1, inplace=True)
    
    # Saves the summary to a new CSV file
    summary.to_csv(summary_csv, index=False)
    
    # Print confirmation message with the absolute path of the saved file
    print(f"Summary statistics exported to '{os.path.abspath(summary_csv)}'.")


# Main loop
def main():
    try:
        root = tk.Tk()
        root.withdraw()
        file_path = select_and_check_abf_file()
        if not file_path:
            return
        abf = load_abf_file(file_path)
        if not abf:
            return
        PlotDataWithTag(abf, sweep=0, channel=0, file_name="", specific_time=None)
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")           
    finally:
        root.destroy()

if __name__ == "__main__":
    main()

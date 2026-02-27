import numpy as np

#creates a class that allows interaction between graph and data within the graph
class DraggableLine:
    epsilon = 5  # Sensitivity for detecting clicks

    def __init__(self, line, text, update_callback, index, tagComments, x_range):
        """
        First we initialize a DraggableLine instance.

        The parameters required:
        line (Line2D): The line object that will be draggable.
        text (Text): The text object associated with the line, displaying the tag number.
        update_callback (function): The callback function to update the tag position.
        index (int): The index of the tag.

        Attributes:
        line (Line2D): The line object.
        text (Text): The text object.
        update_callback (function): Callback to update tag position.
        index (int): Tag index.
        _ind (int or None): Indicator for active dragging.
        press (float or None): Initial x-position when the line is pressed.
        ax (Axes): Axes object of the plot.
        canvas (FigureCanvas): Canvas of the figure for event connection.
        """
        self.line = line  # Store the line object
        self.text = text  # Store the text object
        self.update_callback = update_callback  # Store the callback function
        self.index = index  # Store the index of the tag
        self._ind = None  # Initialize the indicator for active dragging
        self.press = None  # Initialize the press position
        self.ax = line.axes  # Get the axes object from the line
        self.canvas = self.ax.figure.canvas  # Get the canvas from the axes
        self.tagComments = tagComments
        self.x_range = x_range

        # Connect the event handlers to the canvas
        self.cidpress = self.canvas.mpl_connect('button_press_event', lambda event: self.button_press_callback(event))
        self.cidrelease = self.canvas.mpl_connect('button_release_event', lambda event: self.button_release_callback(event))
        self.cidmotion = self.canvas.mpl_connect('motion_notify_event', lambda event: self.motion_notify_callback(event))
        #printed confirmation in a list of draggable lines for each tag 
        print(f"Created tag line for {index + 1}")

    def get_ind_under_point(self, event):
        """
        Check if the click is close enough to the line to start dragging.

        Parameters required:
        event (MouseEvent): The mouse event.

        Returns:
        int or None: 0 if close enough to drag, otherwise None.
        """
        x = self.line.get_xdata()[0]  # Get the x-position of the line
        xt = self.ax.transData.transform([x, 0])[0]  # Transform the x-position to display coordinates
        d = np.abs(xt - event.x)  # Calculate the distance from the click to the line
        if d < self.epsilon:  # Check if the distance is within the sensitivity threshold
            return 0  # Indicate that the line can be dragged
        return None  # Indicate that the line cannot be dragged

    def button_press_callback(self, event):
        """
        Handle the button press event to initiate dragging.

        Parameters required:
        event (MouseEvent): The mouse event.
        """
        if event.inaxes is None:  # Ignore clicks outside the axes
            return
        contains, _ = self.line.contains(event)  # Check if the click is on the line
        if not contains:  # Ignore clicks that are not on the line
            return
        self._ind = self.get_ind_under_point(event)  # Get the indicator for dragging
        self.press = event.xdata  # Store the initial x-position

    def button_release_callback(self, event):
        """
        Handle the button release event to stop dragging.

        Parameters:
        event (MouseEvent): The mouse event.
        """
        if event.button != 1:  # Ignore non-left mouse button releases
            return
        if self._ind is not None and self.press != event.xdata:  # Check if the line was dragged
            self.update_callback(event.xdata, self.index)  # Call the update callback
            print(f"Tag {self.index + 1} moved to position: {event.xdata} seconds")
        self._ind = None  # Reset the indicator
        self.press = None  # Reset the press position

    def motion_notify_callback(self, event):
        """
        Handle the motion notify event to update the line position during dragging.

        Parameters:
        event (MouseEvent): The mouse event.
        """
        if self._ind is None:  # Ignore if not dragging
            return
        if event.inaxes is None:  # Ignore movements outside the axes
            return
        if event.button != 1:  # Ignore non-left mouse button movements
            return
        new_x = event.xdata  # Get the new x-position
        if event.xdata < self.x_range[0]:
            new_x = self.x_range[0]
        if event.xdata > self.x_range[-1]:
            new_x = self.x_range[-1]
        self.text.set_x(new_x)  # Update the text position
        self.line.set_xdata([new_x, new_x])  # Update the line position
        self.line.set_label(f'Tag {self.index + 1} at {new_x:.3f}s: {self.tagComments[self.index]}')
        self.ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=8.5)  # Add a legend
        self.canvas.draw_idle()  # Redraw the canvas

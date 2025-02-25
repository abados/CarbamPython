from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel
from PyQt5.QtCore import QTimer, Qt


class Controll(QWidget):  # Inherit from QWidget
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent
        self.setFocusPolicy(Qt.StrongFocus)  # Ensure it can receive focus
        self.setFocus()  # Request focus explicitly
        self.fuel_speed = 0
        self.brake_speed = 0
        self.steering_speed = 0

        # Set focus policy to handle key events
        self.setFocusPolicy(Qt.StrongFocus)

        # Create sliders and their configurations
        self.fuel_slider = self.create_vertical_slider("Fuel (motor 3)", 1, 0, self.on_fuel_slider_change)
        self.brake_slider = self.create_vertical_slider("Brake (motor 2)", 0, 0, self.on_brake_slider_change)
        self.steering_slider = self.create_horizontal_slider("Steering (motor 1)", 4, 1, 4, self.on_steering_slider_change)

        # Timers for gradual resets
        self.fuel_reset_timer = QTimer(self)
        self.fuel_reset_timer.timeout.connect(self.reset_fuel_slider)
        self.fuel_reset_timer.start(10)

        self.brake_reset_timer = QTimer(self)
        self.brake_reset_timer.timeout.connect(self.reset_brake_slider)
        self.brake_reset_timer.start(30)

        self.steering_reset_timer = QTimer(self)
        self.steering_reset_timer.timeout.connect(self.reset_steering_slider)
        self.steering_reset_timer.start(30)

    def keyPressEvent(self, event):
        """Handle key press events."""
        key = event.key()
        if key == Qt.Key_Up:  # Increase fuel
            self.fuel_slider.setValue(min(self.fuel_slider.value() + 5, self.fuel_slider.maximum()))
        elif key == Qt.Key_Down:  # Increase brake
            self.brake_slider.setValue(min(self.brake_slider.value() + 5, self.brake_slider.maximum()))
        elif key == Qt.Key_Left:  # Decrease steering
            self.steering_slider.setValue(max(self.steering_slider.value() - 10, self.steering_slider.minimum()))
        elif key == Qt.Key_Right:  # Increase steering
            self.steering_slider.setValue(min(self.steering_slider.value() + 10, self.steering_slider.maximum()))
        elif key == Qt.Key_N:  # Neutral gear
            self.parent.set_gear("N")
        elif key == Qt.Key_P:  # Park gear
            self.parent.set_gear("P")
        elif key == Qt.Key_D:  # Drive gear
            self.parent.set_gear("D")
        elif key == Qt.Key_R:  # Reverse gear
            self.parent.set_gear("R")
        elif key == Qt.Key_Q:  # Arm/Disarm
            self.parent.toggle_arm()

    def create_vertical_slider(self, label, row, col, callback):
        """Create and configure a vertical slider."""
        layout = QVBoxLayout()
        slider = QSlider(Qt.Vertical)
        slider.setRange(0, 100)
        slider.setValue(0)
        slider.valueChanged.connect(callback)
        layout.addWidget(QLabel(label))
        layout.addWidget(slider)
        self.parent.main_layout.addLayout(layout, row, col)
        return slider

    def create_horizontal_slider(self, label, row, col_start, col_span, callback):
        """Create and configure a horizontal slider."""
        layout = QVBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(-500, 500)
        slider.setValue(0)
        slider.valueChanged.connect(callback)
        layout.addWidget(QLabel(label))
        layout.addWidget(slider)
        self.parent.main_layout.addLayout(layout, row, col_start, 1, col_span)
        return slider

    def on_fuel_slider_change(self, value):
        self.fuel_speed = value
        self.parent.log_message(f"Fuel speed changed to: {value}")

    def on_brake_slider_change(self, value):
        self.brake_speed = value
        self.parent.log_message(f"Brake speed changed to: {value}")

    def on_steering_slider_change(self, value):
        self.steering_speed = value
        self.parent.log_message(f"Steering angle changed to: {value}")

    def reset_fuel_slider(self):
        if self.fuel_slider.value() > 0:
            self.fuel_slider.setValue(self.fuel_slider.value() - 1)

    def reset_brake_slider(self):
        if self.brake_slider.value() > 0:
            self.brake_slider.setValue(self.brake_slider.value() - 1)

    def reset_steering_slider(self):
        if self.steering_slider.value() > 0:
            self.steering_slider.setValue(self.steering_slider.value() - 5)
        elif self.steering_slider.value() < 0:
            self.steering_slider.setValue(self.steering_slider.value() + 5)

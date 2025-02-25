from PyQt5.QtCore import QTimer, Qt


class KeyEventHandler:
    def __init__(self, app):
        self.app = app

    def handle_key_event(self, event):
        """Handle key presses to update sliders or other states."""
        key = event.key()
        if key == Qt.Key_Up:  # Increase fuel
            self.app.fuel_slider.setValue(min(self.app.fuel_slider.value() + 5, self.app.fuel_slider.maximum()))
        elif key == Qt.Key_Down:  # Increase brake
            self.app.brake_slider.setValue(min(self.app.brake_slider.value() + 5, self.app.brake_slider.maximum()))
        elif key == Qt.Key_Left:  # Decrease steering
            self.app.steering_slider.setValue(max(self.app.steering_slider.value() - 10, self.app.steering_slider.minimum()))
        elif key == Qt.Key_Right:  # Increase steering
            self.app.steering_slider.setValue(min(self.app.steering_slider.value() + 10, self.app.steering_slider.maximum()))
        elif key == Qt.Key_N:  # Neutral gear
            self.app.set_gear("N")
        elif key == Qt.Key_P:  # Park gear
            self.app.set_gear("P")
        elif key == Qt.Key_D:  # Drive gear
            self.app.set_gear("D")
        elif key == Qt.Key_R:  # Reverse gear
            self.app.set_gear("R")
        elif key == Qt.Key_Q:  # Toggle arm/disarm
            self.app.toggle_arm()

class SliderResetHandler:
    def __init__(self, fuel_slider, brake_slider, steering_slider):
        self.fuel_slider = fuel_slider
        self.brake_slider = brake_slider
        self.steering_slider = steering_slider

        # Timers for resetting each slider
        self.fuel_timer = QTimer()
        self.fuel_timer.timeout.connect(self.reset_fuel_slider)
        self.fuel_timer.start(50)  # Adjust interval as needed

        self.brake_timer = QTimer()
        self.brake_timer.timeout.connect(self.reset_brake_slider)
        self.brake_timer.start(50)

        self.steering_timer = QTimer()
        self.steering_timer.timeout.connect(self.reset_steering_slider)
        self.steering_timer.start(50)

    def reset_fuel_slider(self):
        """Gradually reset the fuel slider to default."""
        if self.fuel_slider.value() > 0:
            self.fuel_slider.setValue(self.fuel_slider.value() - 1)

    def reset_brake_slider(self):
        """Gradually reset the brake slider to default."""
        if self.brake_slider.value() > 0:
            self.brake_slider.setValue(self.brake_slider.value() - 1)

    def reset_steering_slider(self):
        """Gradually reset the steering slider to default."""
        if self.steering_slider.value() > 0:
            self.steering_slider.setValue(self.steering_slider.value() - 5)
        elif self.steering_slider.value() < 0:
            self.steering_slider.setValue(self.steering_slider.value() + 5)

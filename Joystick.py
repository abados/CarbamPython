import pygame


class RCSimulator:
    def __init__(self):
        """Initialize the RC Simulator."""
        pygame.init()
        self.joystick = None  # Joystick object
        self.channel_values = [1500] * 8  # Default PWM values for 8 channels
        self.initialize_joystick()
        self.Joystick_conected = False
    def initialize_joystick(self):
        """Initialize joystick if available."""
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self.Joystick_conected = True
            print(f"Joystick initialized: {self.joystick.get_name()}")
        else:
            print("No joystick found!")

    def poll_joystick(self):
        """Poll joystick for channel values."""
        if not self.joystick:
            # print("Joystick not connected.")
            return self.channel_values

        pygame.event.pump()  # Process joystick events

        # Update axes values for Channels 1-4
        for i in range(min(4, self.joystick.get_numaxes())):
            axis_value = self.joystick.get_axis(i)
            pwm_value = int(1500 + axis_value * 500)  # Map axis (-1 to 1) to PWM (1000 to 2000)
            self.channel_values[i] = pwm_value
            self.Joystick_conected = True

        # Update Channel 5 (Button 1)
        if self.joystick.get_numbuttons() > 1:  # Ensure Button 1 exists
            self.channel_values[4] = 2000 if self.joystick.get_button(0) else 1000

        # Update Channel 6 (Button 2)
        if self.joystick.get_numbuttons() > 2:  # Ensure Button 2 exists
            self.channel_values[5] = 2000 if self.joystick.get_button(1) else 1000

        # Update Channel 7 using Buttons 4 and 5
        if self.joystick.get_numbuttons() > 3:  # Ensure Buttons 4 and 5 exist
            if self.joystick.get_button(3):  # Down position (Button 4 pressed)
                self.channel_values[6] = 1000
            elif self.joystick.get_button(4):  # Up position (Button 5 pressed)
                self.channel_values[6] = 2000
            else:  # Neutral position (Both off)
                self.channel_values[6] = 1500

        return self.channel_values

    def get_channel_values(self):
        """Get the current channel values."""
        return self.channel_values

    def close(self):
        """Cleanup resources."""
        pygame.quit()


# Example Usage
if __name__ == "__main__":
    rc_simulator = RCSimulator()

    try:
        while True:
            channel_values = rc_simulator.poll_joystick()
            # print("Channel Values:", channel_values)
            # print(rc_simulator.Joystick_conected)
    except KeyboardInterrupt:
        print("Exiting...")
        rc_simulator.close()

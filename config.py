import os
import sys
import ast

# Default configuration
DEFAULT_CONFIG = {
    "main_video_host": "192.168.1.101",
    "main_video_port": 8081,
    "secondary_video_host": "192.168.1.101",
    "secondary_video_port": 8082,
    "arduino_ip": "192.168.1.177",
    "arduino_port": 80,
    "arduino_socket_port": 80,
    "fps": 10,
    "resolution": 3,
    "min_steering": 1000,
    "max_steering": 2000,
    "fuel_offset": 100,
    "min_fuel": 1000,
    "max_fuel": 1550,
    "min_brake": 1000,
    "max_brake": 1800,
    "gear_P_arduino_value": 2000,
    "gear_R_arduino_value": 1800,
    "gear_N_arduino_value": 1400,
    "gear_D_arduino_value": 1300,
    "gear_L_arduino_value": 1100,
    "fuel_slide_update_rate": 5,
    "brake_slide_update_rate": 2,
    "fuel_multiplier": 1.0,
    "fuel_auto_reset":  0,
    "brake_multiplier": 1.0,
    "steering_multiplier": 1.0,
    "steering_TH":350,
    "arduino_update_ms_rate": 100,
    "path_to_save_video": r"C:\Users\LARA_B\Desktop\test video",
    "connected_to_system": 1,
    "Camera_Locations": 1
}


# Resolution mapping for use cases 1-5
RESOLUTION_MAPPING = {
    "1": (160, 120),  # QQVGA
    "2": (320, 240),  # QVGA
    "3": (640, 480),  # VGA
    "4": (1280, 720),  # HD
    "5": (1920, 1080),  # Full HD
}

def get_exe_folder():
    """Get the folder where the .exe (or script) is located."""
    if getattr(sys, "frozen", False):  # If running as an .exe
        return os.path.dirname(sys.executable)
    else:  # If running as a script
        return os.path.dirname(os.path.abspath(__file__))

def import_config(config_file="config.txt", default_config=DEFAULT_CONFIG):
    """
    Ensure the configuration file exists, and load the configuration.
    If the file doesn't exist, create it with default values.
    """
    exe_folder = get_exe_folder()  # Get the folder where the executable/script is running
    config_path = os.path.join(exe_folder, config_file)

    # Create default configuration file if it doesn't exist
    if not os.path.exists(config_path):
        with open(config_path, "w") as file:
            for key, value in default_config.items():
                file.write(f"{key}={value}\n")
        print(f"Default configuration file '{config_path}' created.")

    # Load configuration from file
    config = {}
    try:
        with open(config_path, "r") as file:
            for line in file:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    config[key.strip()] = value.strip()
        print(f"Configuration loaded from '{config_path}'.")
    except Exception as e:
        print(f"Error reading configuration file '{config_path}': {e}")
        config = default_config

    # Ensure correct types for values
    config["main_video_port"] = int(config.get("main_video_port", default_config["main_video_port"]))
    config["sacandary_video_port"] = int(config.get("secondary_video_port", default_config["secondary_video_port"]))
    config["arduino_port"] = int(config.get("arduino_port", default_config["arduino_port"]))
    config["arduino_socket_port"] = int(config.get("arduino_socket_port", default_config["arduino_socket_port"]))
    config["fps"] = int(config.get("fps", default_config["fps"]))
    config["resolution"] = int(config.get("resolution", default_config["resolution"]))
    config["min_steering"] = int(config.get("min_steering", default_config["min_steering"]))
    config["max_steering"] = int(config.get("max_steering", default_config["max_steering"]))
    config["fuel_offset"] = int(config.get("fuel_offset", default_config["fuel_offset"]))
    config["min_fuel"] = int(config.get("min_fuel", default_config["min_fuel"]))
    config["max_fuel"] = int(config.get("max_fuel", default_config["max_fuel"]))
    config["min_brake"] = int(config.get("min_brake", default_config["min_brake"]))
    config["max_brake"] = int(config.get("max_brake", default_config["max_brake"]))

    config["gear_P_arduino_value"] = int(config.get("gear_P_arduino_value", default_config["gear_P_arduino_value"]))
    config["gear_D_arduino_value"] = int(config.get("gear_D_arduino_value", default_config["gear_D_arduino_value"]))
    config["gear_R_arduino_value"] = int(config.get("gear_R_arduino_value", default_config["gear_R_arduino_value"]))
    config["gear_N_arduino_value"] = int(config.get("gear_N_arduino_value", default_config["gear_N_arduino_value"]))
    config["gear_L_arduino_value"] = int(config.get("gear_L_arduino_value", default_config["gear_L_arduino_value"]))



    config["fuel_slide_update_rate"] = int(config.get("fuel_slide_update_rate", default_config["fuel_slide_update_rate"]))
    config["fuel_auto_reset"] = int(config.get("fuel_auto_reset", default_config["fuel_auto_reset"]))

    config["brake_slide_update_rate"] = int(config.get("brake_slide_update_rate", default_config["brake_slide_update_rate"]))
    config["fuel_multiplier"] = float(config.get("fuel_multiplier", default_config["fuel_multiplier"]))
    config["brake_multiplier"] = float(config.get("brake_multiplier", default_config["brake_multiplier"]))
    config["steering_multiplier"] = float(config.get("steering_multiplier", default_config["steering_multiplier"]))
    config["arduino_update_ms_rate"] = int(config.get("arduino_update_ms_rate", default_config["arduino_update_ms_rate"]))
    config["connected_to_system"] = int(config.get("connected_to_system", default_config["connected_to_system"]))
    config["path_to_save_video"] = config.get("path_to_save_video", default_config["path_to_save_video"])
    config["main_video_host"] = config.get("main_video_host", default_config["main_video_host"])
    config["secondary_video_host"] = config.get("secondary_video_host", default_config["secondary_video_host"])

    config["Camera_Locations"] = config.get("Camera_Locations", default_config["Camera_Locations"])


    return config

# Example usage
if __name__ == "__main__":
    config = import_config()
    print("Loaded Configuration:", config)

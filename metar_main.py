# metar_main.py
# E-Paper METAR Display - by Mark Harris
# Version 2.2 - Modified for 4-Grayscale epd4in2
# Part of Epaper Display project found at; https://github.com/markyharris/metar/
#
# UPDATED to New FAA API 12-2023, https://aviationweather.gov/data/api/
#
# Thanks to Aerodynamics for providing a great start for this project
# Visit his page at;
#   https://github.com/aerodynamics-py/WEATHER_STATION_PI
#
# This script uses the NEW FAA API at aviationweather.gov;
#   https://aviationweather.gov/data/api/#/Dataserver/dataserverMetars
# This script also uses IFR Low maps from;
#   https://vfrmap.com/map_api.html
#
# A new feature was added that allows the user to specify which layouts that should be displayed
# The user will have to setup a list variable in 'metar_setting.py' and set 'use_preferred' to 1
# See the file, 'metar_settings.py' for an example.
#
# Unit conversions were added to allow the user to choose ft vs meter, km/h vs knots etc.
# These will be selected from either the 'metar_settings.py' file or better, the web admin page.
#
# While not part of the scripts, it is suggested to setup a nightly reboot using crontab
# see; https://smarthomepursuits.com/how-to-reboot-raspberry-pi-on-a-schedule/ for information
#
# The script will then either display the json weather information provided,
# or if the json information is not given, the script will use the data scraped
# from the raw metar string provided. However, the json data is a bit more accurate.
#
# Dynamic icon's are displayed depending on the value of each weather field.
#
# For specific info on using e-paper display with RPi, see;
#   https://www.waveshare.com/wiki/Template:Raspberry_Pi_Guides_for_SPI_e-Paper
# For information on the specific display used for this project see;
#   https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT_(B) -- NOTE: CODE MODIFIED FOR 4in2 GRAYSCALE
#
# Software is organized into separate scripts depending on its focus
#   metar_main.py - loads the other files as necessary and executes layout routine
#   metar_routines.py - metar specific routines, typically needed for decoding and scraping
#   metar_layouts.py - houses all the different layouts available for display
#   metar_display.py - provides the routines and fonts needed to print to e-paper (LARGELY BYPASSED in this version)
#   metar_settings.py - User defined default settings such as airport and update interval
#   metar_remarks.py - file created from FAA's definitions of a METAR's remarks (RMK)
#   shutdown.py - Used to blank e-Paper on shutdown.
#   metar_startup.py - Used to display the web admin URL upon boot/reboot
#   metar.html - html file used to control the metar display
#   data.txt - stores the last run setup for restart purposes
#   temp_pic.png - temporary storage of IFR Low map image when that layout is used
#   webapp.py - flask module to provide needed data to epaper.html and provide simple web server


# Imports
# Keep existing imports and add traceback
from metar_layouts import *
from metar_settings import *
from metar_routines import * # Ensures Metar class should be imported
# Import PIL for direct drawing
from PIL import Image, ImageDraw, ImageFont
import time
import requests
import json
import sys
import os
import sys
import logging # Added for consistency with Waveshare examples
import config
import traceback # <--- ADDED IMPORT

# Setup logging
logging.basicConfig(level=logging.INFO) # Use INFO or DEBUG

# Import specific display driver
from waveshare_epd import epd4in2

# --- Define Fonts and Assign to Config Module ---
basedir = os.path.dirname(os.path.realpath(__file__))
fontdir = os.path.join(basedir, 'fonts')
regular_font_path = os.path.join(fontdir, 'noto', 'NotoSansMono-Regular.ttf')
bold_font_path = os.path.join(fontdir, 'noto', 'NotoSansMono-Bold.ttf')

try:
    logging.info(f"Loading regular font: {regular_font_path}")
    logging.info(f"Loading bold font: {bold_font_path}")

    # Assign fonts directly to the imported config module
    config.font16 = ImageFont.truetype(regular_font_path, 16)
    config.font16b = ImageFont.truetype(bold_font_path, 16)
    config.font24 = ImageFont.truetype(regular_font_path, 24)
    config.font24b = ImageFont.truetype(bold_font_path, 24)
    config.font36 = ImageFont.truetype(regular_font_path, 36)
    config.font36b = ImageFont.truetype(bold_font_path, 36)
    config.font48 = ImageFont.truetype(regular_font_path, 48)
    config.font48b = ImageFont.truetype(bold_font_path, 48)
    # Add others if needed...

    logging.info("Fonts loaded successfully into config.")

except Exception as e: # Catch generic Exception during font loading
    logging.error(f"Font file not found or cannot be read: {e}")
    logging.error(f"Regular: {regular_font_path}")
    logging.error(f"Bold: {bold_font_path}")
    logging.warning("Using default PIL font as fallback.")
    # Assign default fonts to the config module
    config.font16 = ImageFont.load_default()
    config.font16b = ImageFont.load_default()
    config.font24 = ImageFont.load_default()
    config.font24b = ImageFont.load_default()
    config.font36 = ImageFont.load_default()
    config.font36b = ImageFont.load_default()
    config.font48 = ImageFont.load_default()
    config.font48b = ImageFont.load_default()
# ---------------------------------------------------------------------

# Layouts - add new layouts to this list as necessary
# Ensure these layout functions are updated to accept (epd, Limage, draw, ...) signature
layout_list = [layout_wind] # Add layout routine names here
use_preferred = 0

# --- Command Line Argument Processing ---
# (Keep existing cmdline arg processing as is)
print('len(sys.argv):',len(sys.argv)) # debug
print('sys.argv:',sys.argv,'\n') # debug

if len(sys.argv) >= 10:
    logging.info('Using Args passed from web admin')
    airport = str(sys.argv[1].upper())
    use_disp_format = int(sys.argv[2])
    interval = int(sys.argv[3])
    use_remarks = int(sys.argv[4])
    wind_speed_units = int(sys.argv[5])
    cloud_layer_units = int(sys.argv[6])
    visibility_units = int(sys.argv[7])
    temperature_units = int(sys.argv[8])
    pressure_units = int(sys.argv[9])
    preferred_layouts = (sys.argv[10]) # string representation of the the list. Needs to be converted back to list

    print('\033[96mpreferred_layouts:',preferred_layouts,'\033[0m') # debug
    if preferred_layouts == 'na':
        use_preferred = 0
    else:
        use_preferred = 1
else:
    logging.info('Using Args from settings.py file')
    # Assuming these are loaded from metar_settings import *
    # airport, use_disp_format, interval, etc.

print("\nAirport\t", "Layout\t", "Update\t", "Remarks")
print(str(airport)+"\t", str(use_disp_format)+"\t", str(interval)+"\t", str(use_remarks)+"\n")


def main(epd, Limage, draw): # Accept epd, Limage, draw
    global metar, remarks, print_table, use_remarks, use_disp_format, interval, wind_speed_units, cloud_layer_units, visibility_units, temperature_units, pressure_units, layout_list, preferred_layouts, use_preferred

    # Choose which layout to use.
    # Pass epd, Limage, draw, and other params to the layout functions
    if use_disp_format == -1:
        # random_layout needs update to accept (epd, Limage, draw, ...)
        random_layout(epd, Limage, draw, metar, remarks, print_table, use_remarks, use_disp_format, interval, wind_speed_units, cloud_layer_units, visibility_units, temperature_units, pressure_units, layout_list)

    elif use_disp_format == -2:
        # cycle_layout needs update to accept (epd, Limage, draw, ...)
        cycle_layout(epd, Limage, draw, metar, remarks, print_table, use_remarks, use_disp_format, interval, wind_speed_units, cloud_layer_units, visibility_units, temperature_units, pressure_units, layout_list, preferred_layouts, use_preferred)

    else:
        # Call the specific layout chosen by index
        if 0 <= use_disp_format < len(layout_list):
            print("Layout -->",use_disp_format,'<--') # debug
            # Call the layout function with the new signature
            layout_list[use_disp_format](epd, Limage, draw, metar, remarks, print_table, use_remarks, use_disp_format, interval, wind_speed_units, cloud_layer_units, visibility_units, temperature_units, pressure_units)
        else:
            logging.error(f"Invalid layout index selected: {use_disp_format}")
            # Optionally draw an error message on Limage using 'draw'
            draw.text((10, 100), f"Error: Invalid Layout {use_disp_format}", fill=epd.GRAY4, font=font24)

    # Printing to e-Paper is now handled in the main loop after main() returns

    return True # Indicate success


# Execute code starting here.
if __name__ == "__main__":
    try:
        logging.info("Initializing E-Paper display epd4in2...")
        epd = epd4in2.EPD() # Instantiate instance for display.
        logging.info("Setting display to 4 Grayscale mode...")
        epd.Init_4Gray()    # Initialize for 4 grayscale mode ONCE.
        logging.info("Clearing display...")
        epd.Clear()         # Clear screen once initially.
        time.sleep(1)       # Allow time for clearing

        while True:
            try:
                # --- Create Image Buffer and Drawing Context ---
                logging.info("Creating new Image buffer (Mode L)")
                # Create image with white background (GRAY1)
                Limage = Image.new('L', (epd.width, epd.height), epd.GRAY1)
                draw = ImageDraw.Draw(Limage) # Get drawing context

                # --- Get METAR Data ---
                current_time = time.strftime("%m/%d/%Y %H:%M", time.localtime())
                logging.info(f"Fetching METAR for {airport} at {current_time}")

                metar = Metar(airport) # Fetch data using Metar class
                raw_metar_text = get_rawOb(metar) # Get raw text

                if raw_metar_text and len(raw_metar_text) > 0:
                    logging.info(f'Raw METAR: {raw_metar_text}')
                    remarks, print_table = decode_remarks(raw_metar_text)
                    flightcategory, icon = flight_category(metar) # Assumes metar object is populated correctly
                    logging.info(f"Flight Category: {flightcategory}")
                else:
                    logging.warning("No METAR Being Reported or fetch failed.")
                    # Draw message directly onto Limage
                    draw.text((20, 100), f"No METAR Data for {airport}", fill=epd.GRAY4, font=font24)
                    remarks, print_table = "", [] # Set defaults
                    flightcategory = "N/A" # Set default category

                # --- Build Display Layout ---
                logging.info("Building display layout...")
                main(epd, Limage, draw) # Call main function to draw on Limage

                # --- Update E-Paper Screen ---
                logging.info("Generating 4Gray Buffer...")
                gray_buffer = epd.getbuffer_4Gray(Limage)

                logging.info("Sending 4Gray Buffer to display...")
                epd.display_4Gray(gray_buffer)
                logging.info("Display update complete.")

                # --- Calculate Sleep Interval ---
                sleep_interval = 0
                if interval != 0: # Manual interval set
                    sleep_interval = interval
                    logging.info(f"Manual sleep interval: {sleep_interval} seconds")
                else: # Auto interval based on flight category
                    if flightcategory == "VFR":
                        sleep_interval = 3600 # 1 hour
                        logging.info("Auto Interval VFR - Sleep 1 hour")
                    elif flightcategory == "MVFR":
                        sleep_interval = 1800 # 30 mins
                        logging.info("Auto Interval MVFR - Sleep 30 mins")
                    elif flightcategory == "IFR":
                        sleep_interval = 1200 # 20 mins
                        logging.info("Auto Interval IFR - Sleep 20 mins")
                    elif flightcategory == "LIFR":
                        sleep_interval = 600 # 10 mins
                        logging.info("Auto Interval LIFR - Sleep 10 mins")
                    else: # N/A or other case
                        sleep_interval = 1800 # Default to 30 mins if category unknown
                        logging.info("Auto Interval Unknown/N/A - Sleep 30 mins")

                logging.info(f"Sleeping for {sleep_interval} seconds...")
                time.sleep(sleep_interval)
                # Do NOT put epd.sleep() here if looping

            except Exception as e:
                logging.error("Error Occurred in Main Loop Execution")
                exception_type, exception_object, exception_traceback = sys.exc_info()
                filename = os.path.basename(exception_traceback.tb_frame.f_code.co_filename)
                line_number = exception_traceback.tb_lineno
                logging.error(f"Error: {e}")
                logging.error(f"Exception type: {exception_type}")
                logging.error(f"File name: {filename}")
                logging.error(f"Line number: {line_number}")
                print(traceback.format_exc()) # Print full traceback for debugging

                # --- Display Error on E-Paper ---
                try:
                    logging.info("Attempting to display error message on e-Paper...")
                    # Create a fresh image for the error message
                    ErrorImage = Image.new('L', (epd.width, epd.height), epd.GRAY1) # White background
                    draw_error = ImageDraw.Draw(ErrorImage)

                    # Simple Error Message
                    msg1 = "- Error Occurred -"
                    msg2 = "Check Logs. Retrying in 60s..."
                    w1, h1 = draw_error.textsize(msg1, font=font36b)
                    draw_error.text(((epd.width - w1) / 2, 80), msg1, fill=epd.GRAY4, font=font36b)
                    w2, h2 = draw_error.textsize(msg2, font=font24)
                    draw_error.text(((epd.width - w2) / 2, 130), msg2, fill=epd.GRAY4, font=font24)

                    # Detailed Info (optional, might be too much)
                    err_line1 = f"Type: {exception_type.__name__}"
                    err_line2 = f"File: {filename} Line: {line_number}"
                    draw_error.text((20, 180), err_line1, fill=epd.GRAY3, font=font16)
                    draw_error.text((20, 200), err_line2, fill=epd.GRAY3, font=font16)
                    draw_error.text((20, 220), str(e)[:40], fill=epd.GRAY3, font=font16) # First part of error message

                    error_buffer = epd.getbuffer_4Gray(ErrorImage)
                    epd.display_4Gray(error_buffer)
                    logging.info("Error message displayed.")

                except Exception as display_err:
                    logging.error(f"Could NOT display error message on e-Paper: {display_err}")

                logging.info("Sleeping for 60 seconds after error...")
                time.sleep(60) # Wait before retrying after an error

    except IOError as e:
        logging.error(f"IOError during initialization or font loading: {e}")
        print(traceback.format_exc())
    except KeyboardInterrupt:
        logging.info("Ctrl+C detected. Exiting...")
        epd.sleep() # Put display to sleep
        time.sleep(1)
        epd4in2.epdconfig.module_exit(cleanup=True) # Clean up GPIO
        exit()
    except Exception as init_err:
        logging.critical(f"FATAL: Unhandled exception during setup: {init_err}")
        print(traceback.format_exc())
        # Attempt cleanup if possible
        try:
            epd4in2.epdconfig.module_exit(cleanup=True)
        except NameError:
            pass # epd object might not exist
        exit()

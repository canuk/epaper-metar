# metar_layouts.py
# Layouts for Metar Display - Mark Harris
# Version 2.1 - Modified for 4-Grayscale epd4in2 direct drawing
# Part of Epaper Display project found at; https://github.com/markyharris/metar/
#
# UPDATED FAA API 12-2023, https://aviationweather.gov/data/api/
#

# Imports
from metar_routines import *
from metar_settings import * # Keep for settings variables if needed
from datetime import datetime, timedelta
import random
import math
# Import PIL directly if needed for fonts (but fonts should be passed from main)
from PIL import Image, ImageDraw, ImageFont
import os # For font paths if loaded locally
import config

# Misc Variables
d = " " # delimiter
cycle_num = 0
pref_cycle = 0

# Utility routines
# These need modification if they used the 'display' object's methods
def center_line_pil(draw, width, text, font): # Pass draw context and total width
    w, h = draw.textsize(text, font=font)
    return int((width - w) / 2) # Return X coordinate

def last_update():
    now = datetime.now()
    # Adjust format if needed "%I:%M %p" is 12-hour AM/PM
    last_update = "Last Updated at "+now.strftime("%H:%M %Z") # 24-hour + timezone
    return last_update

# check_preferred_layout remains the same as it doesn't use display object

# disp_ip needs significant changes if used, as it relied heavily on 'display'
# Need to reimplement using passed 'draw' object and basic PIL commands.
# def disp_ip(epd, Limage, draw, ip_address): ...


# cycle_layout needs update to accept and pass epd, Limage, draw
def cycle_layout(epd, Limage, draw, metar, remarks, print_table, use_remarks, use_disp_format, interval, wind_speed_units, cloud_layer_units, visibility_units, temperature_units, pressure_units, layout_list, preferred_layouts, use_preferred):
    global cycle_num, pref_cycle

    if use_preferred == 1:
        p_layouts_lst = [int(a) for a in str(preferred_layouts)]
        # print('p_layouts_lst:',p_layouts_lst) # debug
        if not p_layouts_lst:
             print("Error: Preferred layout list is empty or invalid.")
             # Optionally draw error message on Limage
             return

        current_pref_index = pref_cycle % len(p_layouts_lst)
        layout_index_to_use = p_layouts_lst[current_pref_index]

        if 0 <= layout_index_to_use < len(layout_list):
             print(f'\033[96m!!! Preferred Layout Index: {layout_index_to_use} IN LIST !!!\033[0m')
             cycle_pick = layout_list[layout_index_to_use]
             # Call with the new signature
             cycle_pick(epd, Limage, draw, metar, remarks, print_table, use_remarks, use_disp_format, interval, wind_speed_units, cloud_layer_units, visibility_units, temperature_units, pressure_units)
             pref_cycle = (pref_cycle + 1) # Cycle through preferred list
        else:
             print(f"Error: Preferred layout index {layout_index_to_use} out of range.")
             # Draw error

    else: # Cycle through all layouts
         current_cycle_index = cycle_num % len(layout_list)
         print(f'\033[91m--> cycle_num Layout Index: {current_cycle_index} <--\033[0m') # debug
         cycle_pick = layout_list[current_cycle_index]
         # Call with the new signature
         cycle_pick(epd, Limage, draw, metar, remarks, print_table, use_remarks, use_disp_format, interval, wind_speed_units, cloud_layer_units, visibility_units, temperature_units, pressure_units)
         cycle_num = (cycle_num + 1) # Cycle through all


# random_layout needs update to accept and pass epd, Limage, draw
def random_layout(epd, Limage, draw, metar, remarks, print_table, use_remarks, use_disp_format, interval, wind_speed_units, cloud_layer_units, visibility_units, temperature_units, pressure_units, layout_list):
    if not layout_list:
         print("Error: Layout list is empty.")
         return
    rand_pick = random.choice(layout_list)
    # print('\033[91m--> Random Layout:',str(rand_pick)[10:18],'<--\033[0m') # debug
    print(f'\033[91m--> Random Layout: {rand_pick.__name__} <--\033[0m')
    # Call with the new signature
    rand_pick(epd, Limage, draw, metar, remarks, print_table, use_remarks, use_disp_format, interval, wind_speed_units, cloud_layer_units, visibility_units, temperature_units, pressure_units)

##################
#  Layout: Wind  #
##################
def layout_wind(epd, Limage, draw, metar, remarks, print_table, use_remarks, use_disp_format, interval, wind_speed_units, cloud_layer_units, visibility_units, temperature_units, pressure_units):
    """
    Wind visualization layout - Adapted for 4-grayscale epd4in2 using direct PIL drawing.
    Includes runway markings, adjusted colors, larger runway number, tighter spacing,
    and pseudo-3D arrow.
    """
    # --- Font access via 'config' module ---

    # --- Metar Data ---
    try:
        # ... (Keep the robust Metar data fetching/decoding) ...
        if not metar or not hasattr(metar, 'data') or not metar.data:
             print("Error: METAR object is empty or invalid in layout_wind.")
             draw.text((10, 100), "Error: Invalid METAR data", fill=epd.GRAY4, font=config.font24)
             return
        raw_metar_text = get_rawOb(metar)
        if not raw_metar_text or raw_metar_text == 'n/a':
            print(f"Warning: No raw METAR text available for decoding in layout_wind.")
            flightcategory, airport = "N/A", "N/A"; decoded_wndir, decoded_wnspd = "0", "0"
            draw.text((10,100), "No METAR text", fill=epd.GRAY4, font=config.font24)
            descript = "N/A"; cctype_lst, ccheight_lst, dis_unit = [], [], ""; vis, vis_unit = "N/A", ""; tempf, temp_unit = "N/A", ""
        else:
            decoded_airport, decoded_time, decoded_wndir, decoded_wnspd, decoded_wngust, decoded_vis, \
                decoded_alt, decoded_temp, decoded_dew, decoded_cloudlayers, decoded_weather, decoded_rvr \
                = decode_rawmessage(raw_metar_text)
            flightcategory, icon = flight_category(metar)
            airport = decoded_airport if decoded_airport else "N/A"
            descript = get_wxstring(metar)
            cctype_lst, ccheight_lst, dis_unit = get_clouds(metar, cloud_layer_units)
            vis, vis_unit = get_visib(metar, visibility_units)
            tempf, temp_unit = get_temp(metar, temperature_units)
    except Exception as e:
        print(f"Error decoding METAR or getting data in layout_wind: {e}")
        flightcategory, airport = "N/A", "Error"; decoded_wndir, decoded_wnspd = "0", "0"
        descript = "Error"; cctype_lst, ccheight_lst, dis_unit = [], [], ""; vis, vis_unit = "N/A", ""; tempf, temp_unit = "N/A", ""
        draw.text((10, 100), "Error: Decode Fail", fill=epd.GRAY4, font=config.font24)

    # --- Constants ---
    runway_number = 18
    HEADER_HEIGHT = 65
    WIND_INFO_Y = 85
    VISUALIZATION_Y = 170 # Base Y for visualization area
    LEFT_MARGIN = 10
    SCREEN_WIDTH = epd.width
    SCREEN_HEIGHT = epd.height
    white = epd.GRAY1
    light_gray = epd.GRAY2
    dark_gray = epd.GRAY3
    black = epd.GRAY4

    # --- Drawing ---
    # Header
    draw.rectangle((0, 0, SCREEN_WIDTH, HEADER_HEIGHT), fill=black)
    airport_text = airport[:10]
    draw.text((LEFT_MARGIN, 10), airport_text, fill=white, font=config.font48b)
    fc_x = SCREEN_WIDTH - 75; fc_y = 15
    # Use font24b for flight category
    fc_font = config.font24b
    if flightcategory and flightcategory != "N/A":
         try: fc_bbox = draw.textbbox((0,0), flightcategory, font=fc_font); fc_w = fc_bbox[2] - fc_bbox[0]; fc_h = fc_bbox[3] - fc_bbox[1]
         except AttributeError: fc_w, fc_h = draw.textsize(flightcategory, font=fc_font)
         if flightcategory == "VFR" or flightcategory == "MVFR": draw.text((fc_x, fc_y), flightcategory, fill=white, font=fc_font)
         else: box_margin = 5; draw.rectangle((fc_x - box_margin, fc_y - box_margin, fc_x + fc_w + box_margin, fc_y + fc_h + box_margin), fill=white); draw.text((fc_x, fc_y), flightcategory, fill=black, font=fc_font)
    else: draw.text((fc_x, fc_y), "N/A", fill=white, font=fc_font)

    # Wind Info Text
    try: wind_direction = int(decoded_wndir) if decoded_wndir and decoded_wndir.isdigit() else 0
    except: wind_direction = 0
    try: wind_speed = float(decoded_wnspd) if decoded_wnspd and decoded_wnspd != "Calm" else 0
    except: wind_speed = 0
    ws_unit_label = "kts"
    if wind_speed_units == 1: ws_unit_label = "mph"
    elif wind_speed_units == 2: ws_unit_label = "kts"
    wind_text = f"Wind: {str(wind_direction).zfill(3)}° at {int(round(wind_speed))} {ws_unit_label}"
    draw.text((LEFT_MARGIN, WIND_INFO_Y), wind_text, fill=black, font=config.font24b)

    # --- Left Column ---
    left_x = LEFT_MARGIN
    y_pos = 125 # Starting Y
    spacing = 55 # <<<< CHANGE: Reduced spacing

    # Weather
    draw.text((left_x, y_pos), "Weather:", fill=black, font=config.font16b)
    max_wx_len = 25
    draw.text((left_x + 5, y_pos + 20), descript[:max_wx_len], fill=black, font=config.font16)
    if len(descript) > max_wx_len:
         draw.text((left_x + 5, y_pos + 40), descript[max_wx_len:max_wx_len*2], fill=black, font=config.font16)
    y_pos += spacing # <<<< CHANGE: Use reduced spacing

    # Cloud Cover
    draw.text((left_x, y_pos), "Clouds:", fill=black, font=config.font16b)
    if cctype_lst:
         for i in range(min(2, len(cctype_lst))):
             cctype = cctype_lst[i]
             ccheight = ccheight_lst[i]
             height_str = str(ccheight) if str(ccheight).isdigit() else "N/A"
             draw.text((left_x + 5, y_pos + 20 + i * 20), f"{cctype} {height_str}{dis_unit}", fill=black, font=config.font16)
    else:
         draw.text((left_x + 5, y_pos + 20), "Clear", fill=black, font=config.font16)
    y_pos += spacing # <<<< CHANGE: Use reduced spacing

    # Visibility
    draw.text((left_x, y_pos), "Visibility:", fill=black, font=config.font16b)
    draw.text((left_x + 5, y_pos + 20), f"{vis}{vis_unit}", fill=black, font=config.font16)
    # No y_pos change needed after last item

    # --- Right Column ---
    right_x = SCREEN_WIDTH - 100
    y_pos = 125 # Reset Y
    # Temperature
    draw.text((right_x, y_pos), "Temp:", fill=black, font=config.font16b)
    draw.text((right_x + 5, y_pos + 20), f"{tempf}{temp_unit}", fill=black, font=config.font16)

    # --- Center Visualization ---
    centerX = SCREEN_WIDTH // 2
    centerY = VISUALIZATION_Y # Base Y stays same, offsets will change

    # Define runway geometry BEFORE arrow calculation needs it
    runway_base_y = centerY + 35
    runway_width_near = 85 # Using the widened value from last step
    runway_width_far = 50
    runway_length = 60

    # Draw Wind Arrow (if wind speed > 0)
    if wind_speed > 0:
        runway_heading = runway_number * 10
        relative_angle_deg = wind_direction - runway_heading
        while relative_angle_deg > 180: relative_angle_deg -= 360
        while relative_angle_deg <= -180: relative_angle_deg += 360

        angle_rad = math.radians(relative_angle_deg)
        cos_a = math.cos(angle_rad); sin_a = math.sin(angle_rad)

        # --- Arrow Perspective Calculation ---
        # Base arrow parameters
        arrow_length = 35       # Total length remains same
        arrow_head_length = 18
        shaft_len = arrow_length - arrow_head_length

        # Define the width where head attaches
        arrow_shaft_width_near = 14 # Let's make it slightly wider for visibility

        # Calculate the runway's taper ratio
        if runway_width_near != 0: # Avoid division by zero
             runway_taper_ratio = runway_width_far / runway_width_near
        else:
             runway_taper_ratio = 1 # Default to no taper if runway width is zero

        # Calculate the arrow's far width based on the runway taper
        arrow_shaft_width_far = arrow_shaft_width_near * runway_taper_ratio

        # Calculate half-widths for drawing points
        near_half_w = arrow_shaft_width_near / 2
        far_half_w = arrow_shaft_width_far / 2
        # ----------------------------------

        # Arrow head width remains constant for now
        arrow_head_width = 25

        # Use the Y offset determined previously to position arrow correctly
        arrow_base_y_offset = -25 # From previous adjustment
        arrow_center_x = centerX
        arrow_center_y = centerY + arrow_base_y_offset

        # Recalculate points relative to arrow center using NEW far/near widths
        shaft_half_l = shaft_len / 2

        # Define corners relative to the arrow's own center *before* rotation
        p1 = (-far_half_w, -shaft_half_l)  # Tail left (uses calculated far width)
        p2 = ( far_half_w, -shaft_half_l)  # Tail right (uses calculated far width)
        p3 = ( near_half_w, shaft_half_l)  # Head base right (uses defined near width)
        p4 = (-near_half_w, shaft_half_l)  # Head base left (uses defined near width)

        # Rotate function
        def rotate(x, y):
            new_x = x * cos_a - y * sin_a; new_y = x * sin_a + y * cos_a
            return int(arrow_center_x + new_x), int(arrow_center_y + new_y)

        # Rotate shaft points
        rp1=rotate(p1[0],p1[1]); rp2=rotate(p2[0],p2[1]); rp3=rotate(p3[0],p3[1]); rp4=rotate(p4[0],p4[1])
        # Draw trapezoid shaft (dark gray)
        draw.polygon([rp1,rp2,rp3,rp4], fill=dark_gray)

        # Head points relative to arrow's center before rotation
        head_base_y = shaft_half_l
        head_tip_y = head_base_y + arrow_head_length
        head_half_w = arrow_head_width / 2 # Head width not tapered for now
        hp1 = (0, head_tip_y)             # Tip
        hp2 = (-head_half_w, head_base_y) # Base corner 1
        hp3 = ( head_half_w, head_base_y) # Base corner 2

        # Rotate head points
        rhp1=rotate(hp1[0],hp1[1]); rhp2=rotate(hp2[0],hp2[1]); rhp3=rotate(hp3[0],hp3[1])
        # Draw triangle head (dark gray)
        draw.polygon([rhp1, rhp2, rhp3], fill=dark_gray)

    # Draw Runway (position adjusted slightly if needed relative to arrow)
    runway_base_y = centerY + 35 # Shift runway down slightly more to accommodate arrow
    runway_width_near = 85; runway_width_far = 50; runway_length = 55
    rw_p1 = (centerX - runway_width_near // 2, runway_base_y + runway_length // 2)
    rw_p2 = (centerX - runway_width_far // 2,  runway_base_y - runway_length // 2)
    rw_p3 = (centerX + runway_width_far // 2,  runway_base_y - runway_length // 2)
    rw_p4 = (centerX + runway_width_near // 2, runway_base_y + runway_length // 2)
    draw.polygon([rw_p1, rw_p2, rw_p3, rw_p4], fill=black)
    # Dashed centerline
    dash_length = 6; gap_length = 4; y_start = runway_base_y - runway_length // 2 + gap_length; y_end = runway_base_y + runway_length // 2 - gap_length
    current_y = y_start
    while current_y < y_start + 16: #only do two dashes
        draw.line((centerX, current_y, centerX, min(current_y + dash_length, y_end)), fill=white, width=2)
        current_y += dash_length + gap_length

    # CHANGE: Larger runway number font
    runway_text = str(runway_number).zfill(2)
    rn_font = config.font36b # Use the larger bold font
    try: rn_bbox = draw.textbbox((0,0), runway_text, font=rn_font); rn_w = rn_bbox[2] - rn_bbox[0]; rn_h = rn_bbox[3] - rn_bbox[1]
    except AttributeError: rn_w, rn_h = draw.textsize(runway_text, font=rn_font)


# Calculate original position
    rn_x_orig = centerX - rn_w // 2
    rn_y_orig = runway_base_y + runway_length // 2 - rn_h - 6

# Apply adjustments: +2 to x, -5 to y
    rn_x_adjusted = rn_x_orig 
    rn_y_adjusted = rn_y_orig - 13

# Draw using adjusted coordinates
    draw.text((rn_x_adjusted, rn_y_adjusted), runway_text, fill=white, font=rn_font)

    # Runway threshold markings (kept from previous fix)
    marker_y1 = runway_base_y + runway_length // 2 - 5
    marker_y2 = runway_base_y + runway_length // 2
    for x_offset in [-25, -18, -11, -4, 4, 11, 18, 25]:
        draw.line((centerX + x_offset, marker_y1, centerX + x_offset, marker_y2), fill=white, width=1)

    # --- Footer ---
    update_text = last_update()
    try: up_bbox = draw.textbbox((0,0), update_text, font=config.font16); up_w = up_bbox[2] - up_bbox[0]; up_h = up_bbox[3] - up_bbox[1]
    except AttributeError: up_w, up_h = draw.textsize(update_text, font=config.font16)
    draw.text((LEFT_MARGIN, SCREEN_HEIGHT - up_h - 5), update_text, fill=black, font=config.font16)

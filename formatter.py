import ast
import html

def format_status(output_str):
    try:
        data = ast.literal_eval(output_str)
    except (ValueError, SyntaxError) as e:
        # Escape the error message as it might contain < > from the exception
        return f"Error parsing output: {html.escape(str(e))}"

    # Extract data and escape strings
    name = html.escape(str(data.get('name', 'Unknown')))
    model_type = html.escape(str(data.get('type', 'Unknown')))
    
    # Main Filter (A3 / FY2180) - fltsts1 / flttotal1
    fltsts1 = data.get('fltsts1', 0)
    flttotal1 = data.get('flttotal1', 1) # Avoid div by zero
    main_pct = (fltsts1 / flttotal1) * 100 if flttotal1 else 0
    
    # Pre-Filter - fltsts0 / flttotal0
    fltsts0 = data.get('fltsts0', 0)
    flttotal0 = data.get('flttotal0', 1)
    pre_pct = (fltsts0 / flttotal0) * 100 if flttotal0 else 0
    
    # Metrics
    pm25 = data.get('pm25', 0)
    iaql = data.get('iaql', 0)
    runtime = data.get('Runtime', 0)
    
    # Interpretations
    # PM2.5 Interpretation (Standard AQI approximation for PM2.5 ug/m3)
    if pm25 <= 12:
        pm25_desc = "Excellent air quality"
    elif pm25 <= 35:
        pm25_desc = "Good air quality"
    elif pm25 <= 55:
        pm25_desc = "Moderate air quality"
    else:
        pm25_desc = "Poor air quality"
        
    # IAI Interpretation
    # 1-3 Good, 4-6 Fair, 7-9 Poor, 10-12 Very Poor (Rough guess based on Philips scale)
    if iaql <= 3:
        iaql_desc = "Very low/Good"
    elif iaql <= 6:
        iaql_desc = "Fair"
    elif iaql <= 9:
        iaql_desc = "Poor"
    else:
        iaql_desc = "Very Poor"

    # Main Filter Status Text
    if main_pct > 90:
        main_status_text = "This suggests the main filter is new or in excellent condition."
    elif main_pct > 50:
        main_status_text = "The main filter is in good condition with plenty of life remaining."
    elif main_pct > 10:
        main_status_text = "The main filter is nearing the end of its life but is still effective."
    else:
        main_status_text = "The main filter needs replacement soon."

    # Overall Condition Text (based on PM2.5 and errors)
    err = data.get('err', 0)
    if err == 0 and pm25 <= 35:
        overall_condition = "excellent condition"
    elif err == 0:
        overall_condition = "good working order"
    else:
        overall_condition = f"warning state (Error Code: {err})"
    
    # Escape overall_condition just in case
    overall_condition = html.escape(overall_condition)

    # Message Construction (Using HTML for Telegram compatibility)
    message = f"""Based on the output from <code>aioairctrl</code>, your Philips Air Purifier (<b>{model_type}</b>) is currently in {overall_condition}. Here is the breakdown of your filter lifespan and status:

<b>1. Main Filter Status (HEPA & Active Carbon)</b>
The main filter is tracked by the <code>fltsts1</code> and <code>flttotal1</code> values.
• <b>Remaining Life:</b> <b>{fltsts1:,} hours</b> (<code>fltsts1</code>)
• <b>Total Capacity:</b> <b>{flttotal1:,} hours</b> (<code>flttotal1</code>)
• <b>Status:</b> <b>{main_pct:.0f}%</b>
<i>{main_status_text}</i>

<b>2. Pre-Filter Status (Cleaning Cycle)</b>
The pre-filter (the mesh that catches hair and large dust) is tracked by <code>fltsts0</code> and <code>flttotal0</code>. Unlike the main filter, this one just needs cleaning, not replacing.
• <b>Hours until next cleaning:</b> <b>{fltsts0:,} hours</b> (<code>fltsts0</code>)
• <b>Cleaning interval:</b> <b>{flttotal0:,} hours</b> (<code>flttotal0</code>)
• <b>Status:</b> <b>~{pre_pct:.0f}% remaining</b>
<i>You have about <b>{fltsts0:,} hours</b> of use left (roughly {fltsts0 // 24} days if run 24/7) before the device will prompt you to clean the pre-filter (usually error code <b>F0</b>).</i>

<b>Summary</b>
• <b>Main Filter (A3):</b> {fltsts1:,} / {flttotal1:,} ({main_pct:.0f}%)
• <b>Pre-Filter:</b> {fltsts0:,} / {flttotal0:,} ({pre_pct:.0f}%)

<b>Other Notable Metrics:</b>
• <b>PM2.5:</b> <code>{pm25}</code> ({pm25_desc}).
• <b>IAI (Allergen Index):</b> <code>{iaql}</code> ({iaql_desc}).
• <b>Name:</b> <code>{name}</code> (The location name set for this device).
• <b>Runtime:</b> <code>{runtime:,}</code> (Total system ticks/runtime).
"""
    return message

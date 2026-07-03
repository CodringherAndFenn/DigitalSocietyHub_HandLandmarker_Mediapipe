STRINGS: dict[str, str] = {
    # App
    "app_title":       "Hand Rehab Tracker",
    "window_title":    "Hand Rehab Tracker",
    "error_no_webcam": "Error: cannot open webcam.",
    "error_no_frame":  "Failed to grab frame.",

    # Base exercise defaults
    "base_name":         "Exercise",
    "base_instructions": "Follow the on-screen prompt.",
    "no_hand":           "No hand detected",

    # Injury categories
    "injury_wrist_forearm": "Wrist / Forearm",
    "injury_finger_thumb":  "Finger / Thumb",
    "injury_general":       "General Mobility",
    "injury_post_surgery":  "Post-Surgery (conservative)",

    # Badge
    "badge_good_rep":  "Good rep!",
    "badge_try_again": "Try again",

    # Motivational
    "motiv_10": "Outstanding session!",
    "motiv_8":  "Excellent effort!",
    "motiv_5":  "Match your ghost — you've done it!",
    "motiv_3":  "You're doing well!",
    "motiv_1":  "Great start — keep going!",

    # Window chrome + keycap legend
    "chrome_title":        "HandTracker6000",
    "legend_header":       "HOW TO CONTROL THE APPLICATION",
    "legend_confirm":      "confirm",
    "legend_up":           "go up",
    "legend_down":         "go down",
    "legend_back":         "go back",
    "legend_new_exercise": "new exercise",
    "key_space_label":     "SPACE",

    # Injury menu
    "injury_heading":   "PLEASE CONFIRM YOUR INJURY TYPE/S",
    "injury_menu_hint": "Exercises will be tailored to your condition.",

    # Exercise menu
    "menu_heading": "WHAT EXERCISE WOULD YOU LIKE TO DO?",

    # HUD
    "hud_waiting":      "Waiting for first rep...",
    "hud_correct_of":   "{correct}/{reps} correct",
    "hud_accuracy_pct": "  ({pct}%)",
    "hud_reps_label":   "REPS",
    "hud_pause_hint":   "Press P to pause",
    "btn_end_exercise": "PRESS SPACE TO END THE EXERCISE",

    # Calibration
    "calib_intro_heading":   "GETTING TO KNOW YOUR HAND",
    "calib_intro_body":      "Hold your hand flat and facing the camera. Calibration is simply the app getting used to your hand — hold each pose when asked and the rest happens by itself.",
    "btn_start_calibration": "PRESS SPACE TO START CALIBRATION",
    "calib_skip_hint":       "Press S to skip calibration and use default settings",
    "calib_progress_header": "CALIBRATION  ({n} / {total})",
    "calib_ready_prompt":    "Press SPACE when you are in position",
    "calib_measuring":       "Measuring...",
    "calib_ready_hint":      "Press SPACE when ready   Press S to skip calibration",
    "calib_done":            "Done!",
    "calib_complete":        "Calibration complete!",
    "calib_skipped":         "Calibration skipped — using default settings.",
    "calib_done_body":       "The real exercise will begin next — don't worry, it is the same motions you just practised. Just go through the motions.",
    "btn_start_exercise":    "PRESS SPACE TO START EXERCISE",

    # Pause
    "pause_header":    "PAUSED",
    "pause_body_one":  "Take a rest. You have done {n} rep so far.",
    "pause_body_many": "Take a rest. You have done {n} reps so far.",
    "pause_resume":    "Press P to continue",

    # Report
    "report_title":        "SESSION COMPLETE",
    "report_col_exercise": "Exercise",
    "report_col_reps":     "Reps",
    "report_col_correct":  "Correct",
    "report_col_accuracy": "Accuracy",
    "report_total":         "Total",
    "report_duration":      "Duration: {m}m {s}s",
    "report_saved":         "Saved:  {filename}",
    "report_encouragement": "Well done — every session counts!",

    # Calibration pose titles and instructions
    "pose_open_title":           "Open Hand",
    "pose_open_instruction":     "Hold hand open and flat, fingers relaxed",
    "pose_fist_title":           "Closed Fist",
    "pose_fist_instruction":     "Make as tight a fist as you can",
    "pose_spread_title":         "Finger Spread",
    "pose_spread_instruction":   "Spread fingers as wide apart as possible",
    "pose_pinch_title":          "Pinch",
    "pose_pinch_instruction":    "Pinch thumb tip to index fingertip",
    "pose_claw_title":           "Claw Hand",
    "pose_claw_instruction":     "Bend only the middle joints (PIP/DIP) while keeping knuckles (MCP) raised",
    "pose_tabletop_title":       "Tabletop Position",
    "pose_tabletop_instruction": "Bend knuckles to ~90° while keeping fingers straight — like fingers flat on a table",

    # Exercises
    "exercise_fist_name":         "Fist Open/Close",
    "exercise_fist_instructions": "Start with a closed fist. Open your hand fully, then close again.",
    "exercise_fist_feedback":     "Open your hand fully",

    "exercise_spread_name":         "Finger Spread",
    "exercise_spread_instructions": "Hold hand open. Spread fingers as wide apart as possible, then bring together.",
    "exercise_spread_feedback":     "Spread fingers wide",

    "exercise_pinch_name":         "Pinch",
    "exercise_pinch_instructions": "Start with open hand. Pinch thumb to index fingertip, then release.",
    "exercise_pinch_feedback":     "Bring thumb to index tip",

    "exercise_thumb_opp_name":         "Thumb Opposition",
    "exercise_thumb_opp_instructions": "Touch thumb to each fingertip in order: index → middle → ring → pinky. That completes one rep.",
    "exercise_thumb_opp_feedback":     "Touch thumb to {finger} finger",

    "exercise_finger_ext_name":         "Finger Extension",
    "exercise_finger_ext_instructions": "Start with a closed fist. Extend each finger one at a time: index → middle → ring → pinky. That completes one rep.",
    "exercise_finger_ext_feedback":     "Extend {finger} finger",

    "exercise_claw_name":         "Claw Hand",
    "exercise_claw_instructions": "Start with open hand. Bend only the middle joints (PIP/DIP) while keeping knuckles (MCP) raised — like a claw. Then straighten.",
    "exercise_claw_feedback":     "Curl only middle joints — keep knuckles up",

    "exercise_ok_name":         "OK Sign",
    "exercise_ok_instructions": "Start with open hand. Pinch thumb to index, keep other fingers straight. Then release.",
    "exercise_ok_feedback":     "Pinch thumb to index, keep other fingers straight",

    "exercise_tabletop_name":         "Tabletop Position",
    "exercise_tabletop_instructions": "Start with open hand. Bend knuckles (MCP) to ~90 degrees while keeping fingers straight — like resting fingers flat on a table. Then straighten.",
    "exercise_tabletop_feedback":     "Keep fingers straight while bending knuckles to 90 degrees",

    # Finger names used in sub-cycling feedback
    "finger_index":  "index",
    "finger_middle": "middle",
    "finger_ring":   "ring",
    "finger_pinky":  "pinky",
}

STRINGS: dict[str, str] = {
    # App
    "app_title":       "Hand Revalidatie Tracker",
    "window_title":    "Hand Revalidatie Tracker",
    "error_no_webcam": "Fout: kan webcam niet openen.",
    "error_no_frame":  "Frame ophalen mislukt.",

    # Base exercise defaults
    "base_name":         "Oefening",
    "base_instructions": "Volg de aanwijzingen op het scherm.",
    "no_hand":           "Geen hand gedetecteerd",

    # Injury categories
    "injury_wrist_forearm": "Pols / Onderarm",
    "injury_finger_thumb":  "Vinger / Duim",
    "injury_general":       "Algemene Mobiliteit",
    "injury_post_surgery":  "Na Operatie (conservatief)",

    # Badge
    "badge_good_rep":  "Goede herhaling!",
    "badge_try_again": "Probeer opnieuw",

    # Motivational
    "motiv_10": "Uitstekende sessie!",
    "motiv_8":  "Geweldige inspanning!",
    "motiv_5":  "Evenaart u uw schaduw — u heeft het gedaan!",
    "motiv_3":  "U doet het goed!",
    "motiv_1":  "Goed begin — ga zo door!",

    # Injury menu
    "injury_menu_header":   "HAND REVALIDATIE TRACKER",
    "injury_menu_subtitle": "Selecteer uw blessuretype:",
    "injury_menu_hint":     "De oefeningen worden afgestemd op uw aandoening.",
    "injury_menu_nav":      "Gebruik ↑↓ pijlen of toetsen 1–4 om te kiezen",
    "injury_menu_confirm":  "Druk op ENTER om te bevestigen",
    "injury_menu_quit":     "Druk op Q om af te sluiten",

    # Exercise menu
    "menu_header":   "HAND REVALIDATIE TRACKER",
    "menu_subtitle": "Selecteer Oefening:",
    "menu_nav":      "Gebruik ↑↓ pijlen of toetsen 1–8 om te kiezen",
    "menu_start":    "Druk op ENTER om te starten",
    "menu_quit":     "Druk op Q om af te sluiten",

    # HUD
    "hud_waiting":      "Wacht op eerste herhaling...",
    "hud_correct_of":   "{correct}/{reps} correct",
    "hud_accuracy_pct": "  ({pct}%)",
    "hud_reps_label":   "REPS",
    "hud_hints":        "Druk op SPATIE om te stoppen   Druk op Q om af te sluiten",

    # Calibration
    "calib_header":          "HAND KALIBRATIE",
    "calib_intro":           "We meten uw persoonlijk bewegingsbereik in {n} houdingen. Houd elke houding aan als gevraagd — druk op S om over te slaan en de standaardinstellingen te gebruiken.",
    "calib_begin":           "Druk op ENTER om te beginnen",
    "calib_skip_hint":       "Druk op S om kalibratie over te slaan en standaardinstellingen te gebruiken",
    "calib_progress_header": "KALIBRATIE  ({n} / {total})",
    "calib_ready_prompt":    "Druk op SPATIE als u in positie bent",
    "calib_measuring":       "Meten...",
    "calib_ready_hint":      "Druk op SPATIE als u klaar bent   Druk op S om over te slaan",
    "calib_done":            "Klaar!",
    "calib_complete":        "Kalibratie voltooid!",
    "calib_skipped":         "Kalibratie overgeslagen — standaardinstellingen worden gebruikt.",
    "calib_continue":        "Druk op ENTER om de oefening te beginnen",

    # Pause
    "pause_header":    "GEPAUZEERD",
    "pause_body_one":  "Neem een pauze. U heeft tot nu toe {n} herhaling gedaan.",
    "pause_body_many": "Neem een pauze. U heeft tot nu toe {n} herhalingen gedaan.",
    "pause_resume":    "Druk op P om door te gaan",

    # Report
    "report_title":        "SESSIE VOLTOOID",
    "report_col_exercise": "Oefening",
    "report_col_reps":     "Herh.",
    "report_col_correct":  "Correct",
    "report_col_accuracy": "Nauwk.",
    "report_total":        "Totaal",
    "report_duration":     "Duur: {m}m {s}s",
    "report_saved":        "Opgeslagen:  {filename}",
    "report_hints":        "Druk op ENTER voor nieuwe sessie   Druk op Q om af te sluiten",

    # Calibration pose titles and instructions
    "pose_open_title":           "Open Hand",
    "pose_open_instruction":     "Houd uw hand open en plat, vingers ontspannen",
    "pose_fist_title":           "Gesloten Vuist",
    "pose_fist_instruction":     "Maak zo'n strakke vuist als u kunt",
    "pose_spread_title":         "Vingers Spreiden",
    "pose_spread_instruction":   "Spreid uw vingers zo ver mogelijk uit elkaar",
    "pose_pinch_title":          "Knijpgreep",
    "pose_pinch_instruction":    "Breng uw duimtop naar uw wijsvingertop",
    "pose_claw_title":           "Klauwhand",
    "pose_claw_instruction":     "Buig alleen de middelste gewrichten (PIP/DIP) terwijl de knokkel (MCP) omhoog blijft",
    "pose_tabletop_title":       "Tafelblad Positie",
    "pose_tabletop_instruction": "Buig knokkel tot ~90° terwijl vingers gestrekt blijven — als vingers plat op een tafel",

    # Exercises
    "exercise_fist_name":         "Vuist Open/Sluit",
    "exercise_fist_instructions": "Begin met een gesloten vuist. Open uw hand volledig, sluit dan weer.",
    "exercise_fist_feedback":     "Open uw hand volledig",

    "exercise_spread_name":         "Vingers Spreiden",
    "exercise_spread_instructions": "Houd uw hand open. Spreid uw vingers zo ver mogelijk, breng ze dan samen.",
    "exercise_spread_feedback":     "Spreid uw vingers breed",

    "exercise_pinch_name":         "Knijpgreep",
    "exercise_pinch_instructions": "Begin met open hand. Breng duim naar wijsvingertop, laat dan los.",
    "exercise_pinch_feedback":     "Breng duim naar wijsvingertop",

    "exercise_thumb_opp_name":         "Duim Oppositie",
    "exercise_thumb_opp_instructions": "Raak met uw duim elke vingertop aan in volgorde: wijsvinger → middelvinger → ringvinger → pink. Dat telt als één herhaling.",
    "exercise_thumb_opp_feedback":     "Raak duim aan {finger}",

    "exercise_finger_ext_name":         "Vinger Strekking",
    "exercise_finger_ext_instructions": "Begin met een gesloten vuist. Strek elke vinger één voor één: wijsvinger → middelvinger → ringvinger → pink. Dat telt als één herhaling.",
    "exercise_finger_ext_feedback":     "Strek {finger}",

    "exercise_claw_name":         "Klauwhand",
    "exercise_claw_instructions": "Begin met open hand. Buig alleen de middelste gewrichten (PIP/DIP) terwijl de knokkel (MCP) omhoog blijft — als een klauw. Strek dan.",
    "exercise_claw_feedback":     "Buig alleen middelste gewrichten — houd knokkel omhoog",

    "exercise_ok_name":         "OK-teken",
    "exercise_ok_instructions": "Begin met open hand. Knijp duim naar wijsvinger, houd andere vingers gestrekt. Laat dan los.",
    "exercise_ok_feedback":     "Knijp duim naar wijsvinger, houd andere vingers gestrekt",

    "exercise_tabletop_name":         "Tafelblad Positie",
    "exercise_tabletop_instructions": "Begin met open hand. Buig knokkel (MCP) tot ~90 graden terwijl vingers gestrekt blijven — als vingers plat op een tafel. Strek dan.",
    "exercise_tabletop_feedback":     "Houd vingers gestrekt terwijl u knokkel naar 90 graden buigt",

    # Finger names used in sub-cycling feedback
    "finger_index":  "wijsvinger",
    "finger_middle": "middelvinger",
    "finger_ring":   "ringvinger",
    "finger_pinky":  "pink",
}

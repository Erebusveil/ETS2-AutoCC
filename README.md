# ETS2 / ATS AutoCC

Automatic cruise control that adjusts to the current speed limit — just like Tesla's speed limit recognition. Built for Euro Truck Simulator 2 and American Truck Simulator.

---

## What does it do?

Once you enable cruise control, AutoCC automatically adjusts your set speed to match the speed limit of the road you're on. If the limit drops, the script reacts immediately. If the limit increases, it waits briefly to confirm the new limit is stable.

A modern dashboard displays your live speed, the current limit, and your cruise control status.

---

## Requirements

- Euro Truck Simulator 2 or American Truck Simulator (Steam)
- Python 3.10 or higher — download at python.org
- The included scs-telemetry.dll

---

## Installation

### Step 1 — Install the SDK Plugin

Open the included folder release_v_1_12_1 and navigate to Win64 → plugins.

Copy the plugins folder to your game directory:

**ETS2:**
```
C:\Program Files (x86)\Steam\steamapps\common\Euro Truck Simulator 2\bin\win_x64\
```

**ATS:**
```
C:\Program Files (x86)\Steam\steamapps\common\American Truck Simulator\bin\win_x64\
```

Already have a plugins folder? Copy only the contents into it, not the folder itself.

### Step 2 — Install Python packages

Open PowerShell and run:

```
py -m pip install PyQt6 pynput truck-telemetry
```

### Step 3 — Start the game

Launch ETS2 or ATS via Steam. On startup you'll see a prompt about advanced SDK features — click OK. This is normal and required for the tool.

### Step 4 — Start AutoCC

Run in PowerShell:

```
py ETS2_AutoCC.py
```

The dashboard will open. Start driving and enable cruise control — the rest is automatic.

---

## Dashboard

- Blue arc — current speed
- Green arc — speed limit
- Purple arc — set CC speed
- Red color — you are exceeding the speed limit
- STOP / START button — temporarily disable AutoCC without closing the window

---

## Default cruise control keys

| Action | Key |
|---|---|
| Enable CC | B (controller, hold) |
| Resume CC | A (controller, hold) |
| Speed up | Numpad + |
| Speed down | Numpad - |

---

## Known limitations

- Only works with cruise control speeds that are a multiple of 5 km/h
- On roads without a detected speed limit, AutoCC does nothing
- SmartScreen may show a warning for the .exe version — click More info and then Run anyway

---

## Built with

- Python
- PyQt6
- pynput
- truck-telemetry
- scs-sdk-plugin by RenCloud

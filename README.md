main*# Lighting Submittal Package Builder

Professional lighting fixture submittal tool.

## Features
- Automatic spec sheet search from part numbers
- Manual editing table
- Auto manufacturer & fixture type detection
- Compliance matrix (DLC, ENERGY STAR, etc.)
- Divider pages (Building/Unit)
- Branded PDF with Calibri font

## Setup Fonts (Important)
1. Create a folder called `fonts` in the root
2. Place `calibri.ttf` and `calibri-bold.ttf` inside it
3. Commit the folder

## Run Locally
```bash
pip install -r requirements.txt
streamlit run lighting_submittal.py**

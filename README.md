# Umamusume-Compatibility-Calculator
Calculates highest scoring affinities based on top 3 parent combinations.

## Setup
- Set up venv: `python -m venv ./venv`
- Activate venv: `./venv/Scripts/activate`
- Install requirements: `pip install -r requirements.txt`

## Usage
- Run `owned-characters.py` to generate owned characters json.
  - Open http://127.0.0.1:5000 in your browser. After selecting the characters you owned, scroll down and click "Save Selection".
    This will save the owned characters to `data/ownedCharacters.json`.
- Run `brute-force-calculator.py` to calculate affinities.
  - If `data/ownedCharacters.json` doesn't exist, it will use `data/availChars.json` instead. This will take longer to calculate affinity scores.

## Credits
- [Gametora](https://gametora.com/umamusume) for providing the character and relationship data.

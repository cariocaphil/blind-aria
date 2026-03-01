"""
Configuration constants for Blind Aria Trainer.
"""

from pathlib import Path

# =========================
# Paths and Files
# =========================
DATA_PATH = Path(__file__).parent / "data" / "works.json"

# =========================
# App Config
# =========================
MIN_VERSIONS_REQUIRED = 3

# =========================
# Questionnaire Options
# =========================
VOICE_PRODUCTION_OPTIONS = [
    "Clear diction",
    "Legato line",
    "Even vibrato",
    "Breath-driven phrasing",
    "Secure upper register",
    "Warm timbre",
    "Bright / metallic timbre",
    "Dark / covered timbre",
    "Heavy production",
    "Flexible / agile",
    "Nasal resonance audible",
    'Croaky / "froggish" quality',
]

LANGUAGE_OPTIONS = [
    "Text clearly understandable",
    "Consonants very present",
    "Vowels well shaped",
    "Non-native accent perceptible",
]

STYLE_OPTIONS = [
    "Bel canto oriented",
    "Verismo oriented",
    "Historically older style",
    "Modern / international style",
    "Dramatic / theatrical",
    "Intimate / inward",
]

MEANING_INTENT_OPTIONS = [
    "Musical intention feels clear",
    "Phrasing feels purposeful",
    "Dynamic shaping feels deliberate",
    "Rubato feels meaningful",
    "Text delivery feels intentional",
    "I sense a clear point of view",
]

SENSE_MAKING_OPTIONS = [
    "Dramatic situation feels clear",
    "Emotional arc is understandable",
    "The aria feels embedded in a story",
    "I understand why this aria exists",
]

TRANSMISSION_OPTIONS = [
    "Strongly reaches me",
    "Reaches me at moments",
    "Neutral",
    "Emotionally distant",
    "Feels mannered / performative",
]

ANCHOR_OPTIONS = ["Yes", "Unsure", "No"]
IMPRESSION_OPTIONS = ["Loved it", "Convincing", "Neutral", "Distracting", "Not for me"]

"""
NewsieNest - AI News Analyzer for everyone (kids, students, adults)

Features
- Live news from BBC, The Hindu, Al Jazeera, Guardian, NPR, NDTV, Indian Express, TOI, HT
- Rolling live ticker, quick topic pills, daily mission, WhatsApp sharing
- Summary, sentiment, credibility hint, translation to Indian languages
- Story Studio: 2-min briefing, cartoon, explain simply, quiz, hard words
- Newsie chatbot (cartoon / real life / game) + dictionary
- Login (PBKDF2), forgot password, guest mode, XP + streaks
- Privacy page, ratings, owner dashboard (visits, feedback), backups, data deletion

Secrets: DATABASE_URL (Neon, permanent data), GEMINI_API_KEY, GROQ_API_KEY (optional), ADMIN_EMAILS, APP_NAME,
CONTACT_EMAIL, GITHUB_URL, APP_URL, NEWSAPI_KEY
Optional (password-reset emails): SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
"""
import os
import re
import io
import base64
import json
import time
import html
import random
import socket
import sqlite3
import hashlib
import hmac
import secrets
import ipaddress
import datetime as dt
from contextlib import closing
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse, parse_qs
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from pathlib import Path

# Optional helper modules. They are not used below, so the app still runs if these files do not exist.
try:
    import boost  # noqa: F401
except Exception:
    boost = None
try:
    import mascot_bot  # noqa: F401
except Exception:
    mascot_bot = None


def cfg(name, default=""):
    """Read a setting from Streamlit secrets first, then environment variables."""
    try:
        v = st.secrets.get(name)
    except Exception:
        v = None
    return str(v) if v not in (None, "") else os.getenv(name, default)


# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
APP_VERSION = "v8-quota-safe"
APP_NAME = cfg("APP_NAME", "NewsieNest")  # change the name any time in Secrets: APP_NAME = "..."
DB_PATH = os.getenv("NEWSVERSE_DB", "data/newsverse.db")
UA = {"User-Agent": "Mozilla/5.0 (NewsieNest learning app)"}
esc = html.escape
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0 Safari/537.36",
              "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5"}
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
MAX_STORIES = 50

LANGS = {
    "English": ("en", "en-IN"), "Hindi (हिन्दी)": ("hi", "hi-IN"),
    "Kannada (ಕನ್ನಡ)": ("kn", "kn-IN"), "Tamil (தமிழ்)": ("ta", "ta-IN"),
    "Telugu (తెలుగు)": ("te", "te-IN"), "Malayalam (മലയാളം)": ("ml", "ml-IN"),
    "Marathi (मराठी)": ("mr", "mr-IN"), "Bengali (বাংলা)": ("bn", "bn-IN"),
    "Gujarati (ગુજરાતી)": ("gu", "gu-IN"), "Punjabi (ਪੰਜਾਬੀ)": ("pa", "pa-IN"),
    "Urdu (اردو)": ("ur", "ur-IN"), "Odia (ଓଡ଼ିଆ)": ("or", "or-IN"),
    "Assamese (অসমীয়া)": ("as", "as-IN"), "Nepali (नेपाली)": ("ne", "ne-NP"),
}
CATEGORIES = {
    "Top stories": None, "India": "NATION", "Karnataka": None, "World": "WORLD", "Business": "BUSINESS",
    "Technology": "TECHNOLOGY", "Science": "SCIENCE", "Health": "HEALTH",
    "Sports": "SPORTS", "Entertainment": "ENTERTAINMENT",
}
KIDS_CATEGORIES = ["Top stories", "Science", "Technology", "Sports", "Entertainment", "World", "Health"]
CAT_COLOR = {"Top stories": "#FFB020", "India": "#FF9F43", "Karnataka": "#FF6B6B", "World": "#4DABF7",
             "Business": "#3DDC97", "Technology": "#8B6CFF", "Science": "#22D3EE", "Health": "#F783AC",
             "Sports": "#FF8787", "Entertainment": "#E599F7"}

"""Design tokens for the video, derived from the worksheet itself.

Every color below was extracted from the vector data of the MCP guided
notes PDF (assets/guided_notes.pdf), so on-screen additions belong to the
same world as the printed page. Fonts are the document's own faces — both
are Google Fonts, freely available.
"""

# --- printed page (extracted from PDF vector fills/strokes) ---------------
NAVY = "#384652"          # dominant ink: headings, rules, cube outlines
PAPER = "#F9F7F0"         # page/panel background cream
ORANGE = "#FAA438"        # accent: section rules, SKILL pill, lesson label
CUBE_TOP = "#F1EEEA"      # isometric cube faces, light → dark
CUBE_SIDE = "#E6DED1"
CUBE_FRONT = "#CFC4B5"
CUBE_SHADE = "#B8AFA2"

# --- typography (embedded in the PDF; both on Google Fonts) ---------------
FONT_HEADING = "Barlow Semi Condensed"   # bold/semibold: headings, labels
FONT_BODY = "Lora"                       # serif: problem text, definitions

# --- the teacher's ink (ours, not the page's) -----------------------------
# Handwriting must read as a distinct human voice laid over the printed
# world: a classic pen blue, warm enough to sit with the cream paper.
# Spike default — subject to an A/B against navy before picture lock.
INK = "#2D5FA8"
INK_WIDTH_PT = 1.9        # nominal stroke width at page scale (points)

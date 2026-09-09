"""Deterministic spelling: fix what is certainly wrong, touch nothing else.

The rule here is conservatism. A spellchecker that guesses will "correct" a
tool name, a model tag or a filename into something that no longer works, and
because it runs on the delivery the operator sees the damage last. So this
pass only changes a word when it is on a list of known misspellings, and it
refuses to look inside anything that is code.

If `pyspellchecker` is installed the coverage widens to a real dictionary, but
the protection rules below still apply and unknown words are only ever
REPORTED, never rewritten -- a word this pass does not recognise is far more
likely to be a proper noun than a mistake.
"""

from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass, field

# Regions that are never touched: fenced code, inline code, urls, paths,
# anything with an underscore or a digit in it, model tags, and CAPS.
_PROTECT = re.compile(
    r"```.*?```"                      # fenced code
    r"|`[^`]*`"                       # inline code
    r"|<[^>]+>"                       # xml tags the chain uses
    r"|https?://\S+"                  # urls
    r"|[\w.-]+/[\w./-]+"              # paths
    r"|\b[\w-]+\.(?:py|md|json|jsonl|txt|toml|yml|yaml|lock)\b"
    r"|\b\w*[_\d]\w*\b"               # identifiers, versions, model tags
    r"|\b[A-Z]{2,}\b",                # acronyms
    re.DOTALL)

_WORD = re.compile(r"\b[a-zA-Z]+\b")

# Common misspellings. Kept deliberately short and certain: every entry is a
# word that is never correct in English, so replacing it cannot lose meaning.
CORRECTIONS: dict[str, str] = {
    "abscence": "absence", "accomodate": "accommodate", "acheive": "achieve",
    "acknowlege": "acknowledge", "aquire": "acquire", "adress": "address",
    "arguement": "argument", "assual": "usual", "auxillary": "auxiliary",
    "baisc": "basic", "becuase": "because", "begining": "beginning",
    "beleive": "believe", "buisness": "business", "calender": "calendar",
    "cancelation": "cancellation", "catagory": "category", "cieling": "ceiling",
    "collegue": "colleague", "comitted": "committed", "commited": "committed",
    "concious": "conscious", "consistant": "consistent", "definately": "definitely",
    "dependant": "dependent", "desicion": "decision", "diferent": "different",
    "dissapear": "disappear", "embarass": "embarrass", "enviroment": "environment",
    "existance": "existence", "experiance": "experience", "explaination": "explanation",
    "familar": "familiar", "finaly": "finally", "foriegn": "foreign",
    "fourty": "forty", "freind": "friend", "goverment": "government",
    "gaurd": "guard", "garuntee": "guarantee", "happend": "happened",
    "harrass": "harass", "hieght": "height", "immediatly": "immediately",
    "independant": "independent", "inteligent": "intelligent", "interupt": "interrupt",
    "knowlege": "knowledge", "lenght": "length", "liason": "liaison",
    "libary": "library", "maintainance": "maintenance", "maintenence": "maintenance",
    "managment": "management", "mispell": "misspell", "neccessary": "necessary",
    "necesary": "necessary", "noticable": "noticeable", "occured": "occurred",
    "occurence": "occurrence", "ocassion": "occasion", "paralell": "parallel",
    "particulary": "particularly", "perfomance": "performance", "persistant": "persistent",
    "posession": "possession", "prefered": "preferred", "priviledge": "privilege",
    "probaly": "probably", "proccess": "process", "publically": "publicly",
    "recieve": "receive", "recomend": "recommend", "refered": "referred",
    "relevent": "relevant", "reponse": "response", "resistence": "resistance",
    "responsibilty": "responsibility", "seperate": "separate", "sieze": "seize",
    "similiar": "similar", "sucessful": "successful", "succesful": "successful",
    "supress": "suppress", "supercede": "supersede", "temperture": "temperature",
    "tendancy": "tendency", "threshhold": "threshold", "tommorow": "tomorrow",
    "tounge": "tongue", "truely": "truly", "unfortunatly": "unfortunately",
    "untill": "until", "usefull": "useful", "vaccum": "vacuum",
    "wich": "which", "wierd": "weird", "writting": "writing",
    "yeild": "yield", "adn": "and", "teh": "the", "thier": "their",
    "hte": "the", "taht": "that", "waht": "what", "tokne": "token",
    "recieved": "received", "occuring": "occurring", "seperated": "separated",
}


@dataclass
class Result:
    text: str
    fixed: list[tuple[str, str]] = field(default_factory=list)
    suspect: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.fixed)

    def note(self) -> str:
        """One line for the run notes, or "" when there is nothing to say."""
        bits = []
        if self.fixed:
            shown = ", ".join(f"{a}->{b}" for a, b in self.fixed[:4])
            more = f" (+{len(self.fixed) - 4})" if len(self.fixed) > 4 else ""
            bits.append(f"corrected {len(self.fixed)}: {shown}{more}")
        if self.suspect:
            bits.append("unrecognised: " + ", ".join(self.suspect[:4]))
        return "spelling: " + "; ".join(bits) if bits else ""


def _match_case(original: str, replacement: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


_SPELLER: list = [None]


def _dictionary():
    """pyspellchecker if present, else None. Probed without importing."""
    if _SPELLER[0] is None:
        try:
            if importlib.util.find_spec("spellchecker") is None:
                _SPELLER[0] = False
            else:
                from spellchecker import SpellChecker
                _SPELLER[0] = SpellChecker()
        except Exception:
            _SPELLER[0] = False
    return _SPELLER[0] or None


def check(text: str, report_unknown: bool = True) -> Result:
    """Correct known misspellings; report unknown words without touching them."""
    if not (text or "").strip():
        return Result(text or "")

    fixed: list[tuple[str, str]] = []
    suspect: list[str] = []
    speller = _dictionary() if report_unknown else None

    def fix_segment(segment: str) -> str:
        def one(m: re.Match) -> str:
            word = m.group(0)
            low = word.lower()
            if low in CORRECTIONS:
                fixed.append((word, CORRECTIONS[low]))
                return _match_case(word, CORRECTIONS[low])
            if speller is not None and len(low) > 3 and low not in speller:
                # Reported, never rewritten: an unknown word is far more often
                # a name than an error, and a wrong "fix" is worse than a typo.
                if word not in suspect:
                    suspect.append(word)
            return word

        return _WORD.sub(one, segment)

    out: list[str] = []
    last = 0
    for m in _PROTECT.finditer(text):
        out.append(fix_segment(text[last:m.start()]))
        out.append(m.group(0))          # protected region, verbatim
        last = m.end()
    out.append(fix_segment(text[last:]))
    return Result("".join(out), fixed, suspect)

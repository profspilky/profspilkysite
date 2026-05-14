"""Management command — scrape fpsu.org.ua pages and populate MemOrgPage model.

Usage:
    python3 manage.py import_mem_orgs
    python3 manage.py import_mem_orgs --update      # re-scrape existing records
    python3 manage.py import_mem_orgs --dry-run     # print without saving
"""
from __future__ import annotations

import re
import time
import urllib.request
from html.parser import HTMLParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

_BASE_G = "https://www.fpsu.org.ua/sajty-chlenskikh-organizatsij-2/2012-12-10-16-02-20"
_BASE_T = "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok"

_GALUZEVI: list[dict] = [
    {"name": "Професійна спілка працівників авіабудування та машинобудування України",
     "url": f"{_BASE_G}/195-profspilka-aviabudivnikiv-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка авіапрацівників України",
     "url": f"{_BASE_G}/194-profspilka-aviapratsivnikiv-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка працівників автомобільного транспорту та шляхового господарства України",
     "url": f"{_BASE_G}/193-profspilka-pratsivnikiv-avtomobilnogo-transportu-ta-shlyakhovogo-gospodarstva-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка працівників автомобільного та сільськогосподарського машинобудування України",
     "url": f"{_BASE_G}/192-profspilka-pratsivnikiv-avtomobilnogo-ta-silskogospodarskogo-mashinobuduvannya-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка працівників агропромислового комплексу України",
     "url": "https://profapk.org.ua/", "org_type": "sectoral", "external": True},
    {"name": "Всеукраїнська профспілка адвокатів України",
     "url": f"{_BASE_G}/25246-vseukrainska-profspilka-advokativ-ukrainy.html", "org_type": "sectoral"},
    {"name": "Атомпрофспілка — Профспілка працівників атомної енергетики та промисловості України",
     "url": "https://www.atomprofspilka.info/", "org_type": "sectoral", "external": True},
    {"name": "ПРОФБУД — Профспілка працівників будівництва і промисловості будівельних матеріалів України",
     "url": "https://www.profbud.org.ua/", "org_type": "sectoral", "external": True},
    {"name": "Всеукраїнська професійна спілка працівників банківських і фінансових установ",
     "url": f"{_BASE_G}/25247-vseukrainska-profesiina-spilka-pratsivnykiv-bankivskykh-i-finansovykh-ustanov.html", "org_type": "sectoral"},
    {"name": "Всеукраїнська профспілка виробничників, підприємців та трудових мігрантів",
     "url": f"{_BASE_G}/188-vseukrajinska-profspilka-virobnichnikiv-i-pidpriemtsiv-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка працівників вугільної промисловості України",
     "url": "http://www.prupu.org/", "org_type": "sectoral", "external": True},
    {"name": "Профспілка працівників газових господарств України",
     "url": f"{_BASE_G}/186-profspilka-pratsivnikiv-gazovikh-gospodarstv-ukrajini.html", "org_type": "sectoral"},
    {"name": "Професійна спілка працівників геології, геодезії та картографії України",
     "url": f"{_BASE_G}/185-profesijna-spilka-pratsivnikiv-geologiji-geodeziji-ta-kartografiji-ukrajini.html", "org_type": "sectoral"},
    {"name": "Професійна спілка працівників державних установ України",
     "url": "http://ppdu-ua.org/", "org_type": "sectoral", "external": True},
    {"name": "УКРЕЛЕКТРОПРОФСПІЛКА — Профспілка працівників енергетики та електротехнічної промисловості України",
     "url": "http://ukrelectroprofspilka.org.ua", "org_type": "sectoral", "external": True},
    {"name": "Профспілка працівників житлово-комунального господарства, місцевої промисловості та побутового обслуговування України",
     "url": f"{_BASE_G}/182-profspilka-pratsivnikiv-zhitlovo-komunalnogo-gospodarstva-mistsevoji-promislovosti-pobutovogo-obslugovuvannya-naselennya-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка працівників зв'язку України",
     "url": "https://profzviazku.org.ua/", "org_type": "sectoral", "external": True},
    {"name": "Всеукраїнська профспілка працівників інноваційних і малих підприємств",
     "url": f"{_BASE_G}/180-vseukrajinska-profspilka-pratsivnikiv-innovatsijnikh-i-malikh-pidpriemstv.html", "org_type": "sectoral"},
    {"name": "Професійна спілка працівників космічного та загального машинобудування України",
     "url": f"{_BASE_G}/179-profesijna-spilka-pratsivnikiv-kosmichnogo-ta-zagalnogo-mashinobuduvannya-ukrajini.html", "org_type": "sectoral"},
    {"name": "Професійна спілка працівників культури України",
     "url": "https://cultura.fpsu.org.ua/", "org_type": "sectoral", "external": True},
    {"name": "Профспілка працівників лісових галузей України",
     "url": f"{_BASE_G}/177-profspilka-pratsivnikiv-lisovikh-galuzej-ukrajini.html", "org_type": "sectoral"},
    {"name": "Професійна спілка працівників лісового господарства України",
     "url": f"{_BASE_G}/176-profesijna-spilka-pratsivnikiv-lisovogo-gospodarstva-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка машинобудівників та приладобудівників України",
     "url": f"{_BASE_G}/175-profspilka-mashinobudivnikiv-ta-priladobudivnikiv-ukrajini.html", "org_type": "sectoral"},
    {"name": "Професійна спілка працівників машинобудування та металообробки України",
     "url": f"{_BASE_G}/174-profesijna-spilka-pratsivnikiv-mashinobuduvannya-ta-metaloobrobki-ukrajini.html", "org_type": "sectoral"},
    {"name": "ПМГУ — Профспілка металургів і гірників України",
     "url": "http://www.pmguinfo.dp.ua/", "org_type": "sectoral", "external": True},
    {"name": "Професійна спілка працівників молодіжних житлових комплексів та комітетів місцевого самоврядування України",
     "url": f"{_BASE_G}/172-profesijna-spilka-pratsivnikiv-molodizhnikh-zhitlovikh-kompleksiv-ta-komitetiv-mistsevogo-samovryaduvannya-ukrajini.html", "org_type": "sectoral"},
    {"name": "Професійна спілка робітників морського транспорту України",
     "url": f"{_BASE_G}/171-profesijna-spilka-robitnikiv-morskogo-transportu-ukrajini.html", "org_type": "sectoral"},
    {"name": "Укрнафтогазпрофспілка — Профспілка працівників нафтової і газової промисловості України",
     "url": "https://ngpu.org.ua/", "org_type": "sectoral", "external": True},
    {"name": "Профспілка працівників оборонної промисловості України",
     "url": f"{_BASE_G}/169-profspilka-pratsivnikiv-oboronnoji-promislovosti-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка працівників освіти і науки України",
     "url": "https://www.pon.org.ua/", "org_type": "sectoral", "external": True},
    {"name": "Профспілка працівників охорони здоров'я України",
     "url": "https://medprof.org.ua/", "org_type": "sectoral", "external": True},
    {"name": "Професійна спілка працівників Пенсійного фонду України",
     "url": f"{_BASE_G}/166-profesijna-spilka-pratsivnikiv-pensijnogo-fondu-ukrajini.html", "org_type": "sectoral"},
    {"name": "Професійна спілка працівників радіоелектроніки та машинобудування України",
     "url": f"{_BASE_G}/164-profesijna-spilka-pratsivnikiv-radioelektroniki-ta-mashinobuduvannya-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка працівників рибного господарства України",
     "url": f"{_BASE_G}/163-profspilka-pratsivnikiv-ribnogo-gospodarstva-ukrajini.html", "org_type": "sectoral"},
    {"name": "Українська профспілка працівників річкового транспорту",
     "url": f"{_BASE_G}/162-ukrajinska-profesijna-spilka-pratsivnikiv-richkovogo-transportu.html", "org_type": "sectoral"},
    {"name": "Профспілка працівників соціальної сфери України",
     "url": f"{_BASE_G}/161-profspilka-pratsivnikiv-sotsialnoji-sferi-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка працівників споживчої кооперації України",
     "url": f"{_BASE_G}/160-profspilka-pratsivnikiv-spozhivchoji-kooperatsiji-ukrajini.html", "org_type": "sectoral"},
    {"name": "Всеукраїнська профспілка захисників України, спортсменів та працівників сфери фізичної культури",
     "url": f"{_BASE_G}/23108-vseukrajinska-profspilka-sportsmeniv-pratsivnikiv-sfer-fizichnoji-kulturi-i-sportu-molodizhnoji-politiki-ta-natsionalno-patriotichnogo-vikhovannya.html", "org_type": "sectoral"},
    {"name": "Професійна спілка працівників суднобудування України",
     "url": f"{_BASE_G}/159-profesijna-spilka-pratsivnikiv-sudnobuduvannya-ukrajini.html", "org_type": "sectoral"},
    {"name": "Професійна спілка таксистів України",
     "url": f"{_BASE_G}/158-profesijna-spilka-taksistiv-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка працівників текстильної та легкої промисловості України",
     "url": f"{_BASE_G}/157-profspilka-pratsivnikiv-tekstilnoji-ta-legkoji-promislovosti-ukrajini.html", "org_type": "sectoral"},
    {"name": "Всеукраїнська профспілка працівників і підприємців торгівлі, громадського харчування та послуг",
     "url": f"{_BASE_G}/156-vseukrajinska-profspilka-pratsivnikiv-i-pidpriemtsiv-torgivli-gromadskogo-kharchuvannya-ta-poslug-vseukrajinska-profspilka-torgivli.html", "org_type": "sectoral"},
    {"name": "Всеукраїнська незалежна профспілка працівників транспорту",
     "url": f"{_BASE_G}/155-vseukrajinska-nezalezhna-profspilka-pratsivnikiv-transportu.html", "org_type": "sectoral"},
    {"name": "Всеукраїнська профспілка «Футбол України»",
     "url": f"{_BASE_G}/154-vseukrajinska-profesijna-spilka-futbol-ukrajini.html", "org_type": "sectoral"},
    {"name": "Профспілка працівників хімічних та нафтохімічних галузей промисловості України",
     "url": "http://www.profchim.kiev.ua/", "org_type": "sectoral", "external": True},
    {"name": "Українська федерація профспілкових організацій — профспілка підприємств з іноземними інвестиціями",
     "url": f"{_BASE_G}/25248-ukrainska-federatsiia-profspilkovykh-orhanizatsii-profspilka-pratsivnykiv-pidpryiemstv-z-inozemnymy-investytsiiamy-hospodarskykh-tovarystv-orhanizatsii-ta-ustanov.html", "org_type": "sectoral"},
]

_TERYTORIALNI: list[dict] = [
    {"name": "Федерація профспілок Вінницької області",
     "url": f"{_BASE_T}/222-federatsiya-profspilok-vinnitskoji-oblasti.html", "org_type": "regional", "region": "Вінницька область"},
    {"name": "Федерація профспілок Волинської області",
     "url": f"{_BASE_T}/221-federatsiya-profspilok-volinskoji-oblasti.html", "org_type": "regional", "region": "Волинська область"},
    {"name": "Дніпропетровське обласне об'єднання профспілок",
     "url": f"{_BASE_T}/220-dnipropetrovske-oblasne-ob-ednannya-profspilok.html", "org_type": "regional", "region": "Дніпропетровська область"},
    {"name": "Донецька обласна рада професійних спілок",
     "url": f"{_BASE_T}/219-donetska-oblasna-rada-profesijnikh-spilok.html", "org_type": "regional", "region": "Донецька область"},
    {"name": "Федерація профспілок Житомирської області",
     "url": f"{_BASE_T}/218-federatsiya-profspilok-zhitomirskoji-oblasti.html", "org_type": "regional", "region": "Житомирська область"},
    {"name": "Закарпатська обласна рада профспілок",
     "url": f"{_BASE_T}/217-zakarpatska-oblasna-rada-profspilok.html", "org_type": "regional", "region": "Закарпатська область"},
    {"name": "Запорізька обласна рада профспілок",
     "url": f"{_BASE_T}/216-zaporizka-oblasna-rada-profspilok.html", "org_type": "regional", "region": "Запорізька область"},
    {"name": "Рада профспілок Івано-Франківської області",
     "url": f"{_BASE_T}/215-rada-profspilok-ivano-frankivskoji-oblasti.html", "org_type": "regional", "region": "Івано-Франківська область"},
    {"name": "Київська міська рада профспілок",
     "url": f"{_BASE_T}/214-kijivska-miska-rada-profspilok.html", "org_type": "regional", "region": "Київ"},
    {"name": "Київська обласна рада професійних спілок",
     "url": f"{_BASE_T}/213-kijivska-oblasna-rada-profesijnikh-spilok.html", "org_type": "regional", "region": "Київська область"},
    {"name": "Федерація профспілок Кіровоградської області",
     "url": f"{_BASE_T}/212-federatsiya-profspilok-kirovogradskoji-oblasti.html", "org_type": "regional", "region": "Кіровоградська область"},
    {"name": "Федерація незалежних профспілок Криму",
     "url": f"{_BASE_T}/211-federatsiya-nezalezhnikh-profspilok-krimu.html", "org_type": "regional", "region": "АР Крим"},
    {"name": "Федерація профспілок Луганської області",
     "url": f"{_BASE_T}/210-federatsiya-profspilok-luganskoji-oblasti.html", "org_type": "regional", "region": "Луганська область"},
    {"name": "Об'єднання профспілок Львівщини",
     "url": f"{_BASE_T}/209-ob-ednannya-profspilok-lvivshchini.html", "org_type": "regional", "region": "Львівська область"},
    {"name": "Миколаївська обласна рада профспілок",
     "url": f"{_BASE_T}/208-mikolajivska-oblasna-rada-profspilok.html", "org_type": "regional", "region": "Миколаївська область"},
    {"name": "Федерація профспілок Одеської області",
     "url": f"{_BASE_T}/207-federatsiya-profspilok-odeskoji-oblasti.html", "org_type": "regional", "region": "Одеська область"},
    {"name": "Полтавська обласна рада профспілок",
     "url": f"{_BASE_T}/206-poltavska-oblasna-rada-profspilok.html", "org_type": "regional", "region": "Полтавська область"},
    {"name": "Федерація профспілок Рівненської області",
     "url": f"{_BASE_T}/205-federatsiya-profspilok-rivnenskoji-oblasti.html", "org_type": "regional", "region": "Рівненська область"},
    {"name": "Сумська обласна рада професійних спілок",
     "url": f"{_BASE_T}/204-sumska-oblasna-rada-profesijnikh-spilok.html", "org_type": "regional", "region": "Сумська область"},
    {"name": "Тернопільська обласна рада профспілок",
     "url": f"{_BASE_T}/203-ternopilska-oblasna-rada-profspilok.html", "org_type": "regional", "region": "Тернопільська область"},
    {"name": "Об'єднання профспілок Харківської області",
     "url": f"{_BASE_T}/202-ob-ednannya-profspilok-kharkivskoji-oblasti.html", "org_type": "regional", "region": "Харківська область"},
    {"name": "Херсонська обласна міжгалузева рада профспілок",
     "url": f"{_BASE_T}/201-khersonska-oblasna-mizhgaluzeva-rada-profspilok.html", "org_type": "regional", "region": "Херсонська область"},
    {"name": "Федерація профспілок Хмельницької області",
     "url": f"{_BASE_T}/200-federatsiya-profspilok-khmelnitskoji-oblasti.html", "org_type": "regional", "region": "Хмельницька область"},
    {"name": "Федерація профспілок Черкаської області",
     "url": f"{_BASE_T}/199-federatsiya-profspilok-cherkaskoji-oblasti.html", "org_type": "regional", "region": "Черкаська область"},
    {"name": "Чернівецька обласна рада профспілок",
     "url": f"{_BASE_T}/198-chernivetska-oblasna-rada-profspilok.html", "org_type": "regional", "region": "Чернівецька область"},
    {"name": "Федерація профспілкових організацій Чернігівської області",
     "url": f"{_BASE_T}/197-federatsiya-profspilkovikh-organizatsij-chernigivskoji-oblasti.html", "org_type": "regional", "region": "Чернігівська область"},
    {"name": "Севастопольська міська рада профспілок",
     "url": f"{_BASE_T}/196-sevastopolska-miska-rada-profspilok.html", "org_type": "regional", "region": "Севастополь"},
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "uk,en;q=0.9",
}


class _ArticleParser(HTMLParser):
    """Extract text inside Joomla's div.item-page (or article body)."""

    def __init__(self) -> None:
        super().__init__()
        self._depth = 0
        self._in_body = False
        self._skip_depth: int | None = None
        self.title = ""
        self.text = ""
        self._h1_done = False
        self._h1_active = False

    def handle_starttag(self, tag: str, attrs: list[tuple]) -> None:
        classes = dict(attrs).get("class", "") or ""
        if "item-page" in classes or "article-body" in classes or "entry-content" in classes:
            self._in_body = True
            self._depth = 1
            return
        if self._in_body:
            self._depth += 1
        if tag == "h1" and not self._h1_done:
            self._h1_active = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self._h1_active = False
            self._h1_done = True
        if self._in_body:
            self._depth -= 1
            if self._depth <= 0:
                self._in_body = False

    def handle_data(self, data: str) -> None:
        if self._h1_active and not self._h1_done:
            self.title += data.strip()
        if self._in_body:
            self.text += data


def _fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_title_from_html(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        t = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        # Відкидаємо суфікс сайту
        for sep in (" :: ", " | ", " - "):
            if sep in t:
                t = t.split(sep)[0].strip()
        return t
    return ""


def _sanitize(s: str) -> str:
    """Strip NUL bytes and other control characters that PostgreSQL rejects."""
    return s.replace("\x00", "").replace("\u0000", "")


def _clean_text(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw).strip()
    return _sanitize(text)


def _parse_address(text: str) -> str:
    m = re.search(
        r"(?:адрес[аи]?\s*:?\s*|місцезнаходження\s*:?\s*)(.{10,200}?)(?=\n|\r|тел|е-?mail|$)",
        text, re.IGNORECASE,
    )
    return m.group(1).strip() if m else ""


def _parse_phone(text: str) -> str:
    m = re.search(
        r"(?:тел(?:ефон)?[.\s:]*|☎\s*)([+\d\s()\-/]{7,40})",
        text, re.IGNORECASE,
    )
    return m.group(1).strip() if m else ""


def _parse_email(text: str) -> str:
    m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return m.group(0).lower() if m else ""


def _parse_founded(text: str) -> int | None:
    m = re.search(
        r"(?:створен|засновани|утворен|заснован)\w*\s+(?:у\s+)?(\d{4})",
        text, re.IGNORECASE,
    )
    return int(m.group(1)) if m else None


def _parse_website(text: str) -> str:
    m = re.search(
        r"(?:сайт\s*:?\s*|www\.\s*)(https?://[^\s<>\"']+|www\.[^\s<>\"']+)",
        text, re.IGNORECASE,
    )
    if m:
        url = m.group(1).strip().rstrip(".,;)")
        if not url.startswith("http"):
            url = "https://" + url
        return url
    return ""


def _slug_from_url(url: str) -> str:
    """Extract slug from fpsu.org.ua URL path, e.g. '195-profspilka-aviabudivnikiv-ukrajini'."""
    path = url.rstrip("/").split("?")[0]
    last = path.split("/")[-1]
    last = re.sub(r"\.html?$", "", last, flags=re.IGNORECASE)
    last = last[:380]
    return last if last else ""


def _make_slug(title: str, source_url: str, existing: set[str]) -> str:
    from apps.core.models import MemOrgPage

    base = ""
    if source_url and "fpsu.org.ua" in source_url:
        base = _slug_from_url(source_url)

    if not base:
        base = slugify(title, allow_unicode=True) or "org"
        base = base[:360]

    slug = base
    i = 2
    while slug in existing or MemOrgPage.objects.filter(slug=slug).exclude(source_url=source_url).exists():
        slug = f"{base[:350]}-{i}"
        i += 1
    existing.add(slug)
    return slug


def _scrape_org(entry: dict) -> dict:
    """Fetch URL and extract fields. Returns partial dict for MemOrgPage."""
    url = entry["url"]
    is_external = entry.get("external", False)

    if is_external or "fpsu.org.ua" not in url:
        return {
            "title": entry["name"],
            "org_type": entry["org_type"],
            "region": entry.get("region", ""),
            "source_url": "",
            "website_url": url,
            "description": "",
            "address": "",
            "phone": "",
            "email": "",
            "founded_year": None,
            "meta_description": "",
        }

    html = _fetch_html(url)
    if not html:
        return {
            "title": entry["name"],
            "org_type": entry["org_type"],
            "region": entry.get("region", ""),
            "source_url": url,
            "website_url": "",
            "description": "",
            "address": "",
            "phone": "",
            "email": "",
            "founded_year": None,
            "meta_description": "",
        }

    parser = _ArticleParser()
    parser.feed(html)

    raw_text = _clean_text(parser.text)
    title = parser.title or _extract_title_from_html(html) or entry["name"]

    meta_m = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
        html, re.IGNORECASE,
    )
    meta_desc = meta_m.group(1).strip() if meta_m else ""

    return {
        "title": _sanitize(title or entry["name"]),
        "org_type": entry["org_type"],
        "region": entry.get("region", ""),
        "source_url": url,
        "website_url": _sanitize(_parse_website(raw_text)),
        "description": _sanitize(raw_text[:5000]),
        "address": _sanitize(_parse_address(raw_text)),
        "phone": _sanitize(_parse_phone(raw_text)),
        "email": _sanitize(_parse_email(raw_text)),
        "founded_year": _parse_founded(raw_text),
        "meta_description": _sanitize(meta_desc[:300]),
    }


class Command(BaseCommand):
    help = "Scrape fpsu.org.ua member organization pages and populate MemOrgPage model."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--update",
            action="store_true",
            help="Re-scrape and update existing records (default: skip existing)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print extracted data without saving to DB",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Delay in seconds between requests (default: 1.0)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.core.models import MemOrgPage

        update = options["update"]
        dry_run = options["dry_run"]
        delay = options["delay"]

        all_entries = _GALUZEVI + _TERYTORIALNI
        total = len(all_entries)
        created_count = 0
        updated_count = 0
        skipped_count = 0
        used_slugs: set[str] = set()

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Починаємо scraping {total} організацій (update={update}, dry_run={dry_run})"
            )
        )

        for idx, entry in enumerate(all_entries, 1):
            self.stdout.write(f"[{idx}/{total}] {entry['name'][:70]}...")

            data = _scrape_org(entry)

            if dry_run:
                self.stdout.write(
                    f"  title={data['title'][:60]}, "
                    f"address={data['address'][:40]}, "
                    f"phone={data['phone']}, "
                    f"email={data['email']}, "
                    f"website={data['website_url'][:40]}"
                )
                time.sleep(0.1)
                continue

            slug = _make_slug(data["title"], data["source_url"], used_slugs)

            existing = MemOrgPage.objects.filter(source_url=data["source_url"]).first() \
                if data["source_url"] else None

            if not existing and data["website_url"]:
                existing = MemOrgPage.objects.filter(website_url=data["website_url"]).first()

            if existing and not update:
                self.stdout.write(f"  → вже існує (id={existing.pk}), пропускаємо")
                used_slugs.add(existing.slug)
                skipped_count += 1
                time.sleep(0.05)
                continue

            fields = {
                "title": data["title"],
                "org_type": data["org_type"],
                "region": data.get("region", ""),
                "description": data["description"],
                "address": data["address"],
                "phone": data["phone"],
                "email": data["email"],
                "website_url": data["website_url"],
                "source_url": data["source_url"],
                "meta_description": data["meta_description"],
                "is_published": True,
            }
            if data["founded_year"]:
                fields["founded_year"] = data["founded_year"]

            if existing and update:
                for k, v in fields.items():
                    setattr(existing, k, v)
                # Also update slug if it looks like a generic fallback
                if re.match(r"^org(-\d+)?$", existing.slug):
                    existing.slug = slug
                    existing.save()
                else:
                    existing.save(update_fields=list(fields.keys()))
                used_slugs.add(existing.slug)
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"  → оновлено (id={existing.pk}, slug={existing.slug})"))
            else:
                fields["slug"] = slug
                obj = MemOrgPage(**fields)
                obj.save()
                used_slugs.add(slug)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  → створено (id={obj.pk}, slug={slug})"))

            if data["source_url"] and "fpsu.org.ua" in data["source_url"]:
                time.sleep(delay)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nГотово! Створено: {created_count}, оновлено: {updated_count}, "
                f"пропущено: {skipped_count} з {total}"
            )
        )

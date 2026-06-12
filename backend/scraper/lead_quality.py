import re


_TR_TRANSLATION = str.maketrans('İıĞğŞşÇçÖöÜü', 'IiGgSsCcOoUu')

_CLEAR_NON_PERSON_NAME_TERMS = {
    "about", "about us", "academic", "academy", "admin", "blog", "career",
    "careers", "contact", "contact us", "department", "directory", "event",
    "events", "faculty", "home", "homepage", "institute", "job", "jobs",
    "login", "privacy", "program", "school", "services", "team",
    "teacher workshops", "training", "want take", "workshop", "workshops",
    "arkadaşınızın adresi", "arkadasinizin adresi", "belge hazırlığı",
    "belge hazirligi", "toefl ibt", "deneme sınavları", "deneme sinavlari",
    "küresel perspektif", "kuresel perspektif", "geleneksel yemekleri",
    "geleneksel lezzetler", "günlük rutini", "gunluk rutini",
    "aylık bütçesi", "aylik butcesi", "yaş öğrencilik", "yas ogrencilik",
    "kurumsaliletisim", "dilmer", "oidb", "ialf indonesia",
    "saglikbilfakulte", "üniversite seçimi", "universite secimi",
    "güz dönemi", "guz donemi", "çok toplum", "cok toplum",
    "çek vizesi", "cek vizesi", "çok yapı", "cok yapi",
    "ikonik lezzetleri", "akademik içerir", "akademik icerir",
}

_CLEAR_NON_PERSON_NAME_TOKENS = {
    "about", "academic", "academy", "admin", "blog", "career", "careers",
    "contact", "department", "directory", "event", "events", "faculty",
    "home", "homepage", "institute", "job", "jobs", "login", "privacy",
    "program", "school", "service", "services", "team", "training",
    "workshop", "workshops", "course", "courses", "class", "classes",
    "lesson", "lessons", "module", "modules", "product", "products",
    "exam", "exams", "test", "tests", "toefl", "ielts", "ibt",
    "resource", "resources", "guide", "guides", "newsletter",
    "address", "adres", "adresi", "arkadasinizin", "belge", "hazirligi",
    "sinav", "sinavi", "sinavlari", "deneme", "kaynak", "kaynaklar",
    "kuresel", "perspektif", "geleneksel", "yemekleri", "lezzetler",
    "gunluk", "rutini", "aylik", "butcesi", "yas", "ogrencilik",
    "kurumsaliletisim", "dilmer", "oidb", "ialf", "saglikbilfakulte",
    "universite", "secimi", "guz", "donemi", "cok", "toplum", "cek",
    "vizesi", "vize", "yapi", "ikonik", "lezzetleri", "akademik",
    "icerir",
}


def _normalize_name_text(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    return normalized


def _ascii_fold(value: str) -> str:
    return value.translate(_TR_TRANSLATION)


def looks_like_clear_non_person_name(lead_name: str | None) -> bool:
    """Return True only for obvious page/company labels, never for missing names."""
    if not lead_name:
        return False

    normalized = _normalize_name_text(lead_name)
    if not normalized:
        return False

    ascii_normalized = _ascii_fold(normalized)
    if normalized in _CLEAR_NON_PERSON_NAME_TERMS or ascii_normalized in _CLEAR_NON_PERSON_NAME_TERMS:
        return True
    if any(char.isdigit() for char in normalized):
        return True

    tokens = re.findall(r"[a-zA-ZğüşöçıİĞÜŞÖÇ]+", normalized)
    ascii_tokens = [_ascii_fold(token) for token in tokens]
    if not tokens:
        return True
    if len(tokens) > 5:
        return True
    if any(token in _CLEAR_NON_PERSON_NAME_TOKENS for token in ascii_tokens):
        return True
    if all(token in _CLEAR_NON_PERSON_NAME_TERMS for token in ascii_tokens):
        return True
    return False

"""Remote/global English-primary job search helpers for the dashboard."""

from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


DATE_WINDOWS = {
    "Last 3 days": 3,
    "One week": 7,
    "Two weeks": 14,
    "One month": 30,
}

GLOBAL_LOCATION_PATTERNS = (
    r"\bworldwide\b",
    r"\bglobal\b",
    r"\banywhere\b",
    r"\banywhere in the world\b",
    r"\binternational\b",
    r"\bwork from anywhere\b",
)

NON_ENGLISH_PRIMARY_PATTERNS = (
    r"\bfrench language\b",
    r"\bfrench speakers?\b",
    r"\bspanish language\b",
    r"\bspanish speakers?\b",
    r"\bgerman language\b",
    r"\bgerman speakers?\b",
    r"\bitalian language\b",
    r"\bitalian speakers?\b",
    r"\bportuguese language\b",
    r"\bportuguese speakers?\b",
    r"\bdutch language\b",
    r"\bdutch speakers?\b",
    r"\bjapanese language\b",
    r"\bjapanese speakers?\b",
    r"\bmandarin language\b",
    r"\bmandarin speakers?\b",
    r"\barabic language\b",
    r"\barabic speakers?\b",
)

ENGLISH_EVIDENCE_PATTERNS = (
    r"\bnative english\b",
    r"\bprimary language (?:is )?english\b",
    r"\benglish as (?:a )?(?:first|primary|native) language\b",
    r"\bfluent (?:in )?english\b",
    r"\bexcellent (?:written and verbal )?english\b",
    r"\benglish proficiency\b",
    r"\benglish[- ]speaking\b",
    r"\benglish speakers?\b",
    r"\bc[12]\s+english\b",
    r"\benglish\b",
)

STOPWORDS = {
    "about",
    "after",
    "all",
    "also",
    "and",
    "are",
    "can",
    "candidate",
    "candidates",
    "company",
    "description",
    "english",
    "for",
    "from",
    "fluent",
    "global",
    "globally",
    "have",
    "job",
    "language",
    "must",
    "our",
    "remote",
    "role",
    "that",
    "the",
    "their",
    "this",
    "with",
    "work",
    "worldwide",
    "you",
    "your",
}


@dataclass(frozen=True)
class JobListing:
    source: str
    title: str
    company: str
    url: str
    location: str
    published_at: str
    description: str
    tags: list[str]
    match_score: int
    keyword_matches: list[str]
    english_evidence: list[str]

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["tags"] = ", ".join(self.tags)
        row["keyword_matches"] = ", ".join(self.keyword_matches)
        row["english_evidence"] = " | ".join(self.english_evidence)
        row["description"] = self.description[:500]
        return row


def strip_html(value: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    raw = str(value).strip().replace("Z", "+00:00")
    for candidate in (raw, raw.split(".")[0]):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def extract_keywords(text: str, max_terms: int = 14) -> list[str]:
    counts: dict[str, int] = {}
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{2,}", text.lower()):
        word = raw.strip(".-")
        if len(word) < 3 or word in STOPWORDS:
            continue
        counts[word] = counts.get(word, 0) + 1

    return [
        word
        for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ][:max_terms]


def normalize_match_word(word: str) -> str:
    value = word.lower().strip(".-")
    if len(value) > 5 and value.endswith("ies"):
        return value[:-3] + "y"
    for suffix in ("ing", "ers", "er", "ed", "es", "s"):
        if len(value) > len(suffix) + 4 and value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def match_tokens(text: str) -> set[str]:
    tokens = set()
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{2,}", text.lower()):
        word = raw.strip(".-")
        if len(word) < 3 or word in STOPWORDS:
            continue
        tokens.add(word)
        tokens.add(normalize_match_word(word))
    return tokens


def keyword_matches_text(keyword: str, tokens: set[str], fuzzy_threshold: float) -> tuple[bool, str | None]:
    normalized_keyword = normalize_match_word(keyword)
    if keyword in tokens or normalized_keyword in tokens:
        return True, keyword

    for token in tokens:
        if len(token) < 4:
            continue
        if (
            len(normalized_keyword) >= 5
            and len(token) >= 5
            and (normalized_keyword.startswith(token) or token.startswith(normalized_keyword))
        ):
            return True, f"{keyword}~{token}"
        if (
            normalized_keyword[:4] == token[:4]
            and SequenceMatcher(None, normalized_keyword, token).ratio() >= max(0.72, fuzzy_threshold - 0.1)
        ):
            return True, f"{keyword}~{token}"
        if SequenceMatcher(None, normalized_keyword, token).ratio() >= fuzzy_threshold:
            return True, f"{keyword}~{token}"

    return False, None


def default_search_phrase(job_description: str) -> str:
    keywords = extract_keywords(job_description, max_terms=6)
    return " ".join(keywords[:5]) if keywords else "english remote"


def is_global_remote(location: str, description: str = "") -> bool:
    location_text = (location or "").strip().lower()
    description_text = (description or "")[:1200].lower()

    if not location_text and not description_text.strip():
        return False

    location_is_global = any(
        re.search(pattern, location_text) for pattern in GLOBAL_LOCATION_PATTERNS
    )
    description_is_global = any(
        re.search(pattern, description_text) for pattern in GLOBAL_LOCATION_PATTERNS
    )

    generic_remote_locations = {"remote", "remote only", "fully remote", "n/a", "na"}
    if location_text and location_text not in generic_remote_locations:
        return location_is_global

    return location_is_global or description_is_global


def find_english_evidence(title: str, description: str) -> list[str]:
    text = strip_html(f"{title}. {description}")
    lower = text.lower()
    if any(re.search(pattern, lower) for pattern in NON_ENGLISH_PRIMARY_PATTERNS):
        return []

    snippets: list[str] = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for pattern in ENGLISH_EVIDENCE_PATTERNS:
        for sentence in sentences:
            if re.search(pattern, sentence.lower()):
                cleaned = sentence.strip()
                if cleaned and cleaned not in snippets:
                    snippets.append(cleaned[:180])
                break
        if snippets:
            break
    return snippets[:3]


def within_window(published_at: str, days: int, now: datetime | None = None) -> bool:
    parsed = parse_datetime(published_at)
    if parsed is None:
        return False
    current = now or datetime.now(timezone.utc)
    return parsed >= current - timedelta(days=days)


def score_listing(
    title: str,
    description: str,
    tags: list[str],
    keywords: list[str],
    fuzzy_threshold: float = 0.84,
) -> tuple[int, list[str]]:
    haystack = strip_html(f"{title} {' '.join(tags)} {description}").lower()
    title_lower = title.lower()
    tag_lower = " ".join(tags).lower()
    listing_tokens = match_tokens(haystack)
    title_tokens = match_tokens(title_lower)
    tag_tokens = match_tokens(tag_lower)

    score = 0
    matches: list[str] = []
    used_match_tokens: set[str] = set()
    for keyword in keywords:
        matched, match_label = keyword_matches_text(keyword, listing_tokens, fuzzy_threshold)
        if not matched:
            continue

        label = match_label or keyword
        matched_token = label.split("~", 1)[1] if "~" in label else normalize_match_word(label)
        if matched_token in used_match_tokens:
            continue
        used_match_tokens.add(matched_token)

        matches.append(label)
        score += 1
        if keyword_matches_text(keyword, tag_tokens, fuzzy_threshold)[0]:
            score += 1
        if keyword_matches_text(keyword, title_tokens, fuzzy_threshold)[0]:
            score += 3
    return score, matches


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "AIAlchemyJobseeker/1.0 (+local dashboard)",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def fetch_remotive_jobs(query: str, limit: int = 80) -> list[dict[str, Any]]:
    encoded = urllib.parse.urlencode({"search": query})
    payload = fetch_json(f"https://remotive.com/api/remote-jobs?{encoded}")
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    return jobs[:limit]


def fetch_remoteok_jobs(limit: int = 200) -> list[dict[str, Any]]:
    payload = fetch_json("https://remoteok.com/api")
    jobs = payload[1:] if isinstance(payload, list) and payload else []
    return jobs[:limit]


def normalize_remotive(job: dict[str, Any], keywords: list[str], fuzzy_threshold: float = 0.84) -> JobListing | None:
    title = str(job.get("title") or "")
    company = str(job.get("company_name") or "")
    description = strip_html(str(job.get("description") or ""))
    location = str(job.get("candidate_required_location") or "")
    tags = [str(value) for value in (job.get("tags") or []) if value]
    if job.get("category"):
        tags.append(str(job["category"]))

    score, matches = score_listing(title, description, tags, keywords, fuzzy_threshold=fuzzy_threshold)
    evidence = find_english_evidence(title, description)
    return JobListing(
        source="Remotive",
        title=title,
        company=company,
        url=str(job.get("url") or ""),
        location=location,
        published_at=str(job.get("publication_date") or ""),
        description=description,
        tags=tags,
        match_score=score,
        keyword_matches=matches,
        english_evidence=evidence,
    )


def normalize_remoteok(job: dict[str, Any], keywords: list[str], fuzzy_threshold: float = 0.84) -> JobListing | None:
    title = str(job.get("position") or job.get("title") or "")
    company = str(job.get("company") or "")
    description = strip_html(str(job.get("description") or ""))
    location = str(job.get("location") or "")
    tags = [str(value) for value in (job.get("tags") or []) if value]
    score, matches = score_listing(title, description, tags, keywords, fuzzy_threshold=fuzzy_threshold)
    evidence = find_english_evidence(title, description)
    return JobListing(
        source="RemoteOK",
        title=title,
        company=company,
        url=str(job.get("url") or job.get("apply_url") or ""),
        location=location,
        published_at=str(job.get("date") or ""),
        description=description,
        tags=tags,
        match_score=score,
        keyword_matches=matches,
        english_evidence=evidence,
    )


def keep_listing(
    listing: JobListing,
    days: int,
    now: datetime | None = None,
    min_match_score: int = 1,
) -> bool:
    return (
        bool(listing.url)
        and within_window(listing.published_at, days, now=now)
        and is_global_remote(listing.location, listing.description)
        and bool(listing.english_evidence)
        and listing.match_score >= min_match_score
    )


def search_jobs(
    job_description: str,
    date_window_label: str,
    search_phrase: str | None = None,
    max_per_source: int = 80,
    min_match_score: int = 1,
    fuzzy_threshold: float = 0.84,
    now: datetime | None = None,
) -> list[JobListing]:
    days = DATE_WINDOWS[date_window_label]
    keywords = extract_keywords(job_description)
    query = (search_phrase or default_search_phrase(job_description)).strip()
    if "english" not in query.lower():
        query = f"{query} english".strip()

    seen_urls: set[str] = set()
    results: list[JobListing] = []

    source_batches: list[tuple[str, list[dict[str, Any]]]] = [
        ("remotive", fetch_remotive_jobs(query, limit=max_per_source)),
        ("remoteok", fetch_remoteok_jobs(limit=max_per_source)),
    ]

    for source_name, jobs in source_batches:
        for job in jobs:
            listing = (
                normalize_remotive(job, keywords, fuzzy_threshold=fuzzy_threshold)
                if source_name == "remotive"
                else normalize_remoteok(job, keywords, fuzzy_threshold=fuzzy_threshold)
            )
            if not listing or listing.url in seen_urls:
                continue
            seen_urls.add(listing.url)
            if keep_listing(listing, days, now=now, min_match_score=min_match_score):
                results.append(listing)

    return sorted(
        results,
        key=lambda item: (
            item.match_score,
            parse_datetime(item.published_at) or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )

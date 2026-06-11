#!/usr/bin/env python3
"""Download PDF assets for NHC standards — uses requests, no Playwright needed."""

from __future__ import annotations

import time
import uuid

import requests


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def main() -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from harvester.db.models import RawObject
    from harvester.db.settings import DatabaseSettings
    from harvester.jobs.archive import ArchiveConfig, ArchiveWriter
    from harvester.jobs.repository import create_job

    settings = DatabaseSettings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    source_id = uuid.UUID("095ae9c9-1d54-46a3-b77b-d92aae7c580a")
    BATCH = 20

    http = requests.Session()
    http.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://www.nhc.gov.cn/",
    })

    total = 0
    batch_num = 0

    while True:
        session = Session()
        rows = session.execute(
            text("""
                UPDATE crawl_targets SET status='running', updated_at=NOW()
                WHERE id IN (
                    SELECT id FROM crawl_targets
                    WHERE source_id = :s AND media_type='pdf' AND status='pending'
                    ORDER BY last_seen_at ASC LIMIT :n
                ) RETURNING id, target_url, category
            """),
            {"s": source_id, "n": BATCH},
        ).fetchall()
        if not rows:
            session.commit()
            session.close()
            break

        batch_num += 1
        t0 = time.time()
        ok = 0
        fails = 0

        for idx, (tid, url, cat) in enumerate(rows):
            t1 = time.time()
            try:
                resp = http.get(url, timeout=30, allow_redirects=True)
                resp.raise_for_status()

                content_type = resp.headers.get("Content-Type", "application/pdf")
                if b"%PDF" not in resp.content[:10]:
                    # Some PDFs redirect to HTML error pages
                    if resp.content.strip().startswith(b"<!") or resp.content.strip().startswith(b"<html"):
                        raise RuntimeError("got HTML instead of PDF")
                    # Still try if it's PDF-like
                    if b"%PDF" not in resp.content[:1024]:
                        raise RuntimeError(f"not a PDF (starts with {resp.content[:20]})")

                # Derive filename from URL
                filename = url.rsplit("/", 1)[-1]
                if not filename.endswith(".pdf"):
                    filename += ".pdf"

                ar = ArchiveWriter(ArchiveConfig.from_env()).write(
                    payload=resp.content,
                    source_id=source_id,
                    crawl_run_id=uuid.uuid4(),
                    content_type="application/pdf",
                    original_url=url,
                    category_override=cat,
                    suggested_filename=filename,
                )
                rid = uuid.uuid4()
                session.add(RawObject(
                    id=rid, source_id=source_id, content_type="application/pdf",
                    content_hash=ar.content_hash, storage_uri=ar.storage_uri,
                    byte_size=ar.byte_size, retention_policy="raw",
                    retain_until=ar.retain_until, compressed=False,
                ))
                session.flush()
                session.execute(text(
                    "UPDATE crawl_targets SET status='completed', last_raw_object_id=:r, "
                    "final_url=:u, last_error=NULL, updated_at=NOW() WHERE id=:t"
                ), {"r": rid, "u": resp.url, "t": tid})
                create_job(session, job_type="extract",
                           payload={"raw_object_id": str(rid)},
                           source_id=str(source_id), auto_commit=False)
                ok += 1
                dt = time.time() - t1
                if idx % 5 == 0:
                    log(f"  [{idx+1}/{len(rows)}] ok {filename[:40]} {len(resp.content)}b {dt:.1f}s")
            except Exception as exc:
                fails += 1
                try:
                    with session.begin_nested():
                        session.execute(text(
                            "UPDATE crawl_targets SET status='failed', "
                            "failure_count=failure_count+1, last_error=:e, "
                            "updated_at=NOW() WHERE id=:t AND status='running'"
                        ), {"e": str(exc)[:300], "t": tid})
                except Exception:
                    pass
                if fails <= 5:
                    log(f"  [{idx+1}/{len(rows)}] FAIL {url[-50:]} {exc}")

        session.commit()
        session.close()
        elapsed = time.time() - t0
        speed = ok / elapsed * 60 if elapsed > 0 else 0
        total += ok
        log(f"batch#{batch_num}: {ok}/{len(rows)} ok {fails}fail {elapsed:.0f}s ({speed:.0f}/min) total={total}")

    log(f"ALL DONE. {total} PDFs downloaded.")


if __name__ == "__main__":
    main()

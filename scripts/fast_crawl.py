#!/usr/bin/env python3
"""Fast batch crawl — shared browser, serial pages, minimal waits."""

from __future__ import annotations

import time
import uuid


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def main() -> None:
    from playwright.sync_api import sync_playwright
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

    total = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--disable-gpu", "--no-sandbox"],
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        log("browser ready")

        batch_num = 0
        while True:
            session = Session()
            rows = session.execute(
                text("""
                    UPDATE crawl_targets SET status='running', updated_at=NOW()
                    WHERE id IN (
                        SELECT id FROM crawl_targets
                        WHERE source_id = :s AND media_type='html' AND status='pending'
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
            page = ctx.new_page()

            for idx, (tid, url, cat) in enumerate(rows):
                t1 = time.time()
                try:
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    except Exception:
                        pass

                    # Brief wait for anti-bot JS
                    time.sleep(1)

                    html = ""
                    for _ in range(3):
                        try:
                            html = page.content()
                            if len(html) > 200:
                                break
                        except Exception:
                            time.sleep(1)
                        else:
                            if len(html) < 200:
                                time.sleep(1)

                    if not html or len(html) < 200:
                        raise RuntimeError(f"empty page ({len(html)}b)")

                    ar = ArchiveWriter(ArchiveConfig.from_env()).write(
                        payload=html.encode(),
                        source_id=source_id,
                        crawl_run_id=uuid.uuid4(),
                        content_type="text/html",
                        original_url=url,
                        category_override=cat,
                    )
                    rid = uuid.uuid4()
                    session.add(RawObject(
                        id=rid, source_id=source_id, content_type="text/html",
                        content_hash=ar.content_hash, storage_uri=ar.storage_uri,
                        byte_size=ar.byte_size, retention_policy="raw",
                        retain_until=ar.retain_until, compressed=False,
                    ))
                    session.flush()
                    session.execute(text(
                        "UPDATE crawl_targets SET status='completed', last_raw_object_id=:r, "
                        "final_url=:u, last_error=NULL, updated_at=NOW() WHERE id=:t"
                    ), {"r": rid, "u": url, "t": tid})
                    create_job(session, job_type="extract",
                               payload={"raw_object_id": str(rid)},
                               source_id=str(source_id), auto_commit=False)
                    ok += 1
                    dt = time.time() - t1
                    if idx % 5 == 0:
                        log(f"  [{idx+1}/{len(rows)}] ok {dt:.1f}s {len(html)}b")
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
                    if fails <= 3:
                        log(f"  [{idx+1}/{len(rows)}] FAIL {str(exc)[:80]}")

            page.close()
            session.commit()
            session.close()
            elapsed = time.time() - t0
            speed = ok / elapsed * 60 if elapsed > 0 else 0
            total += ok
            remaining = 0
            # Quick remaining count check every 5 batches
            if batch_num % 5 == 0:
                s2 = Session()
                r2 = s2.execute(text(
                    "SELECT COUNT(*) FROM crawl_targets WHERE source_id=:s AND media_type='html' AND status='pending'"
                ), {"s": source_id}).scalar()
                remaining = r2
                s2.close()
            log(f"batch#{batch_num}: {ok}/{len(rows)} ok {fails}fail {elapsed:.0f}s ({speed:.0f}/min) total={total} remaining={remaining}")

        ctx.close()
        browser.close()

    log(f"ALL DONE. {total} detail pages.")


if __name__ == "__main__":
    main()

#!/bin/env python
from datetime import UTC, datetime, timedelta
import logging
import random
from functools import wraps
from json import JSONDecodeError
import asyncio
import base64

from cryptography import x509
import httpx
import structlog


logger = structlog.stdlib.get_logger()
client = httpx.AsyncClient()



def decode_cert(leaf: bytes) -> x509.Certificate:
    # MerkleTreeLeaf for timestamped entry containing an x509 certificate:
    #
    # +------+-----------------------+
    # | Byte |                       |
    # +------+-----------------------+
    # |    0 |        Version        |
    # +------+-----------------------+
    # |    1 |       Leaf type       |
    # +------+-----------------------+
    # |    2 |                       |
    # |    3 |                       |
    # |    4 |                       |
    # |    5 |       Timestamp       |
    # |    6 |                       |
    # |    7 |                       |
    # |    8 |                       |
    # |    9 |                       |
    # +------+-----------------------+
    # |   10 |       Entry type      |
    # |   11 |                       |
    # +------+-----------------------+
    # |   12 |                       |
    # |   13 |    Cert length (n)    |
    # |   14 |                       |
    # +------+-----------------------+
    # |   15 |                       |
    # |   .. |     x509 DER cert     |
    # |    n |                       |
    # +------+-----------------------+
    # |  n+1 |     CT extensions     |
    # |   .. |                       |
    # +------+-----------------------+
    #
    # https://www.rfc-editor.org/rfc/rfc6962.html#section-3.4
    # https://www.rfc-editor.org/rfc/rfc5246.html#section-4

    # RFC 6962 only defines version 1 (0x00) of the merkle tree leaf and
    # a single leaf type: timestamped entry (0x00).
    if (version := leaf[0]) != 0:
        raise ValueError(f"Unknown version {version}")
    if (leaf_type := leaf[1]) != 0:
        raise ValueError(f"Unknown leaf type {leaf_type}")

    if leaf[10:12] != b"\x00\x00":
        # Timestamped entry type 0x0000 designates a x509 certificate. Type
        # 0x001 is a precert, which we can not use, and therefore ignore.
        raise TypeError("Not x509 entry")

    cert_length = int.from_bytes(leaf[12:15], "big")
    cert_bytes = leaf[15 : 15 + cert_length]
    cert = x509.load_der_x509_certificate(cert_bytes)
    return cert


async def get_log_urls() -> set[str]:
    """TODO."""
    # The format of these server lists are not part of the RFC, but both
    # Apple's and Google's list follow the same format.
    # https://certificate.transparency.dev/useragents/
    log_lists = {
        "https://www.gstatic.com/ct/log_list/v3/log_list.json",
        "https://valid.apple.com/ct/log_list/current_log_list.json",
    }
    now = datetime.now(tz=UTC)
    logs = set()
    for log_list in log_lists:
        r = await client.get(log_list)
        if not r.is_success:
            continue
        for operator in r.json()["operators"]:
            for log in operator["logs"]:
                if "usable" not in log["state"]:
                    continue
                interval = log["temporal_interval"]
                if datetime.fromisoformat(interval["start_inclusive"]) > now:
                    continue
                if datetime.fromisoformat(interval["end_exclusive"]) < now:
                    continue
                logs.add(log["url"])
    if not logs:
        raise ValueError("Failed to retrieve certificate log servers")
    return logs



def forever(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        while True:
            try:
                await f(*args, **kwargs)
            except Exception:
                logger.exception("Retrying")
                await asyncio.sleep(30)
            except:
                break

    return wrapper


class Watcher:
    page_size = 32

    def __init__(self, server: str, queue: asyncio.Queue) -> None:
        self.server = server
        self.queue = queue

        self.log = logger.bind(server=server)

        self.tree_size = 0
        self.tree_watcher = asyncio.create_task(self.watch_tree_size())

        self.start = 0
        self.end = 0

    @forever
    async def watch_tree_size(self) -> None:
        self.log.debug("get-sth")
        r = await client.get(f"{self.server}ct/v1/get-sth")
        self.tree_size = r.json()["tree_size"]
        self.log.debug("sth", size=self.tree_size)
        await asyncio.sleep(600)

    @forever
    async def watcher(self) -> None:
        index = random.randrange(self.start, self.tree_size - self.page_size)
        self.log.debug("get-entries", index=index)
        r = await client.get(
            f"{self.server}ct/v1/get-entries",
            params={
                "start": index,
                "end": index + self.page_size,
            },
        )
        entries = r.json()["entries"]

        now = datetime.now(tz=UTC)
        for entry in entries:
            leaf = base64.b64decode(entry["leaf_input"])
            try:
                cert = decode_cert(leaf)
            except TypeError:
                # Ignore precerts
                continue
            # Move start of search space up if certificate was issued more than
            # 398 days ago; the maximum validity period of public certificates.
            # https://cabforum.org/working-groups/server/baseline-requirements/documents/CA-Browser-Forum-TLS-BR-2.0.7.pdf#3d
            if cert.not_valid_before_utc < now - timedelta(days=398):
                print(cert.not_valid_before_utc, "moving from", self.start, "to", index)
                self.start = index
                break
            if cert.not_valid_before_utc > now:
                continue
            if cert.not_valid_after_utc < now:
                continue
            await self.queue.put(cert)



q = asyncio.Queue(maxsize=128)


async def asd():
    while True:
        # await asyncio.sleep(0.1)
        cert = await q.get()
        print(cert)


async def main():
    asyncio.create_task(asd())
    urls = await get_log_urls()
    for url in urls:
        w = Watcher(url, q)
        asyncio.create_task(w.watch_tree_size())
        await asyncio.sleep(3)
        asyncio.create_task(w.watcher())
        break
    await asyncio.sleep(99999)

asyncio.run(main())

# TODO:
# if 429 too many request => self.sleep += 1
# if queue empty: crash (something is definitely wrong!)

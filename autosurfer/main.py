import asyncio
import json
import os

import websockets
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.remote.webelement import WebElement

service = webdriver.FirefoxService(
    # Selenium only checks /usr/bin/geckodriver by default
    executable_path="/bin/geckodriver",
)

options = webdriver.FirefoxOptions()
# Selenium only checks /usr/bin/firefox by default
options.binary_location = "/bin/firefox"

if not os.getenv("DISPLAY"):
    options.add_argument("--headless")

driver = webdriver.Firefox(service=service, options=options)
driver.set_page_load_timeout(3)


async def ct_stream(domains: asyncio.Queue) -> None:
    """Watch Certificate Transparency (CT) logs for new certificates."""
    while True:
        try:
            async with websockets.connect("wss://certstream.calidog.io") as websocket:
                async for message_data in websocket:
                    ct_handler(message_data, domains)
        except (KeyboardInterrupt, asyncio.CancelledError):
            return
        except Exception as e:
            print(e)


def ct_handler(data: websockets.Data, domains: asyncio.Queue) -> None:
    """Save certificate's domain to queue if needed."""
    # There are A LOT of certificates coming through the transparency logs;
    # immediately bail without spending time decoding the message if we have
    # enough domains queued up already.
    if domains.full():
        return

    message = json.loads(data)
    if message["message_type"] != "certificate_update":
        return

    # Certificates can verify multiple domains: We arbitrarily select the first
    # non-wildcard one since we cannot connect to such host in the browser.
    cert_domains = message["data"]["leaf_cert"]["all_domains"]
    try:
        cert_domain = next(d for d in cert_domains if "*" not in d)
    except StopIteration:
        return

    domains.put_nowait(cert_domain)


async def surfer() -> None:
    """Continuously open domains from the queue in Firefox."""
    domains = asyncio.Queue(maxsize=50)
    ct_stream_task = asyncio.create_task(ct_stream(domains))
    while True:
        domain = await domains.get()
        url = f"https://{domain}"
        print("🏄", url)
        try:
            await asyncio.to_thread(driver.get, url)
        except WebDriverException:
            pass
        except (KeyboardInterrupt, asyncio.CancelledError):
            break
    ct_stream_task.cancel()


asyncio.run(surfer())

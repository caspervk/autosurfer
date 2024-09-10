import asyncio
import math
import os
import random

from selenium import webdriver
from selenium.common.exceptions import InvalidSessionIdException
from selenium.common.exceptions import WebDriverException

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


async def surf(url: str) -> None:
    """Surf around URL for a bit."""
    for i in range(math.ceil(random.expovariate(0.5))):
        print("🏄" if i == 0 else "🔗", url)
        try:
            await asyncio.to_thread(driver.get, url)
            # Find all links on page. This is *much* faster than find_elements("a") + get_attribute("href")
            links = await asyncio.to_thread(
                driver.execute_script,
                "return [...document.links].filter(a => !!a.host && a.href != location.href && !a.href.includes('#')).map(a => a.href);",
            )
        except InvalidSessionIdException:
            # Browser closed: no way to recover
            raise
        except WebDriverException as e:
            print(e)
            print(type(e))
            # Timeout, network error, JavaScript failure etc.
            break
        try:
            url = random.choice(links)
        except IndexError:
            break


async def surfer() -> None:
    """Continuously open domains from the queue in Firefox."""
    domains = asyncio.Queue(maxsize=50)
    ct_stream_task = asyncio.create_task(ct_stream(domains))
    while True:
        try:
            # TODO: asyncio.wait_for?
            domain = await domains.get()
            url = f"https://{domain}"
            await surf(url)
        except (KeyboardInterrupt, asyncio.CancelledError) as e:
            print(e)
            raise
    ct_stream_task.cancel()


asyncio.run(surfer())

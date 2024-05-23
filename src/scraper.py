import inquirer.questions
import pyppeteer
import inquirer
from pathlib import Path
import json
import csv
import asyncio
import logging
import functools
import math
import random


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

__all__ = ["scrape", "log"]


async def scrape(product_url):
    browser = await pyppeteer.launch(
        # options={"executablePath": "/usr/bin/google-chrome-stable", "headless": False},
    )
    page = await browser.newPage()

    await page.goto(product_url)
    await page.waitForSelector("[data-test='product-title']")

    try:
        await page.evaluate(
            """
            async () => {
                await new Promise((resolve) => {
                    var totalHeight = 0;
                    var distance = 100;
                    var timer = setInterval(() => {
                        var scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;

                        if (totalHeight >= scrollHeight - window.innerHeight) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 50);
                });
            }"""
        )

        await asyncio.sleep(1.5)
        product_name = await page.evaluate(
            "() => document.querySelector(\"[data-test='product-title']\").innerText"
        )

        try:
            await page.waitForSelector('[data-test="reviews-list"]')
        except Exception as e:
            log.error("Error occurred while waiting for reviews list", exc_info=e)
            log.info("Could not find reviews list")
            return product_name, []

        data = await page.evaluate(
            r"""
async () => {
    console.log("Im here")
    const { ProductName, ProductPrice } = { ProductName: document.querySelector("[data-test='product-title']").innerText, ProductPrice: document.querySelector("[data-test='product-price']").innerText.replace("$", "").replaceAll(/([^\d\.])/g, "") }
    const overallConstants = { ProductName, ProductPrice, TotalStars: 0, TotalStarsAverage: 0, TotalReviews: 0, TotalRecommendations: 0, TotalQuality: 0, TotalValue: 0, PercentFiveStars: 0, PercentFourStars: 0, PercentThreeStars: 0, PercentTwoStars: 0, PercentOneStars: 0 }
    const delay = ms => new Promise(resolve => setTimeout(resolve, ms))


    while (true) {
        const reviewListTemp = document.querySelector('[data-test="reviews-list"]')
        const loadMore = reviewListTemp.nextElementSibling
        if (loadMore.hasAttribute('data-test') && loadMore.getAttribute('data-test') === 'load-more-btn') {
            loadMore.querySelector('button').click()
            await delay(3000)
        } else {
            break
        }

    }

    // Handling constant values that will be present in each review Object
    const ratingHistogram = document.querySelector('div[data-test="rating-histogram"]');

    for (const button of ratingHistogram.querySelectorAll('button')) {
        const ariaLabel = button.getAttribute('aria-label')
        const match = ariaLabel.match(/((?<pc>\d{1,2}?\%)(?:.+)(?<starCount>[1-5](?=\sstars)))/)
        let pc, starCount;
        if (!match) {
            ({ pc, starCount } = { pc: '0%', starCount: '0' })
        } else {
            ({ pc, starCount } = match.groups)
        }
        pc = parseInt(pc.replace("%", ""))
        switch (starCount) {
            case '1':
                overallConstants["PercentOneStars"] = pc
                break
            case '2':
                overallConstants["PercentTwoStars"] = pc
                break
            case '3':
                overallConstants["PercentThreeStars"] = pc
                break
            case '4':
                overallConstants["PercentFourStars"] = pc
                break
            case '5':
                overallConstants["PercentFiveStars"] = pc
                break
            default:
                throw new Error("Unexpected star count")
        }
        console.log(pc, starCount)
    }

    overallConstants.TotalStars = document.querySelector('[data-test="rating-count"]').innerText.split(" ")[0]
    overallConstants.TotalStarsAverage = parseFloat(document.querySelector('[data-test="rating-value"]').innerText).toFixed(1)

    let reviewList = document.querySelector('[data-test="reviews-list"]')
    const reviewTitles = Array.from(reviewList.querySelectorAll('[data-test="review-card--title"]'))


    var reviews = reviewTitles.map(
        function (title) {
            //RecommendationStatus uwu
            const recommendationElement = title.nextSibling.querySelector('[data-test="review-card--recommendation"]');
            let recommendationStatus = "";
            if (recommendationElement) {
                recommendationStatus = recommendationElement.innerText.split("\n")[1]
            }

            // ReviewValueOrQualityNum and Texts uwu
            var secondaryRatings = title.nextSibling.querySelector("div[data-test='review-card--secondary-ratings']")
            var ReviewValueOrQualityNum1 = null;
            var ReviewValueOrQualityText1 = null;
            var ReviewValueOrQualityNum2 = null;
            var ReviewValueOrQualityText2 = null;
            if (secondaryRatings) {
                secondaryRatings = Array.from(secondaryRatings.querySelectorAll(".h-sr-only"));
                var quality = secondaryRatings.filter((value, ind, _) => value.innerText.split(": ")[0] === "quality")[0];
                var value = secondaryRatings.filter((value, ind, _) => value.innerText.split(": ")[0] === "value")[0];
                if (quality) {
                    ReviewValueOrQualityNum1 = parseInt(quality.innerText.split(": ")[1].split(" ")[0]);
                    ReviewValueOrQualityText1 = "Quality";
                }
                if (value) {
                    ReviewValueOrQualityNum2 = parseInt(value.innerText.split(": ")[1].split(" ")[0]);
                    ReviewValueOrQualityText2 = "Value";
                }
            }

            return {
                ReviewHeading: title.innerText,
                ReviewBody: title.nextSibling.querySelector('[data-test="review-card--text"]').innerText,
                ReviewValueOrQualityNum1: ReviewValueOrQualityNum1,
                ReviewValueOrQualityText1: ReviewValueOrQualityText1,
                ReviewValueOrQualityNum2: ReviewValueOrQualityNum2,
                ReviewValueOrQualityText2: ReviewValueOrQualityText2,
                ReviewTime: title.nextSibling.querySelector('[data-test="review-card--reviewTime"]').innerText,
                RecommendationStatus: recommendationStatus,
            }

        }
    )

    return { reviews, overallConstants }
}
"""
        )
        log.debug(data)
        reviews, overall_constants = data["reviews"], data["overallConstants"]
        # all total values are actually the averages
        quality_filtered = list(
            filter(
                lambda review: review["ReviewValueOrQualityNum1"]
                and not math.isnan(review["ReviewValueOrQualityNum1"]),
                reviews,
            )
        )
        overall_constants["TotalQuality"] = round(
            (
                functools.reduce(
                    lambda acc, review: acc
                    + min(review["ReviewValueOrQualityNum1"], 5),
                    quality_filtered,
                    0,
                )
                / len(quality_filtered)
            ),
            2,
        )

        value_filtered = list(
            filter(
                lambda review: review["ReviewValueOrQualityNum2"]
                and not math.isnan(review["ReviewValueOrQualityNum2"]),
                reviews,
            )
        )
        overall_constants["TotalValue"] = round(
            (
                (
                    functools.reduce(
                        lambda acc, review: acc
                        + min(review["ReviewValueOrQualityNum2"], 5),
                        value_filtered,
                        0,
                    )
                )
                / len(value_filtered)
            ),
            1,
        )

        overall_constants["TotalReviews"] = len(reviews)
        overall_constants["TotalRecommendations"] = functools.reduce(
            lambda acc, review: acc + (review["RecommendationStatus"] != ""), reviews, 0
        )

        # Weird requirement for the csv columns to be in the correct order
        sortedColumns = [
            "ProductName",
            "ProductPrice",
            "ReviewHeading",
            "ReviewBody",
            "ReviewValueOrQualityNum1",
            "ReviewValueOrQualityText1",
            "ReviewValueOrQualityNum2",
            "ReviewValueOrQualityText2",
            "ReviewTime",
            "RecommendationStatus",
            "TotalQuality",
            "TotalValue",
            "TotalReviews",
            "PercentFiveStars",
            "PercentFourStars",
            "PercentThreeStars",
            "PercentTwoStars",
            "PercentOneStars",
            "TotalStars",
            "TotalStarsAverage",
            "TotalRecommendations",
        ]

        final_reviews = list(
            map(
                lambda item: dict(
                    map(
                        lambda key: (
                            key,
                            (
                                tmp.replace('"', '""')
                                if isinstance(
                                    tmp := (
                                        item.get(key) or overall_constants.get(key)
                                    ),
                                    str,
                                )
                                else tmp
                            ),
                        ),
                        sortedColumns,
                    )
                ),
                reviews,
            )
        )

        log.debug(final_reviews, len(final_reviews))
        return (
            overall_constants["ProductName"],
            final_reviews,
        )
    except Exception as e:
        log.error("Error occurred while scraping", exc_info=e)
        log.info("Could not find reviews list")
        return "", []

    finally:
        await browser.close()


def cwd():
    return Path(__file__).parent.parent


async def main():
    answers = inquirer.prompt(
        [
            inquirer.Text(
                name="product_url",
                message="Enter the product url (The URL must belong to target.com):",
                validate=lambda answers, value: (
                    True
                    if value.startswith("https://www.target.com/p/")
                    else 'The URL must start with "https://www.target.com/p/"'
                ),
                default="https://www.target.com/p/palm-leaf-beach-towel-sun-squad-8482/-/A-88638708#lnk=sametab",
            ),
            inquirer.List(
                name="output_type",
                message="Choose the output type",
                choices=["json", "csv", "both"],
                default="json",
            ),
            inquirer.Text(
                name="output_file",
                message="Enter the output file name (without extension, use '{{product_name}}' to replace with the product's name):",
                default="{{product_name}}_reviews",
            ),
        ],
    )

    iterations = 0
    responses = [
        "This is taking rather long �",
        "It's getting hot in here, no? �",
        "The wait is exhausting, isn't it? �",
        "I'm getting tired of waiting now �",
        "I'm starting to get impatient �",
        "I'm getting bored �",
        "I'm getting really bored �",
        "Ok I'm worried now �",
    ]

    async def waiting_():
        if iterations == (len(responses) * 2):
            log.error(
                "This has taken an unusual amount of time to complete. The process is being terminated. Try again later."
            )
            exit()
        log.info(responses[round(random.random() * len(responses))])
        await asyncio.sleep(30)

    waiting = asyncio.create_task(waiting_())
    waiting.add_done_callback(
        lambda _: log.info(
            "The process is taking longer than usual. Process is being ended"
        )
        and exit()
    )
    product_name, reviews = await scrape(answers["product_url"])
    waiting.cancel()

    if not reviews:
        log.error("No reviews were found for the product")
        exit()

    output_file: str = answers["output_file"].replace(
        "{product_name}", product_name.replace(" ", "_").replace("-", "_")
    )
    if not (dir := Path(cwd() / "scraped/")).exists():
        dir.mkdir()

    if answers["output_type"] == "json" or answers["output_type"] == "both":
        with open(dir / Path(f"{output_file}.json"), "w") as f:
            json.dump(reviews, f)

    if answers["output_type"] == "csv" or answers["output_type"] == "both":
        with open(dir / Path(f"{output_file}.csv"), "w") as f:
            writer = csv.DictWriter(f, fieldnames=reviews[0].keys())
            writer.writeheader()
            writer.writerows(reviews)

    exit()


if __name__ == "__main__":
    asyncio.run(main())
    log.info("Process completed successfully!")

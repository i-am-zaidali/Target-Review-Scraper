import puppeteer from "puppeteer";
import FileSystem from "fs";
import inquirer from "inquirer";

const delay = ms => new Promise(resolve => setTimeout(resolve, ms))


async function scrape(productURL) {

    const browser = await puppeteer.launch();
    const page = await browser.newPage()

    await page.goto(productURL)
    await page.waitForSelector("[data-test='product-title']")


    try {
        await page.evaluate(
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
            }
        )



        await delay(1500)

        try {
            await page.waitForSelector('[data-test="reviews-list"]')
        } catch (e) {
            console.error(e)
            console.log("Could not find reviews list")
            return { ProductName, reviews: [] }
        }

        const { reviews, overallConstants } = await page.evaluate(
            async function () {
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
                        case _:
                            throw new Error("Unexpected star count")
                    }
                    console.log(pc, starCount)
                }

                overallConstants.TotalStars = document.querySelector('[data-test="rating-count"]').innerText.split(" ")[0]
                overallConstants.TotalStarsAverage = parseInt(document.querySelector('[data-test="rating-value"]').innerText)

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

                        // var ReviewPhotos = title.nextSibling.querySelector('[data-test="review-card--photos"]')

                        return {
                            ReviewHeading: title.innerText,
                            ReviewBody: title.nextSibling.querySelector('[data-test="review-card--text"]').innerText,
                            ReviewValueOrQualityNum1: ReviewValueOrQualityNum1,
                            ReviewValueOrQualityText1: ReviewValueOrQualityText1,
                            ReviewValueOrQualityNum2: ReviewValueOrQualityNum2,
                            ReviewValueOrQualityText2: ReviewValueOrQualityText2,
                            ReviewTime: title.nextSibling.querySelector('[data-test="review-card--reviewTime"]').innerText,
                            RecommendationStatus: recommendationStatus,

                            // ReviewPhotos: ReviewPhotos ? Array.from(photos.querySelectorAll('img')).map((img) => img.src) : [],
                            // ReviewRating: parseInt(title.nextSibling.querySelector('span[data-test="ratings"]').querySelector('span').innerText[0])

                        }

                    }
                )

                return { reviews, overallConstants }
            }
        )
        // all total values are actually the averages
        var qualityFiltered = reviews.filter(review => review.ReviewValueOrQualityNum1 !== null && !isNaN(review.ReviewValueOrQualityNum1))
        overallConstants.TotalQuality = ((qualityFiltered.reduce((acc, review) => acc + Math.min(review.ReviewValueOrQualityNum1, 5), 0)) / qualityFiltered.length).toFixed(1);

        var valueFiltered = reviews.filter(review => review.ReviewValueOrQualityNum2 !== null && !isNaN(review.ReviewValueOrQualityNum2))
        overallConstants.TotalValue = ((valueFiltered.reduce((acc, review) => acc + Math.min(review.ReviewValueOrQualityNum2, 5), 0)) / valueFiltered.length).toFixed(1);

        overallConstants.TotalReviews = reviews.length
        overallConstants.TotalRecommendations = reviews.reduce((acc, review) => acc + (review.RecommendationStatus !== ""), 0)

        // Weird requirement for the csv columns to be in the correct order
        var sortedColumns = ["ProductName", "ProductPrice", "ReviewHeading", "ReviewBody", "ReviewValueOrQualityNum1", "ReviewValueOrQualityText1", "ReviewValueOrQualityNum2", "ReviewValueOrQualityText2", "ReviewTime", "RecommendationStatus", "TotalQuality", "TotalValue", "TotalReviews", "PercentFiveStars", "PercentFourStars", "PercentThreeStars", "PercentTwoStars", "PercentOneStars", "TotalStars", "TotalStarsAverage", "TotalRecommendations"]

        const finalReviews = reviews.map(
            (item) => {
                let tmp;
                return Object.fromEntries(sortedColumns.map((key) => [key, (typeof (tmp = (item[key] ?? overallConstants[key])) === "string" ? tmp.replaceAll('"', '""') : tmp)]));
            }
        );


        console.log(finalReviews, finalReviews.length)
        return { ProductName: overallConstants.ProductName, reviews: finalReviews }
    } catch (e) {
        console.error(e)
        console.log("Could not find reviews list")
        return { ProductName: "", reviews: [] }
    }
}


inquirer.prompt(
    [{
        type: 'input',
        name: 'productURL',
        message: 'Enter the product url (The URL must belong to target.com):',
        validate: (value, answers) => value.startsWith('https://www.target.com/p/') ? true : 'The URL must start with "https://www.target.com/p/"',
    },
    {
        type: 'list',
        name: 'outputType',
        message: 'Choose the output type',
        choices: ['json', 'csv', 'both'],
        default: 'json',
    },
    {
        type: 'input',
        name: 'outputFile',
        message: 'Enter the output file name (without extension, use "{productName}" to replace with the product\'s name):',
        default: '{ProductName}_reviews',
    }
    ],
).then(
    async (answers) => {
        let iterations = 0;
        let responses = ["This is taking rather long �", "It's getting hot in here, no? �", "The wait is exhausting, isn't it? �", "I'm getting tired of waiting now �", "I'm starting to get impatient �", "I'm getting bored �", "I'm getting really bored �", "Ok I'm worried now �"]
        var waiting = setInterval(() => {
            if (iterations === (responses.length * 2)) {
                console.error("This has taken an unusual amount of time to complete. The process is being terminated. Try again later.")
                process.exit()
            }
            console.log(responses[Math.round(Math.random() * responses.length)])
        }, 30000)
        scrape(answers.productURL).then(
            async ({ ProductName, reviews }) => {
                clearInterval(waiting)
                const outputFile = answers.outputFile.replace('{ProductName}', ProductName.replaceAll(' ', '_').replaceAll('-', '_'))
                if (!FileSystem.existsSync('scraped')) {
                    FileSystem.mkdirSync('scraped')
                }
                if (answers.outputType === 'json' || answers.outputType === 'both') {
                    FileSystem.writeFileSync(`scraped/${outputFile}.json`, JSON.stringify(reviews, null, 4))
                }
                if (answers.outputType === 'csv' || answers.outputType === 'both') {
                    const csv = '"' + Object.keys(reviews[0]).join('","') + '"\n"' + reviews.map((review) => Object.values(review).join('","')).join('"\n"') + '"'
                    FileSystem.writeFileSync(`scraped/${outputFile}.csv`, csv)
                }
                process.exit()
            }
        )
    }
)

"use strict";

$(document).ready(() => {
    const cookie = parseCookie(document.cookie);
    const countryCode = cookie["countryCode"] || "us";

    getMoviesFromAllServices(countryCode);

    $(".section-service__div-movies").on(
        "click",
        "div:has(> .bi-arrow-left), div:has(> .bi-arrow-right)",
        { countryCode },
        handleServiceMoviesPageChange
    );
});

// ==================================================

/**
 * Gets all the first page of movies for all streaming services on the homepage.
 *
 * @param {String} countryCode The user's country's 2-letter code.
 */
async function getMoviesFromAllServices(countryCode) {
    const $servicesMoviesLists = $(".section-service__div-movies");

    await $servicesMoviesLists.each(async function (index, element) {
        const serviceId = element.dataset.service;

        const moviePageData = await getPageOfMoviesFromService(countryCode, serviceId);

        let movieIds;
        let moviePosterData;
        if (moviePageData) {
            movieIds = moviePageData.items.reduce((arr, currentItem) => {
                arr.push(currentItem.movie_id);
                return arr;
            }, []);

            moviePosterData = await getMoviePosters(movieIds, ["verticalPoster"], ["w240"]);
        }

        buildMoviesDiv(element, moviePageData, moviePosterData);
    });
}

/**
 * Retrieves a page of movies for a specified streaming service, along with other page-related data.
 *
 * @param {String} countryCode The country's 2-letter code.
 * @param {String} serviceId Streaming service ID.
 * @param {Number} page The page for movies results or undefined.
 * @returns An Object {StreamingOption[] items, Number page, Boolean has_prev, Boolean has_next}.
 */
async function getPageOfMoviesFromService(countryCode, serviceId, page) {
    const url = `/api/v1/${countryCode}/${serviceId}/movies`;

    let response;
    try {
        response = await axios.get(url, { params: { page: page } });
    } catch (error) {
        logAxiosError(error);
        return;
    }

    const data = response.data;
    // Converting the nested Array of items from Strings to Objects, because Axios doesn't convert them.
    data["items"] = data["items"].reduce((arr, currentItem) => {
        arr.push(JSON.parse(currentItem));
        return arr;
    }, []);

    return data;
}

/**
 * Creates and inserts the HTML elements, for a service's list of movies, into a provided div element.  If the data
 * for the page of movies (moviePageData) is falsy, such as when there is a network issue when retrieving the data, the
 * text "error" is displayed instead of movies.
 *
 * @param {Element} element The HTML div element that contains the list of movies.
 * @param {Object} moviePageData An Object {StreamingOption[] items, Number page, Boolean has_prev, Boolean has_next}.
 * @param {Object} moviePosterData An Object {movie_id: {type: {size: link}}} or an empty Object.
 */
function buildMoviesDiv(element, moviePageData, moviePosterData) {
    const $serviceMoviesUlElement = $(element).find(".section-service__list-movies");
    $serviceMoviesUlElement.empty();

    if (moviePageData) {
        $(element).attr("data-page", moviePageData["page"]);

        if (moviePageData["has_prev"]) {
            $(element).find(".bi-arrow-left").removeClass("bi-arrow--hidden");
        } else {
            $(element).find(".bi-arrow-left").addClass("bi-arrow--hidden");
        }

        if (moviePageData["has_next"]) {
            $(element).find(".bi-arrow-right").removeClass("bi-arrow--hidden");
        } else {
            $(element).find(".bi-arrow-right").addClass("bi-arrow--hidden");
        }

        if (moviePageData.items.length === 0) {
            $serviceMoviesUlElement.append(
                `<li class="col">
                    <p class="p-5 m-0">No movies found</p>
                </li>`
            );
        } else {
            moviePageData.items.forEach((streamingOption) => {
                $serviceMoviesUlElement.append(
                    `<li class="col p-0 m-3">
                        <a href="movie/${streamingOption["movie_id"]}">
                            <img
                            src="${
                                moviePosterData?.[streamingOption["movie_id"]]?.["verticalPoster"]?.[
                                    "w240"
                                ] ?? "data:" // supposedly good for no src
                            }"
                            alt="Movie ${streamingOption["movie_id"]}"
                            width="240" height="320" />
                        </a>
                    </li>`
                );
            });
        }
    } else {
        $serviceMoviesUlElement.append("<li>Error</li>");
    }
}

/**
 * Loads the previous or next page of movies for a streaming service's list on the homepage.
 *
 * @param {Event} event The Event for clicking on an arrow in a streaming service's list of movies.
 */
async function handleServiceMoviesPageChange(event) {
    const delegateTarget = event.delegateTarget;
    const arrowButton = event.currentTarget;
    const currentPage = parseInt(delegateTarget.dataset.page);
    const serviceId = delegateTarget.dataset.service;
    const countryCode = event.data.countryCode;

    let pageToLoad;
    if (arrowButton.querySelector(".bi-arrow-left")) {
        pageToLoad = currentPage - 1;
    } else if (arrowButton.querySelector(".bi-arrow-right")) {
        pageToLoad = currentPage + 1;
    }

    const moviePageData = await getPageOfMoviesFromService(countryCode, serviceId, pageToLoad);

    let movieIds;
    let moviePosterData;
    if (moviePageData) {
        movieIds = moviePageData.items.reduce((arr, currentItem) => {
            arr.push(currentItem.movie_id);
            return arr;
        }, []);

        moviePosterData = await getMoviePosters(movieIds, ["verticalPoster"], ["w240"]);
    }

    buildMoviesDiv(delegateTarget, moviePageData, moviePosterData);
}

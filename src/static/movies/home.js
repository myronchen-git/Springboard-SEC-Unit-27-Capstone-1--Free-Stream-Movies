"use strict";

$(document).ready(() => {
    const cookie = parseCookie(document.cookie);
    getMoviesFromAllServices(cookie["countryCode"] || "us");
});

// ==================================================

/**
 * Gets all the first page of movies for all streaming services on the homepage.
 *
 * @param {String} countryCode The user's country's 2-letter code.
 */
async function getMoviesFromAllServices(countryCode) {
    const $servicesMoviesLists = $(".section-service__div-movies");

    $servicesMoviesLists.each(async function (index, element) {
        const serviceId = element.dataset.service;
        const moviePageData = await getPageOfMoviesFromService(countryCode, serviceId);
        buildMoviesDiv(element, moviePageData);
    });
}

/**
 * Retrieves a page of movies for a specified streaming service, along with other page-related data.
 *
 * @param {String} countryCode The country's 2-letter code.
 * @param {String} serviceId Streaming service ID.
 * @param {Number} page The page for movies results.
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
 */
function buildMoviesDiv(element, moviePageData) {
    const $serviceMoviesUlElement = $(element).children(".section-service__list-movies");
    $serviceMoviesUlElement.empty();

    if (moviePageData) {
        $(element).data("page", moviePageData["page"]);

        if (moviePageData["has_prev"]) {
            $(element).children(".bi-arrow-left-circle-fill").removeClass("bi-arrow--hidden");
        } else {
            $(element).children(".bi-arrow-left-circle-fill").addClass("bi-arrow--hidden");
        }

        if (moviePageData["has_next"]) {
            $(element).children(".bi-arrow-right-circle-fill").removeClass("bi-arrow--hidden");
        } else {
            $(element).children(".bi-arrow-right-circle-fill").addClass("bi-arrow--hidden");
        }

        if (moviePageData.items.length === 0) {
            $serviceMoviesUlElement.append("<li>No movies found</li>");
        } else {
            moviePageData.items.forEach((streamingOption) => {
                $serviceMoviesUlElement.append(
                    `<li><a href="${streamingOption["link"]}">${streamingOption["movie_id"]}</a></li>`
                );
            });
        }
    } else {
        $serviceMoviesUlElement.append("<li>Error</li>");
    }
}

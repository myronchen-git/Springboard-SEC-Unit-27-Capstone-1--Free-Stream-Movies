describe("getMoviesFromAllServices", () => {
    beforeEach(() => {
        this.origMoviePageData = { items: [{ movie_id: "1" }] };
        this.moviePageData = JSON.parse(JSON.stringify(this.origMoviePageData));

        // get array of IDs from moviePageData to simplify assertions
        this.moviePageDataIds = Object.freeze(
            this.moviePageData.items.reduce((arr, streamingOption) => {
                arr.push(streamingOption.movie_id);
                return arr;
            }, [])
        );

        this.buildMoviesDivSpy = spyOn(window, "buildMoviesDiv");

        this.origMoviePosterData = { movie_id: { verticalPoster: { w240: "example.com" } } };
        window.getMoviePosters = jasmine
            .createSpy("getMoviePostersSpy")
            .and.returnValue(JSON.parse(JSON.stringify(this.origMoviePosterData)));
    });

    afterEach(() => {
        $("#testarea").empty();
    });

    it(
        "should not call getPageOfMoviesFromService, getMoviePosters, or buildMoviesDiv " +
            "when there are no streaming services.",
        async () => {
            // Arrange
            const countryCode = "us";

            const getPageOfMoviesFromServiceSpy = spyOn(window, "getPageOfMoviesFromService");

            // Act
            await getMoviesFromAllServices(countryCode);

            // Assert
            expect(getPageOfMoviesFromServiceSpy).not.toHaveBeenCalled();
            expect(window.getMoviePosters).not.toHaveBeenCalled();
            expect(this.buildMoviesDivSpy).not.toHaveBeenCalled();
        }
    );

    it(
        "should call getPageOfMoviesFromService to get data " +
            "and pass that data to buildMoviesDiv " +
            "for one service.",
        async () => {
            // Arrange
            const countryCode = "us";
            const serviceIds = ["plutotv"];
            const elements = [createTestDivHelper(serviceIds[0])[0]];
            $("#testarea").append(...elements);

            const getPageOfMoviesFromServiceSpy = spyOn(window, "getPageOfMoviesFromService").and.returnValue(
                this.moviePageData
            );

            // Act
            await getMoviesFromAllServices(countryCode);

            // Assert
            expect(getPageOfMoviesFromServiceSpy).toHaveBeenCalledTimes(serviceIds.length);
            expect(getPageOfMoviesFromServiceSpy).toHaveBeenCalledWith(countryCode, serviceIds[0]);

            expect(window.getMoviePosters).toHaveBeenCalledWith(
                this.moviePageDataIds,
                jasmine.arrayContaining([]),
                jasmine.arrayContaining([])
            );

            expect(this.buildMoviesDivSpy).toHaveBeenCalledTimes(serviceIds.length);
            expect(this.buildMoviesDivSpy).toHaveBeenCalledWith(
                elements[0],
                this.origMoviePageData,
                this.origMoviePosterData
            );
        }
    );

    it(
        "should call getPageOfMoviesFromService to get data " +
            "and pass that data to buildMoviesDiv for each service.",
        async () => {
            // Arrange
            const countryCode = "us";
            const serviceIds = ["plutotv", "tubi"];
            const elements = [createTestDivHelper(serviceIds[0])[0], createTestDivHelper(serviceIds[1])[0]];
            $("#testarea").append(...elements);

            const getPageOfMoviesFromServiceSpy = spyOn(window, "getPageOfMoviesFromService").and.returnValue(
                this.moviePageData
            );

            // Act
            await getMoviesFromAllServices(countryCode);

            // Assert
            expect(getPageOfMoviesFromServiceSpy).toHaveBeenCalledTimes(serviceIds.length);
            expect(getPageOfMoviesFromServiceSpy).toHaveBeenCalledWith(countryCode, serviceIds[0]);
            expect(getPageOfMoviesFromServiceSpy).toHaveBeenCalledWith(countryCode, serviceIds[1]);

            expect(window.getMoviePosters).toHaveBeenCalledWith(
                this.moviePageDataIds,
                jasmine.arrayContaining([]),
                jasmine.arrayContaining([])
            );

            expect(this.buildMoviesDivSpy).toHaveBeenCalledTimes(serviceIds.length);
            expect(this.buildMoviesDivSpy).toHaveBeenCalledWith(
                elements[0],
                this.origMoviePageData,
                this.origMoviePosterData
            );
            expect(this.buildMoviesDivSpy).toHaveBeenCalledWith(
                elements[1],
                this.origMoviePageData,
                this.origMoviePosterData
            );
        }
    );

    it(
        "should call getPageOfMoviesFromService to get undefined " +
            "and pass undefined to buildMoviesDiv for each service, " +
            "for the case when getPageOfMoviesFromService has network issues.",
        async () => {
            // Arrange
            const countryCode = "us";
            const serviceIds = ["plutotv", "tubi"];
            const elements = [createTestDivHelper(serviceIds[0])[0], createTestDivHelper(serviceIds[1])[0]];
            $("#testarea").append(...elements);

            const getPageOfMoviesFromServiceSpy = spyOn(window, "getPageOfMoviesFromService");

            // Act
            await getMoviesFromAllServices(countryCode);

            // Assert
            expect(getPageOfMoviesFromServiceSpy).toHaveBeenCalledTimes(serviceIds.length);
            expect(getPageOfMoviesFromServiceSpy).toHaveBeenCalledWith(countryCode, serviceIds[0]);
            expect(getPageOfMoviesFromServiceSpy).toHaveBeenCalledWith(countryCode, serviceIds[1]);

            expect(window.getMoviePosters).not.toHaveBeenCalled();

            expect(this.buildMoviesDivSpy).toHaveBeenCalledTimes(serviceIds.length);
            expect(this.buildMoviesDivSpy).toHaveBeenCalledWith(elements[0], undefined, undefined);
            expect(this.buildMoviesDivSpy).toHaveBeenCalledWith(elements[1], undefined, undefined);
        }
    );
});

describe("getPageOfMoviesFromService", () => {
    afterEach(() => {
        $("#testarea").empty();
    });

    it(
        "should return a data Object with no items when " +
            "there are no free movies from a streaming service.",
        async () => {
            // Arrange
            const countryCode = "us";
            const serviceId = "tubi";

            const responseData = {
                data: { items: [], page: 1, has_prev: false, has_next: false },
            };
            const expectedData = JSON.parse(JSON.stringify(responseData["data"]));

            const getSpy = spyOn(axios, "get").and.returnValue(responseData);

            // Act
            const result = await getPageOfMoviesFromService(countryCode, serviceId);

            // Assert
            expect(result).toEqual(expectedData);
            expect(getSpy).toHaveBeenCalledOnceWith(`/api/v1/${countryCode}/${serviceId}/movies`, {
                params: { page: undefined },
            });
        }
    );

    it(
        "should return a data Object with one item when " +
            "there is one free movie from a streaming service.",
        async () => {
            // Arrange
            const countryCode = "us";
            const serviceId = "tubi";

            const items = [Object.freeze({ id: 1 })];
            const responseData = {
                data: {
                    items: [JSON.stringify(items[0])],
                    page: 1,
                    has_prev: false,
                    has_next: false,
                },
            };
            // making a copy
            const expectedData = JSON.parse(JSON.stringify(responseData["data"]));
            expectedData["items"] = items;

            const getSpy = spyOn(axios, "get").and.returnValue(responseData);

            // Act
            const result = await getPageOfMoviesFromService(countryCode, serviceId);

            // Assert
            expect(result).toEqual(expectedData);
            expect(getSpy).toHaveBeenCalledOnceWith(`/api/v1/${countryCode}/${serviceId}/movies`, {
                params: { page: undefined },
            });
        }
    );

    it("should return a data Object with items when there are free movies from a streaming service.", async () => {
        // Arrange
        const countryCode = "us";
        const serviceId = "tubi";

        const items = [Object.freeze({ id: 1 }), Object.freeze({ id: 2 })];
        const responseData = {
            data: {
                items: [JSON.stringify(items[0]), JSON.stringify(items[1])],
                page: 1,
                has_prev: false,
                has_next: true,
            },
        };
        // making a copy
        const expectedData = JSON.parse(JSON.stringify(responseData["data"]));
        expectedData["items"] = items;

        const getSpy = spyOn(axios, "get").and.returnValue(responseData);

        // Act
        const result = await getPageOfMoviesFromService(countryCode, serviceId);

        // Assert
        expect(result).toEqual(expectedData);
        expect(getSpy).toHaveBeenCalledOnceWith(`/api/v1/${countryCode}/${serviceId}/movies`, {
            params: { page: undefined },
        });
    });

    it("should call the app's API with a page query parameter when passing in a page argument.", async () => {
        // Arrange
        const countryCode = "us";
        const serviceId = "tubi";
        const page = 2;

        const items = [Object.freeze({ id: 1 })];
        const responseData = {
            data: {
                items: [JSON.stringify(items[0])],
                page: 2,
                has_prev: true,
                has_next: false,
            },
        };
        // making a copy
        const expectedData = JSON.parse(JSON.stringify(responseData["data"]));
        expectedData["items"] = items;

        const getSpy = spyOn(axios, "get").and.returnValue(responseData);

        // Act
        const result = await getPageOfMoviesFromService(countryCode, serviceId, page);

        // Assert
        expect(result).toEqual(expectedData);
        expect(getSpy).toHaveBeenCalledOnceWith(`/api/v1/${countryCode}/${serviceId}/movies`, {
            params: { page: page },
        });
    });

    it("should return undefined when the GET request has failed.", async () => {
        // Arrange
        const countryCode = "us";
        const serviceId = "tubi";

        const getSpy = spyOn(axios, "get").and.throwError(new Error());

        // Act
        const result = await getPageOfMoviesFromService(countryCode, serviceId);

        // Assert
        expect(result).nothing();
    });
});

describe("buildMoviesDiv", () => {
    beforeAll(() => {
        this.items = Object.freeze([
            Object.freeze({ id: 1, movie_id: 1, link: "http://www.example.com/1" }),
            Object.freeze({ id: 2, movie_id: 2, link: "http://www.example.com/2" }),
        ]);

        this.expectedMoviePosterLinks = Object.freeze([
            "http://www.example.com/1/poster",
            "http://www.example.com/2/poster",
        ]);

        this.moviePosterData = {};
        this.moviePosterData[this.items[0].id] = {
            verticalPoster: { w240: this.expectedMoviePosterLinks[0] },
        };
        this.moviePosterData[this.items[1].id] = {
            verticalPoster: { w240: this.expectedMoviePosterLinks[1] },
        };
    });

    it("should build the elements for the first page and when there is no next page.", () => {
        // Arrange
        const element = createTestDivHelper("tubi")[0];

        const moviePageData = Object.freeze({
            items: this.items,
            page: 1,
            has_prev: false,
            has_next: false,
        });

        // Act
        buildMoviesDiv(element, moviePageData, this.moviePosterData);

        // Assert
        const page = parseInt($(element).attr("data-page"));
        expect(page).toBe(moviePageData["page"]);
        expect($(element).find(".bi-arrow-left").hasClass("bi-arrow--hidden")).toBeTrue();
        expect($(element).find(".bi-arrow-right").hasClass("bi-arrow--hidden")).toBeTrue();

        const liElements = $(element).find(".section-service__list-movies > li");
        expect(liElements.length).toBe(this.items.length);

        const links = liElements.find("a");
        expect(links[0].href).toContain(`movie/${this.items[0].movie_id}`);
        expect(links[1].href).toContain(`movie/${this.items[1].movie_id}`);

        const imgs = liElements.find("img");
        expect(imgs[0].src).toBe(this.expectedMoviePosterLinks[0]);
        expect(imgs[1].src).toBe(this.expectedMoviePosterLinks[1]);
    });

    it("should build the elements for the second page and when there is no next page.", () => {
        // Arrange
        const element = createTestDivHelper("tubi")[0];

        const moviePageData = Object.freeze({
            items: this.items,
            page: 2,
            has_prev: true,
            has_next: false,
        });

        // Act
        buildMoviesDiv(element, moviePageData, this.moviePosterData);

        // Assert
        const page = parseInt($(element).attr("data-page"));
        expect(page).toBe(moviePageData["page"]);
        expect($(element).find(".bi-arrow-left").hasClass("bi-arrow--hidden")).toBeFalse();
        expect($(element).find(".bi-arrow-right").hasClass("bi-arrow--hidden")).toBeTrue();

        const liElements = $(element).find(".section-service__list-movies > li");
        expect(liElements.length).toBe(this.items.length);

        const links = liElements.find("a");
        expect(links[0].href).toContain(`movie/${this.items[0].movie_id}`);
        expect(links[1].href).toContain(`movie/${this.items[1].movie_id}`);

        const imgs = liElements.find("img");
        expect(imgs[0].src).toBe(this.expectedMoviePosterLinks[0]);
        expect(imgs[1].src).toBe(this.expectedMoviePosterLinks[1]);
    });

    it("should build the correct arrows when there is only a prev page.", () => {
        // Arrange
        const element = createTestDivHelper("tubi")[0];

        const moviePageData = Object.freeze({
            items: this.items,
            page: 2,
            has_prev: true,
            has_next: false,
        });

        // Act
        buildMoviesDiv(element, moviePageData, this.moviePosterData);

        // Assert
        expect($(element).find(".bi-arrow-left").hasClass("bi-arrow--hidden")).toBeFalse();
        expect($(element).find(".bi-arrow-right").hasClass("bi-arrow--hidden")).toBeTrue();
    });

    it("should build the correct arrows when there is only a next page.", () => {
        // Arrange
        const element = createTestDivHelper("tubi")[0];

        const moviePageData = Object.freeze({
            items: this.items,
            page: 1,
            has_prev: false,
            has_next: true,
        });

        // Act
        buildMoviesDiv(element, moviePageData, this.moviePosterData);

        // Assert
        expect($(element).find(".bi-arrow-left").hasClass("bi-arrow--hidden")).toBeTrue();
        expect($(element).find(".bi-arrow-right").hasClass("bi-arrow--hidden")).toBeFalse();
    });

    it("should build the correct arrows when there is a prev and next page.", () => {
        // Arrange
        const element = createTestDivHelper("tubi")[0];

        const moviePageData = Object.freeze({
            items: this.items,
            page: 2,
            has_prev: true,
            has_next: true,
        });

        // Act
        buildMoviesDiv(element, moviePageData, this.moviePosterData);

        // Assert
        expect($(element).find(".bi-arrow-left").hasClass("bi-arrow--hidden")).toBeFalse();
        expect($(element).find(".bi-arrow-right").hasClass("bi-arrow--hidden")).toBeFalse();
    });

    it("should display no movies when movie page data contains no movies.", () => {
        // Arrange
        const element = createTestDivHelper("tubi")[0];

        const moviePageData = Object.freeze({
            items: [],
            page: 1,
            has_prev: false,
            has_next: false,
        });

        const moviePosterData = {};

        // Act
        buildMoviesDiv(element, moviePageData, moviePosterData);

        // Assert
        const page = parseInt($(element).attr("data-page"));
        expect(page).toBe(moviePageData["page"]);
        expect($(element).find(".bi-arrow-left").hasClass("bi-arrow--hidden")).toBeTrue();
        expect($(element).find(".bi-arrow-right").hasClass("bi-arrow--hidden")).toBeTrue();

        expect($(element).text()).toContain("No movies found");
    });

    it(
        "should display an error message if there is a connection issue " +
            "when retrieving moviePageData; moviePageData is undefined.",
        () => {
            // Arrange
            const element = createTestDivHelper("tubi")[0];

            // Act
            buildMoviesDiv(element);

            // Assert
            expect($(element).text()).toContain("Error");
        }
    );

    it("should not have any movie poster src links if there are no movie posters for movies.", () => {
        // Arrange
        const element = createTestDivHelper("tubi")[0];

        const moviePageData = Object.freeze({
            items: this.items,
            page: 1,
            has_prev: false,
            has_next: false,
        });

        const moviePosterData = {};

        // Act
        buildMoviesDiv(element, moviePageData, moviePosterData);

        // Assert
        const liElements = $(element).find(".section-service__list-movies > li");
        const imgs = liElements.find("img");
        expect(imgs[0].src).toBe("data:");
        expect(imgs[0].alt).toBe(`Movie ${this.items[0].movie_id}`);
        expect(imgs[1].src).toBe("data:");
        expect(imgs[1].alt).toBe(`Movie ${this.items[1].movie_id}`);
    });

    it(
        "should not have any movie poster src links if there is a connection issue " +
            "when retrieving moviePosterData; moviePosterData is undefined",
        () => {
            // Arrange
            const element = createTestDivHelper("tubi")[0];

            const moviePageData = Object.freeze({
                items: this.items,
                page: 1,
                has_prev: false,
                has_next: false,
            });

            const moviePosterData = undefined;

            // Act
            buildMoviesDiv(element, moviePageData, moviePosterData);

            // Assert
            const liElements = $(element).find(".section-service__list-movies > li");
            const imgs = liElements.find("img");
            expect(imgs[0].src).toBe("data:");
            expect(imgs[0].alt).toBe(`Movie ${this.items[0].movie_id}`);
            expect(imgs[1].src).toBe("data:");
            expect(imgs[1].alt).toBe(`Movie ${this.items[1].movie_id}`);
        }
    );
});

describe("handleServiceMoviesPageChange", () => {
    beforeEach(() => {
        this.origMoviePageData = { items: [{ movie_id: "1" }] };
        this.moviePageData = JSON.parse(JSON.stringify(this.origMoviePageData));

        // get array of IDs from moviePageData to simplify assertions
        this.moviePageDataIds = Object.freeze(
            this.moviePageData.items.reduce((arr, streamingOption) => {
                arr.push(streamingOption.movie_id);
                return arr;
            }, [])
        );

        this.getPageOfMoviesFromServiceSpy = spyOn(window, "getPageOfMoviesFromService").and.returnValue(
            this.moviePageData
        );
        this.buildMoviesDivSpy = spyOn(window, "buildMoviesDiv");

        this.origMoviePosterData = { movie_id: { verticalPoster: { w240: "example.com" } } };
        window.getMoviePosters = jasmine
            .createSpy("getMoviePostersSpy")
            .and.returnValue(JSON.parse(JSON.stringify(this.origMoviePosterData)));
    });

    it("should load the previous page when the event contains the left arrow.", async () => {
        // Arrange
        const countryCode = "us";
        const serviceId = "tubi";
        const page = 9;
        const expectedPageToLoad = page - 1;

        const moviesListDiv = $("<div>").attr("data-service", serviceId).attr("data-page", page)[0];
        const arrowButtonContainer = $("<div>").append($("<i>").addClass("bi-arrow-left"))[0];

        const event = jQuery.Event("click", {
            delegateTarget: moviesListDiv,
            target: arrowButtonContainer,
            data: { countryCode },
        });

        // Act
        await handleServiceMoviesPageChange(event);

        // Assert
        expect(this.getPageOfMoviesFromServiceSpy).toHaveBeenCalledWith(
            countryCode,
            serviceId,
            expectedPageToLoad
        );

        expect(window.getMoviePosters).toHaveBeenCalledWith(
            this.moviePageDataIds,
            jasmine.arrayContaining([]),
            jasmine.arrayContaining([])
        );

        expect(this.buildMoviesDivSpy).toHaveBeenCalledWith(
            moviesListDiv,
            this.origMoviePageData,
            this.origMoviePosterData
        );
    });

    it("should load the next page when the event contains the right arrow.", async () => {
        // Arrange
        const countryCode = "us";
        const serviceId = "tubi";
        const page = 9;
        const expectedPageToLoad = page + 1;

        const moviesListDiv = $("<div>").attr("data-service", serviceId).attr("data-page", page)[0];
        const arrowButtonContainer = $("<div>").append($("<i>").addClass("bi-arrow-right"))[0];

        const event = jQuery.Event("click", {
            delegateTarget: moviesListDiv,
            target: arrowButtonContainer,
            data: { countryCode },
        });

        // Act
        await handleServiceMoviesPageChange(event);

        // Assert
        expect(this.getPageOfMoviesFromServiceSpy).toHaveBeenCalledWith(
            countryCode,
            serviceId,
            expectedPageToLoad
        );

        expect(window.getMoviePosters).toHaveBeenCalledWith(
            this.moviePageDataIds,
            jasmine.arrayContaining([]),
            jasmine.arrayContaining([])
        );

        expect(this.buildMoviesDivSpy).toHaveBeenCalledWith(
            moviesListDiv,
            this.origMoviePageData,
            this.origMoviePosterData
        );
    });
});

// ==================================================

/**
 * Creates the div HTML element with class "section-service__div-movies".
 * This needs to be manually updated when there are changes to HTML!
 *
 * @param {String} serviceId Streaming service ID.
 * @returns A JQuery Object.
 */
function createTestDivHelper(serviceId) {
    return $(`
        <div class="section-service__div-movies card-body container" data-service="${serviceId}">
            <div class="row">
                <div class="col-auto p-0">
                    <i class="bi bi-arrow-left p-2 bi-arrow--hidden"></i>
                </div>
                <div class="col container text-center">
                    <ul class="section-service__list-movies row m-0 list-unstyled">
                        <li class="col">
                            <p class="p-5 m-0">Loading Movies...</p>
                        </li>
                    </ul>
                </div>
                <div class="col-auto p-0">
                    <i class="bi bi-arrow-right p-2 bi-arrow--hidden"></i>
                </div>
            </div>
        </div>
    `);
}

describe("getMoviePosters", () => {
    it("should call the route with parameters and return the response data.", async () => {
        // Arrange
        const movieIds = ["1", "2"];
        const types = ["verticalPoster"];
        const sizes = ["w240", "w360"];

        const data = "some data";
        const responseData = { data };
        const getSpy = spyOn(axios, "get").and.returnValue(responseData);

        // Act
        const result = await getMoviePosters([...movieIds], [...types], [...sizes]);

        // Assert
        expect(result).toEqual(data);

        expect(getSpy).toHaveBeenCalledOnceWith("/api/v1/movie-posters", {
            params: { movieId: movieIds, type: types, size: sizes },
            paramsSerializer: { indexes: null },
        });
    });

    it("should return an empty Object if an error occurs from the HTTP request.", async () => {
        // Arrange
        const movieIds = ["1", "2"];
        const types = ["verticalPoster"];
        const sizes = ["w240", "w360"];

        const getSpy = spyOn(axios, "get").and.throwError(new Error());

        // Act
        const result = await getMoviePosters(movieIds, types, sizes);

        // Assert
        expect(result).toEqual({});

        expect(getSpy).toHaveBeenCalledOnceWith("/api/v1/movie-posters", {
            params: { movieId: movieIds, type: types, size: sizes },
            paramsSerializer: { indexes: null },
        });
    });
});

"use strict";

/**
 * Gets movie poster image links from app API.
 *
 * @param {String[]} movieIds An array of movie IDs to look for.
 * @param {String[]} types An array of types to look for.
 * @param {String[]} sizes An array of sizes to look for.
 * @returns An Object containing movie poster links: {movie_id: {type: {size: link}}}
 * or an empty Object if there is an error with the GET request.
 */
async function getMoviePosters(movieIds, types, sizes) {
    const url = "/api/v1/movie-posters";

    let response;
    try {
        response = await axios.get(url, {
            params: { movieId: movieIds, type: types, size: sizes },
            paramsSerializer: { indexes: null },
        });
    } catch (error) {
        logAxiosError(error);
        return {};
    }

    return response.data;
}

"use strict";

/**
 * Helps display the error in the API response.
 *
 * @param {Error} error
 */
function logAxiosError(error) {
    if (error.response) {
        const responseObject = error.response;
        console.log(
            `status: ${responseObject.status}\n${responseObject.data?.message || responseObject.statusText}`
        );
    } else if (error.request) {
        console.log("Did not receive a response from the server.");
    } else {
        console.log("Error occurred while setting up request.");
    }
}

/**
 * Converts a HTTP cookie from String to Object.  Does not parse the value.
 * https://www.30secondsofcode.org/js/s/parse-or-serialize-cookie/
 *
 * @param {String} cookie The raw cookie String stored in the browser.
 * @returns A cookie in Object form.
 */
function parseCookie(cookie) {
    if (cookie) {
        return cookie
            .split(";")
            .map((keyValueString) => keyValueString.split("="))
            .reduce((obj, keyValue) => {
                obj[decodeURIComponent(keyValue[0].trim())] = decodeURIComponent(keyValue[1].trim());
                return obj;
            }, {});
    } else {
        return {};
    }
}

/**
 * Converts a key-value pair into a String to use as a HTTP cookie.  If name or val is falsy, returns an empty String.
 * Cookie will also have Max-Age and Path attributes.  Path is set to root directory.
 * https://www.30secondsofcode.org/js/s/parse-or-serialize-cookie/
 *
 * @param {String} name The name of the piece of data.
 * @param {String} val The value for the piece of data.
 * @param {Number} maxAge The number of seconds before the cookie expires.  Default is 1 year.
 * @returns A cookie String or an empty String.
 */
function serializeCookie(name, val, maxAge = 31557600) {
    return name && val
        ? `${encodeURIComponent(name)}=${encodeURIComponent(val)}; Max-Age=${maxAge}; Path=/`
        : "";
}

describe("parseCookie", () => {
    it("should return an empty Object when there are no cookies.", () => {
        // Arrange
        const cookieString = "";

        // Act
        result = parseCookie(cookieString);

        // Assert
        expect(result).toEqual({});
    });

    it("should return an Object with one property when there is only one cookie.", () => {
        // Arrange
        const cookieString = "country_code = us";

        // Act
        result = parseCookie(cookieString);

        // Assert
        expect(result).toEqual({ country_code: "us" });
    });

    it("should return an Object with multiple properties when there are multiple cookies.", () => {
        // Arrange
        const cookieString = "country_code = us; theme = dark";

        // Act
        result = parseCookie(cookieString);

        // Assert
        expect(result).toEqual({ country_code: "us", theme: "dark" });
    });

    it("should decode encoded URI text.", () => {
        // Arrange
        const cookieString = "smiley%E2%98%BA = m%3At";

        // Act
        result = parseCookie(cookieString);

        // Assert
        expect(result).toEqual({ "smiley☺": "m:t" });
    });

    it("should not parse the value.", () => {
        // Arrange
        const arrayString = JSON.stringify([1, 2]);
        const cookieString = `items = ${encodeURIComponent(arrayString)}`;

        // Act
        result = parseCookie(cookieString);

        // Assert
        expect(result).toEqual({ items: arrayString });
    });
});

describe("serializeCookie", () => {
    it("should return a URI-safe String, ready to be stored into a HTTP cookie.", () => {
        // Arrange
        const name = "country_code";
        const val = "us";

        // Act
        result = serializeCookie(name, val);

        // Assert
        expect(result).toBe(`${name}=${val}; Max-Age=31557600; Path=/`);
    });

    it("should return a URI-safe String, when given special characters.", () => {
        // Arrange
        const name = "smiley☺";
        const val = "m:t";

        // Act
        result = serializeCookie(name, val);

        // Assert
        expect(result).toBe("smiley%E2%98%BA=m%3At; Max-Age=31557600; Path=/");
    });

    it("should return an empty String if name argument is falsy.", () => {
        // Arrange
        const name = "";
        const val = "us";

        // Act
        result = serializeCookie(name, val);

        // Assert
        expect(result).toBe("");
    });

    it("should return an empty String if val argument is falsy.", () => {
        // Arrange
        const name = "country_code";
        const val = "";

        // Act
        result = serializeCookie(name, val);

        // Assert
        expect(result).toBe("");
    });

    it("should allow setting the expiration time.", () => {
        // Arrange
        const name = "country_code";
        const val = "us";
        const maxAge = 60;

        // Act
        result = serializeCookie(name, val, maxAge);

        // Assert
        expect(result).toBe(`${name}=${val}; Max-Age=${maxAge}; Path=/`);
    });
});

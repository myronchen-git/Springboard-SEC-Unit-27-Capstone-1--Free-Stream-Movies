"use strict";

$(document).ready(() => {
    displayStoredCountry();
    $("#form-country-selection > select").on("change", handleSelectCountry);
});

// ==================================================

function displayStoredCountry() {
    const cookie = parseCookie(document.cookie);
    const countryCode = cookie["countryCode"] || "us";
    $("#form-country-selection > select").val(countryCode);
}

function handleSelectCountry(event) {
    const cookie = serializeCookie("countryCode", event.target.value);
    document.cookie = cookie;
    location.reload();
}

# Free Stream Movies

https://myron-chen-free-stream-movies.onrender.com/

A website for finding free movies to stream.

## Overview

This web app shows a list of streaming services that provide currently available free movies to stream. Users can
choose which country to show options for, view movie details, and search movie titles to see if a particular title
is free.

## Features

-   Allow selecting a country to display free movies for. The choice will be saved in a browser cookie.
    -   The movie data isn't restricted only to the United States. To allow everyone to benefit, and to not needlessly
        show streaming options a user can not use, movies are displayed in accordance to country, with users being
        able to select the country. This allows the web app to be used across the world.
-   List streaming services that provide free streaming options, and their movies.
    -   This is the main feature of the the website. This shows what movies are available for free on what streaming
        providers. This allows people to easily find free movies, instead of trying to find the movies by going through
        lists of paid and subscription options, or filtering for free options.
-   Search all movies by title.
    -   Allows users to easily find a specific movie, to see if it is free or to see its info.
-   Movie details page, which also displays list of links to streaming options.
    -   Shows detailed info such as release year, cast, and runtime. Also shows all of the free streaming options
        across different streaming providers.
-   User accounts.
    -   Allows for future features such as adding movies to watchlists and emailing users when a movie becomes free.
-   Viewable on mobile devices and on desktops.
    -   Most people view websites on their phones. Having the web app work well on both small and large screens allows
        it to be accessible to a wider audience.
-   Database is easily updatable with new data from the external API.
    -   Free streaming options do not last forever. To keep the displayed movies current, a developer can run a file
        to call the API and to save the retrieved data into the database.

## User Flow

On the homepage, streaming providers are shown with their movies. For each streaming provider, a max of 20 movies are
shown at a time. Users can click on the left and right arrows to scroll the movie options for a provider. Streaming
providers with no free streaming options are not shown.

Users can select a country from the navigation bar, which will then reload the webpage and populate the list of
streaming services and movies for that country.

Clicking on a movie will go to the movie details page and show movie info like release year, rating, runtime,
description, directors, and cast. The details page will also show the list of free streaming options, if there are
any, and whether the options are expiring soon. Clicking on an option from a streaming provider will redirect to that
provider's movie's page.

At the top, in the navigation bar, users can type in a movie title to search for. Upon sending a search request, a
new page is displayed with a list of movie results, along with their descriptions. Clicking on a result leads to the
details page.

To create an account, users can click on the "Register" link in the navbar at the top-right. A form is displayed
with fields username, password, repeat password, and email. If username or email is not unique, or if the repeated
password is not the same as the first password inputted, an error will be shown.

If users already have an account, they can log in through the "Login" link in the navbar at the top-right.

After registering or logging in, users will be redirected to the homepage. Users will stay logged in after closing
their browsers.

If logged in, the "Register" and "Login" links will not be shown. Instead, the "Logout" link will be shown. Users can
click on the "Logout" link in the navbar to log out.

## External APIs

### Streaming Availability API

https://www.movieofthenight.com/about/api/  
https://rapidapi.com/movie-of-the-night-movie-of-the-night-default/api/streaming-availability

This has a limited number of streaming services.

## Tech Stack

-   Python
-   Flask
-   PostgresQL
-   Flask-SQLAlchemy
-   Flask-Bcrypt
-   Flask-Login
-   Flask-WTF (WTForms)
-   Jinja
-   HTML
-   CSS
-   JavaScript
-   JQuery
-   Axios
-   Bootstrap

## Other

Project Ideas:
https://docs.google.com/document/d/1EYCoiANIPEsIVZTgVDpPSY2jYtedfrGOQlAPqVkLT3o/edit?usp=sharing

Proposal:
https://docs.google.com/document/d/1WoXzewIRBwGr2g7bMLV0evk-s5cDGe1VeVO0oxh2WJI/edit?usp=sharing

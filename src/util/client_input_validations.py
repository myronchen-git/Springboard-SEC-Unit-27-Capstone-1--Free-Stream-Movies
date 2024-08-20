def has_comma_in_query_parameters(query_params: list[list[str]]) -> bool:
    """
    Checks if there is a comma in any of the query parameter values.

    @param {list[list[str]]} query_params - A list of query parameter lists,
    which are obtained from request.args.getlist('QUERY_PARAM_NAME').
    @returns {bool} True if there is a comma in a query parameter.
    """

    for query_param_list in query_params:
        for query_param_item in query_param_list:
            if ',' in query_param_item:
                return True

    return False

def call_with_retry(request, sleep, attempts=3):
    for attempt in range(attempts):
        try:
            return request()
        except TimeoutError:
            sleep(2 ** attempt)

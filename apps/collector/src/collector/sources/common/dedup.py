import redis

r = redis.Redis(host='localhost', port=6379, db=0)


def is_duplicate(source : str, url):
    key = f"job:seen:{source + url}"
    created = r.set(key, "1", nx=True, ex = 60*60*24*7)

    if created:
        return False
    else:
        return True
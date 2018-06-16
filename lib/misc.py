def getpostcodes(postcodes):
    import requests
    import requests_cache
    requests_cache.install_cache('postcodecache')

    from defaults import ApiURL
    try:
        import ujson
    except ImportError:
        import json as ujson
    URL = ApiURL
    if len(postcodes) > 100:
        a = getpostcodes(postcodes[:100])
        b = getpostcodes(postcodes[100:])
        retrun = []
        for x in (a, b):
            try:
                retrun += x
            except TypeError:
                pass
        return retrun
    if len(postcodes) > 1:
        data = requests.post(URL, {'postcodes': postcodes})
        if data.status_code == 200:
            data = ujson.loads(data.content.decode('utf-8'))
            retrun = [x['result'] for x in data['result'] if x['result'] is not None]
            if retrun is not None:
                return retrun
        else:
            print('Error, Code:', data.status_code)
    elif len(postcodes) == 1:
        data = requests.get(URL + postcodes[0].replace(' ', '').upper())
        if data.status_code == 200:
            data = ujson.loads(data.content.decode('utf-8'))
            return [data['result'], ]
    print(data)
    print(len(postcodes))
    return []


def ensure_dir(file_path):
    import os
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

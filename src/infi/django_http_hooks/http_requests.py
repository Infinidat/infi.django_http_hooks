import requests
import json


def send_request(url, method, **kwargs):
    '''send http request according to given configuration, assuming headers and payload are valid jsons'''
    headers = {}
    if kwargs.get('headers'):
        # headers are expected to be a valid json
        headers = json.loads(kwargs['headers'])
    # add content-type to the headers
    if kwargs.get('conent_type'):
        headers['Content-Type'] = kwargs['content_type']

    res = requests.request(method=method,
                           url=url,
                           headers=headers,
                           # payload is a valid json as it was created by utils.set_payload
                           json=kwargs.get('payload'))
    res.raise_for_status()
    return res
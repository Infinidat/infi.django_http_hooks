from gevent import pywsgi
import json


HEADERS = (
    ('Content-Type',  'application/json'),
    ('Cache-Control', 'no-cache, no-store, must-revalidate'),
    ('Pragma',        'no-cache'),
    ('Expires',       '0'),
)




def process_request(environ, start_response):
    # Called by wsgi to handle each request
    # returns a dict with expected results by the testing method in test_requests.py
    body = {}
    body['http_method'] = environ['REQUEST_METHOD']
    if environ.get('CONTENT_TYPE'):
        body['content_type'] = environ['CONTENT_TYPE']
    if environ.get('HTTP_TEST_TOKEN'):
        body['test_token'] = environ['HTTP_TEST_TOKEN']

    input_ = environ['wsgi.input'].read()
    body['payload'] = input_.decode('utf-8')
    response_body = json.dumps(body)
    response = dict(code='200 Accepted',
                    body=response_body)

    start_response(response['code'], HEADERS)

    return [response['body'].encode()]


def runserver():
    server = pywsgi.WSGIServer(('127.0.0.1', 8080), process_request)
    server.serve_forever()




if __name__ == '__main__':
    runserver()
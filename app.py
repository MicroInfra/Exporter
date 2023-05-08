import os
import time
import typing as tp
from flask import Flask, Response, request
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app
from prometheus_client import Counter, Gauge, Histogram

app = Flask(__name__)

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})
metrics: tp.Dict[str, tp.Any] = {}
AUTH_TOKEN = os.getenv('AUTH_TOKEN', None)
DEBUG = False


@app.route('/load_metrics', methods=['POST'])
def start_task():
    '''
    Example of request:
    Header:
    Authorization: auth_token
     {
        "metrics":[
            {
                "name": "random_number_value",   str
                "value": 10,                     int
                "type": "counter|gauge|",        [Optional] str
                "labels": {"name": "value"}      [Optional] str
            }
        ]
        ...
    }
    '''
    global metrics
    if 'microinfra_exporter_rps' not in metrics:
        metrics['microinfra_exporter_rps'] = Counter('microinfra_exporter_rps', 'Requests per second')
    metrics['microinfra_exporter_rps'].inc()
    start = time.time()
    data = request.get_json()
    if DEBUG:
        print(data)

    if AUTH_TOKEN and request.headers.get('Authorization') != AUTH_TOKEN:
        auth_name = 'microinfra_exporter_auth_failed'
        if auth_name not in metrics:
            metrics[auth_name] = Counter(auth_name, 'Unauthorized requests per second')
        metrics[auth_name].inc(1)
        # Do not count time of auth failed since it not important
        return Response('', status=401)

    if not data.get('metrics'):
        no_data_name = 'microinfra_exporter_no_data'
        if no_data_name not in metrics:
            metrics[no_data_name] = Counter(no_data_name, 'Unauthorized requests per second')
        metrics[no_data_name].inc(1)
        return Response('', status=400)

    for row in data['metrics']:
        if row['name'] not in metrics:
            if row['type'] == 'counter':
                if 'response_code' in row['name']:
                    if DEBUG:
                        print('creating label for ', row['name'])
                    metrics[row['name']] = Counter(row['name'], row['name'], ['code'])
                else:
                    metrics[row['name']] = Counter(row['name'], row['name'])
            elif row['type'] == 'histogram':
                metrics[row['name']] = Histogram(row['name'], row['name'])
            else:
                metrics[row['name']] = Gauge(row['name'], row['name'])

        # Set values
        if row['type'] == 'counter':
            if row.get('labels') and 'response_code' in row['name'] and 'code' in row.get('labels'):
                code = row['labels']['code']
                if DEBUG:
                    print('setting label for ', row['name'], code)
                metrics[row['name']].labels(code).inc(row['value'])
            else:
                metrics[row['name']].inc(row['value'])
            # if row.get('labels'):
            #     metrics[row['name']].labels(**row['labels']).inc(row['value'])

        elif row['type'] == 'histogram':
            metrics[row['name']].observe(row['value'], row.get('labels', None))

        else:
            metrics[row['name']].set(row['value'])

    if 'microinfra_exporter_latency_ms' not in metrics:
        metrics['microinfra_exporter_latency_ms'] = Gauge('microinfra_exporter_latency_ms', 'Timing of requests ms')
    metrics['microinfra_exporter_latency_ms'].set((time.time() - start) * 1000)
    return ''


if __name__ == '__main__':

    app.run(host='0.0.0.0', port=60123)

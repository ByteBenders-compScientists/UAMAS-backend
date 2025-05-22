import os
import time
import uuid
import logging

from .utils import handler, proxy_request

from flask import Blueprint, request, Response, g, jsonify, render_template
from pythonjsonlogger import jsonlogger
from dotenv import load_dotenv

def register_routes(app):
    load_dotenv()

    # logging
    handler.setLevel(os.getenv('LOGGING_LEVEL'))
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(message)s',
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(os.getenv('LOGGING_LEVEL'))

    # Request tracing & timing
    @app.before_request
    def start_request():
        g.trace_id = str(uuid.uuid4())
        g.start_time = time.time()

        if request.method == 'OPTIONS':
            return Response(status=200)

    @app.after_request
    def after_request(response):
        start = getattr(g, 'start_time', None)

        if start is None:
            return response
        
        duration = time.time() - start

        log_data = {
            'level': 'info',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'trace_id': g.trace_id,
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'duration': duration,
            'client_ip': request.remote_addr or '',
            'user_id': getattr(g, 'user_id', '')
        }

        app.logger.info("request", extra=log_data)

        return response

    # health check
    @app.route('/health')
    def health():
        return jsonify({
            "message": "Api gateway is healthy"
        }), 200

    # Authentication proxy
    @app.route('/api/v1/auth/<path:subpath>', methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def auth_proxy(subpath):
        auth_url = os.getenv('AUTH_URL')
        try:
            return proxy_request(auth_url, request)
        except Exception as e:
            app.logger.error(
                'proxy error',
                extra={
                    'trace_id': g.trace_id,
                    'target': auth_url,
                    'error': str(e)
                }
            )
            return Response('Upstream error', status=502)
        
    # Backend proxy
    @app.route('/api/v1/bd/<path:subpath>', methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'])
    def backend_proxy(subpath):
        bd_url = os.getenv('BACKEND_URL')
        try:
            return proxy_request(bd_url, request)
        except Exception as e:
            app.logger.error(
                'proxy error',
                extra={
                    'trace_id': g.trace_id,
                    'target': bd_url,
                    'error': str(e)
                }
            )
            return Response('Upstream error', status=502)
        
    # documentation
    @app.route('/api/v1/docs', methods=['GET'])
    def documentation():
        return render_template('index.html')
    
    # 404 

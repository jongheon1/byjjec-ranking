#!/usr/bin/env python3
import http.server
import socketserver
import os

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"서버가 http://localhost:{PORT} 에서 실행 중입니다.")
    print(f"지도를 보려면 브라우저에서 http://localhost:{PORT}/map.html 을 열어주세요.")
    print("종료하려면 Ctrl+C를 누르세요.")
    httpd.serve_forever() 
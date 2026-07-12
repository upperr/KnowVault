#!/usr/bin/env python3
"""简单的文件服务器，用于提供 PDF 文件给 MinerU API"""
import http.server
import socketserver
import os
import sys

PORT = 8081
DIRECTORY = "/Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code/data/documents"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"文件服务器运行在 http://localhost:{PORT}")
        print(f"目录：{DIRECTORY}")
        print(f"按 Ctrl+C 停止")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")
            sys.exit(0)

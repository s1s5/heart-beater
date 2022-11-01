import http.server
import socketserver


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        print(self.path)
        print(self.headers)
        length = int(self.headers.get('content-length', 0))
        if length:
            print(self.rfile.read(length))
        # print(self.rfile.read())

        body = "hello"
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-length', len(body.encode()))
        self.end_headers()
        self.wfile.write(body.encode())


def main(port):
    with socketserver.TCPServer(("", port), Handler) as httpd:
        httpd.serve_forever()


def __entry_point():
    import argparse
    parser = argparse.ArgumentParser(
        description=u'',  # プログラムの説明
    )
    # parser.add_argument("args", nargs="*")
    parser.add_argument("--port", type=int, default=8888)
    # parser.add_argument("--int-value", type=int)
    # parser.add_argument('--move', choices=['rock', 'paper', 'scissors'])
    main(**dict(parser.parse_args()._get_kwargs()))


if __name__ == '__main__':
    __entry_point()

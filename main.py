import threading
import time
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib
from io import BytesIO

HOST = "0.0.0.0"
PORT = 8086
MAX_POINTS = 100

SERVERS = [
    ("localhost", 42439),
] # <<--- Вставляйте сервера сюда в таком формате: ("АДРЕС", ПОРТ)


history = {s[0]: [] for s in SERVERS}
latency = {s[0]: 0 for s in SERVERS}
ping_history = {s[0]: [] for s in SERVERS}


def check_server(host, port, timeout=2):
    start = time.time()
    try:
        sock = socket.create_connection((host, port), timeout)
        sock.close()
        delay = int((time.time() - start) * 1000)
        return 1, delay
    except:
        return 0, 0


def monitor():
    while True:
        for host, port in SERVERS:
            status, ping = check_server(host, port)

            history[host].append(status)
            latency[host] = ping
            ping_history[host].append(ping if status else 0)

            if len(history[host]) > MAX_POINTS:
                history[host].pop(0)

            if len(ping_history[host]) > MAX_POINTS:
                ping_history[host].pop(0)

        time.sleep(5)

def make_graph(host):
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO

    data = history.get(host, [])
    pings = ping_history.get(host, [])

    MAX_POINTS_LOCAL = 12
    data = data[-MAX_POINTS_LOCAL:]
    pings = pings[-MAX_POINTS_LOCAL:]

    if not pings:
        pings = [0]

    w, h = 300, 120

    graph_x0 = 30
    graph_x1 = 290
    graph_w = graph_x1 - graph_x0

    graph_top = 15
    graph_bottom = 85
    graph_h = graph_bottom - graph_top

    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("unifont.ttf", 13)
        small = ImageFont.truetype("unifont.ttf", 11)
        small12 = ImageFont.truetype("unifont.ttf", 12)
    except:
        font = ImageFont.load_default()
        small = font
        small12 = font

    max_val = max(pings)
    if max_val < 50:
        max_val = 50

    draw.line((graph_x0, graph_top, graph_x0, graph_bottom), fill="black", width=1)
    draw.line((graph_x0, graph_bottom, graph_x1, graph_bottom), fill="black", width=1)

    for i in range(5):
        y = int(graph_top + (graph_h / 4.0 * i))

        if i > 0:
            draw.line((graph_x0, y, graph_x1, y), fill=(220, 220, 220), width=1)

        val = int(max_val - (max_val / 4.0 * i))
        draw.text((2, y - 6), str(val), fill="black", font=small)

    n = len(pings)
    if n > 1:
        for i in range(n):
            if i % 2 == 0:
                x = int(graph_x0 + (i * graph_w) / float(n - 1))
                draw.line((x, graph_top, x, graph_bottom), fill=(235, 235, 235), width=1)

    pts = []
    n = len(pings)

    for i in range(n):
        if n > 1:
            x = graph_x0 + (i * graph_w) / float(n - 1)
        else:
            x = graph_x0

        y = graph_bottom - (pings[i] * graph_h / float(max_val))

        pts.append((int(round(x)), int(round(y))))

    for i in range(len(pts) - 1):
        draw.line(
            (pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]),
            fill=(41, 87, 162),
            width=1
        )

    for x, y in pts:
        draw.ellipse((x-2, y-2, x+2, y+2), fill=(41, 87, 162))

    for i, val in enumerate(data):
        if val == 0:
            n = len(data)
            if n > 1:
                x = int(graph_x0 + (i * graph_w) / float(n - 1))
            else:
                x = graph_x0

            y = graph_bottom - 5

            draw.line((x-4, y-4, x+4, y+4), fill=(200, 0, 0), width=2)
            draw.line((x-4, y+4, x+4, y-4), fill=(200, 0, 0), width=2)

    draw.text((graph_x0, graph_bottom + 5), "-60s", fill="black", font=small)
    draw.text((graph_x0 + graph_w//2 - 10, graph_bottom + 5), "-30s", fill="black", font=small)
    draw.text((graph_x1 - 20, graph_bottom + 5), "now", fill="black", font=small)

    uptime = int(sum(data) / float(len(data)) * 100) if data else 0
    ping = latency.get(host, 0)
    online = data[-1] == 1 if data else False

    y_text = 100

    status_left = f"Uptime: {uptime}%  Ping: {ping}ms  Status:"
    status_right = "online" if online else "offline"

    draw.rectangle((graph_x0, y_text, w-5, y_text + 16), fill="white")

    x = graph_x0
    y = y_text

    draw.text((x, y),
              status_left,
              fill="black",
              font=small12)

    bbox = draw.textbbox((0, 0), status_left, font=small12)
    text_w = bbox[2] - bbox[0]

    draw.text((x + text_w + 5, y),
              status_right,
              fill=(0, 160, 0) if online else (200, 0, 0),
              font=small12)


    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            html = """
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>Сеть DMconnect.</title>

<script>
function setHeight(h) {
    var f = document.getElementById("dash");
    if (f) {
        f.style.height = h + "px";
    }
}
</script>

<style type="text/css">
a {
    color : #0033cc;
    text-decoration : none;
}

a:hover {
    text-decoration : underline;
}
</style>

</head>

<body bgcolor="white" text="black">

<center>
<font size=5><b>Сеть DMconnect</b></font>
<br>
<b><a href="https://github.com/tankwars92/DMonitor">Исходный код.</a></b>
</center>

<center>
<iframe id="dash"
        src="/dashboard"
        width="720"
        height="600"
        frameborder="0"
        scrolling="no">
</iframe>
</center>

</body>
</html>
"""
            self.wfile.write(html.encode())
            return

        if parsed.path == "/dashboard":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            total = len(SERVERS)
            alive = sum(1 for h in history if history[h] and history[h][-1] == 1)

            if alive == total:
                status_html = '<font color="#24692A" size=4><b>ВСЕ УЗЛЫ ДОСТУПНЫ</b></font>'
            elif alive == 0:
                status_html = '<font color="red" size=4><b>СЕТЬ НЕ РАБОТАЕТ</b></font>'
            else:
                status_html = f'<font color="black" size=4><b>{alive}/{total} УЗЛОВ РАБОТАЕТ</b></font>'

            def block(host):
                status = "ONLINE" if history[host][-1:] == [1] else "OFFLINE"
                ping = latency[host]

                return f"""
                <table border=1 width=330>
                    <tr><td><b>{host}</b></td></tr>
                    <tr><td>Status: {status}</td></tr>
                    <tr><td>Ping: {ping} ms</td></tr>
                    <tr><td>
                        <img src="/img?host={host}&t={time.time()}"
                             width=300 height=120 border=0>
                    </td></tr>
                </table>
                """

            half = (len(SERVERS) + 1) // 2

            left_servers = SERVERS[:half]
            right_servers = SERVERS[half:]

            left_html = "<br>".join(block(s[0]) for s in left_servers)
            right_html = "<br>".join(block(s[0]) for s in right_servers)

            html = f"""
            <html>
            <head>
            <meta http-equiv="refresh" content="5">
            </head>

            <body bgcolor="white">

            <table width=700 align=center cellspacing=10>

            <tr>
            <td valign=top>
            {left_html}
            </td>

            <td valign=top>
            {right_html}
            </td>
            </tr>

            </table>

            <br>

            <center>
            {status_html}
            </center>

            <script>
            function sendSize() {{
                var h = document.body.scrollHeight;
                if (parent && parent.setHeight) {{
                    parent.setHeight(h);
                }}
            }}
            setInterval(sendSize, 1000);
            window.onload = sendSize;
            </script>
            </body>
            </html>
            """

            self.wfile.write(html.encode())
            return

        if parsed.path == "/img":
            qs = urllib.parse.parse_qs(parsed.query)
            host = qs.get("host", [""])[0]

            img = make_graph(host)

            self.protocol_version = "HTTP/1.0"

            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(img)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(img)
            return

if __name__ == "__main__":
    t = threading.Thread(target=monitor, daemon=True)
    t.start()

    server = HTTPServer((HOST, PORT), Handler)
    print(f"Running on http://{HOST}:{PORT}/.")
    server.serve_forever()

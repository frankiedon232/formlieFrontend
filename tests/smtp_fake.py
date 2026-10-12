"""A small SMTP server for tests (like Mailpit, on 127.0.0.1 and a free port): greets, EHLO with AUTH PLAIN,
checks the sign-in, takes MAIL / RCPT / DATA and keeps what it got. `greeting` changes what it says first (b"" says
nothing, so the client times out; anything not starting with 220 is "not a mail server")."""

from __future__ import annotations

import base64
import socketserver
import threading
from dataclasses import dataclass, field


@dataclass
class Received:
    sender: str
    recipients: list[str]
    data: str


@dataclass
class FakeSmtp:
    username: str = "mailer"
    password: str = "s3cret-pass"
    greeting: bytes = b"220 fake.test ESMTP ready\r\n"
    refuse_sender: bool = False
    messages: list[Received] = field(default_factory=list)
    logins: list[str] = field(default_factory=list)
    port: int = 0

    def start(self) -> FakeSmtp:
        fake = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self) -> None:  # noqa: C901
                if not fake.greeting:
                    self.rfile.readline()  # say nothing
                    return
                self.wfile.write(fake.greeting)
                if not fake.greeting.startswith(b"220"):
                    return
                sender, recipients = "", []
                while True:
                    raw = self.rfile.readline()
                    if not raw:
                        return
                    line = raw.decode("utf-8", "replace").strip()
                    upper = line.upper()
                    if upper.startswith(("EHLO", "HELO")):
                        self.wfile.write(b"250-fake.test\r\n250-AUTH PLAIN\r\n250 OK\r\n")
                    elif upper.startswith("AUTH PLAIN"):
                        parts = line.split(" ", 2)
                        decoded = base64.b64decode(parts[2]).split(b"\0") if len(parts) == 3 else []
                        ok = len(decoded) == 3 and decoded[1].decode() == fake.username \
                            and decoded[2].decode() == fake.password
                        fake.logins.append(decoded[1].decode() if len(decoded) == 3 else "")
                        self.wfile.write(b"235 OK\r\n" if ok else b"535 5.7.8 Authentication failed\r\n")
                    elif upper.startswith("MAIL FROM"):
                        sender = line.split(":", 1)[1].strip().split()[0].strip("<>")
                        self.wfile.write(b"550 sender refused\r\n" if fake.refuse_sender else b"250 OK\r\n")
                    elif upper.startswith("RCPT TO"):
                        recipients.append(line.split(":", 1)[1].strip().strip("<>"))
                        self.wfile.write(b"250 OK\r\n")
                    elif upper == "DATA":
                        self.wfile.write(b"354 go on\r\n")
                        lines = []
                        while True:
                            chunk = self.rfile.readline().decode("utf-8", "replace")
                            if chunk in (".\r\n", ".\n", ""):
                                break
                            lines.append(chunk)
                        fake.messages.append(Received(sender, list(recipients), "".join(lines)))
                        sender, recipients = "", []
                        self.wfile.write(b"250 queued\r\n")
                    elif upper == "RSET":
                        sender, recipients = "", []
                        self.wfile.write(b"250 OK\r\n")
                    elif upper == "QUIT":
                        self.wfile.write(b"221 bye\r\n")
                        return
                    else:
                        self.wfile.write(b"502 not here\r\n")

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self._server = Server(("127.0.0.1", 0), Handler)
        self.port = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

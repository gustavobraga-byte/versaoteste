"""Testes da VPN da UFV (v0.7.11).

Cobrem o que é determinístico e offline:
  * parsing/validação do perfil .ovpn;
  * máscara de CPF e redaction de logs;
  * reescrita do perfil com IP fixo;
  * decisão da tela inicial (should_ask / mark_decision);
  * armazenamento cifrado das credenciais;
  * handshake SOCKS5 + relay (com um servidor HTTP local).

O teste de conexão real com a UFV depende das credenciais do usuário e não
roda aqui (ver docs/VPN_UFV.md).
"""
from __future__ import annotations

import http.server
import socket
import socketserver
import threading
import time

import pytest

from pesquisai import vpn


# ── fixtures ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Cada teste roda com estado e credenciais isolados."""
    monkeypatch.setenv("UFVAI_VPN_DIR", str(tmp_path / "vpn"))
    monkeypatch.setenv("HOME", str(tmp_path))
    with vpn._LOCK:
        vpn._STATE.update(
            {
                "state": "disconnected",
                "mode": "",
                "progress": "",
                "last_error": "",
                "connected_at": 0.0,
                "tun_ip": "",
                "routes": [],
                "dns": [],
                "proxy": "",
                "pids": {},
                "forwards": [],
                "full_tunnel": False,
                "system_mode": False,
            }
        )
    yield
    vpn._cleanup_processes()


PROFILE = """client
dev tun
proto udp
remote vpn.ufvnet.ufv.br 1195
auth-user-pass
comp-lzo yes
<ca>
-----BEGIN CERTIFICATE-----
AAA
-----END CERTIFICATE-----
</ca>
<cert>
-----BEGIN CERTIFICATE-----
BBB
-----END CERTIFICATE-----
</cert>
<key>
-----BEGIN PRIVATE KEY-----
CCC
-----END PRIVATE KEY-----
</key>
"""


# ── perfil ────────────────────────────────────────────────────

def test_parse_profile_ok():
    meta = vpn.parse_profile(PROFILE)
    assert meta["valid"] is True
    assert meta["remote_host"] == "vpn.ufvnet.ufv.br"
    assert meta["remote_port"] == 1195
    assert meta["proto"] == "udp"
    assert meta["dev"] == "tun"
    assert meta["has_ca"] and meta["has_cert"] and meta["has_key"]


def test_parse_profile_invalid():
    meta = vpn.parse_profile("client\ndev tun\n")
    assert meta["valid"] is False
    assert meta["remote_host"] == ""


def test_runtime_profile_pins_ip_and_drops_auth_line():
    runtime = vpn._build_runtime_profile(PROFILE, "200.235.168.86", 1195)
    assert "remote 200.235.168.86 1195" in runtime
    assert "remote vpn.ufvnet.ufv.br" not in runtime
    # a linha nua de auth-user-pass sai; o arquivo é passado por CLI
    assert "auth-user-pass\n" not in runtime
    assert "proto udp" in runtime


def test_save_profile_text_roundtrip(tmp_path):
    meta = vpn.save_profile_text(PROFILE)
    assert meta["valid"] is True
    assert vpn.profile_path().exists()
    assert oct(vpn.profile_path().stat().st_mode & 0o777) == "0o600"
    assert vpn.parse_profile(vpn._read(vpn.profile_path()))["valid"] is True


def test_save_profile_text_rejects_garbage():
    with pytest.raises(ValueError):
        vpn.save_profile_text("nada aqui")


# ── segurança / apresentação ─────────────────────────────────

def test_mask_cpf():
    assert vpn._mask_cpf("123.456.789-01") == "***.***.***-01"
    assert vpn._mask_cpf("123") == ""


def test_redact_hides_cpf_and_password():
    text = "user 12345678901 password=segredo123"
    out = vpn._redact(text)
    assert "12345678901" not in out
    assert "segredo123" not in out
    assert "***.***.***-**" in out


# ── decisão da tela inicial ──────────────────────────────────

def test_should_ask_by_default():
    assert vpn.should_ask(str(vpn.state_dir())) is True


def test_mark_decision_stops_asking():
    vpn.mark_decision("no")
    assert vpn.load_prefs()["last_choice"] == "no"
    assert vpn.should_ask(str(vpn.state_dir())) is False


def test_mark_decision_ufv():
    vpn.mark_decision("ufv")
    assert vpn.load_prefs()["last_choice"] == "ufv"
    assert vpn.should_ask(str(vpn.state_dir())) is False


# ── credenciais cifradas ─────────────────────────────────────

def test_save_load_forget_credentials(tmp_path):
    backup = str(tmp_path / "backups")
    assert vpn.save_credentials("12345678901", "senha", backup) is True
    assert vpn.load_saved_credentials(backup) == ("12345678901", "senha")
    assert vpn.has_saved_credentials(backup) is True
    assert vpn.forget_credentials(backup) is True
    assert vpn.load_saved_credentials(backup) == ("", "")


def test_credentials_never_in_status(tmp_path):
    backup = str(tmp_path / "backups")
    vpn.save_credentials("12345678901", "senha-secreta", backup)
    st = vpn.status(backup)
    blob = repr(st)
    assert "senha-secreta" not in blob
    assert "12345678901" not in blob
    assert st["has_saved_credentials"] is True


# ── SOCKS5 + relay ───────────────────────────────────────────

class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b"ola-do-http-local"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_socks5_handshake_and_relay():
    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    http_port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    socks_port = vpn._free_port(19080, 19120)
    threading.Thread(
        target=vpn.run_socks_server,
        args=("127.0.0.1", socks_port, []),
        daemon=True,
    ).start()
    time.sleep(0.6)

    client = socket.create_connection(("127.0.0.1", socks_port), timeout=5)
    try:
        client.sendall(b"\x05\x01\x00")
        assert client.recv(2) == b"\x05\x00"
        host = b"127.0.0.1"
        req = b"\x05\x01\x00\x03" + bytes([len(host)]) + host + http_port.to_bytes(2, "big")
        client.sendall(req)
        reply = client.recv(10)
        assert reply[:2] == b"\x05\x00"
        client.sendall(b"GET / HTTP/1.1\r\nHost: local\r\nConnection: close\r\n\r\n")
        data = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            data += chunk
        assert b"ola-do-http-local" in data
    finally:
        client.close()
        httpd.shutdown()
        httpd.server_close()


# ── estado / capacidades ─────────────────────────────────────

def test_capabilities_shape():
    caps = vpn.capabilities()
    for key in (
        "has_tun",
        "has_net_admin",
        "has_unshare",
        "has_slirp4netns",
        "has_openvpn",
        "mode",
        "can_install",
    ):
        assert key in caps
    assert caps["mode"] in ("direct", "netns", "unavailable")


def test_status_shape_without_connection(tmp_path):
    st = vpn.status(str(tmp_path / "backups"))
    assert st["ok"] is True
    assert st["state"] == "disconnected"
    assert "capabilities" in st
    assert "should_ask" in st
    assert st["proxy"] == ""
    assert isinstance(st["log_tail"], list)

# ── modo total / encaminhamento de portas ────────────────────

def test_runtime_profile_full_tunnel():
    runtime = vpn._build_runtime_profile(PROFILE, "1.2.3.4", 1195, full_tunnel=True)
    assert "redirect-gateway def1" in runtime
    split = vpn._build_runtime_profile(PROFILE, "1.2.3.4", 1195, full_tunnel=False)
    assert "redirect-gateway" not in split


def test_status_has_forward_and_system_fields(tmp_path):
    st = vpn.status(str(tmp_path / "backups"))
    assert st["forwards"] == []
    assert st["full_tunnel"] is False
    assert st["system_mode"] is False


def test_set_system_mode():
    vpn.set_system_mode(True)
    assert vpn.status()["system_mode"] is True
    vpn.set_system_mode(False)
    assert vpn.status()["system_mode"] is False


def test_publish_port_requires_connection():
    with pytest.raises(vpn.VPNError):
        vpn.publish_port(8000, 8000)


def test_add_forward_requires_connection():
    with pytest.raises(vpn.VPNError):
        vpn.add_forward("10.0.0.1", 11434)


def test_remove_unknown_forward():
    assert vpn.remove_forward("nao-existe") is False

def test_test_without_proxy_is_no_proxy():
    res = vpn.test(proxy="")
    assert res["ok"] is False
    assert res["verdict"] == "no_proxy"
    assert res["proxy_ip"] == ""
    assert res["direct_ip"] == ""

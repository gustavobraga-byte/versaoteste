"""
security.py — Módulo de segurança do PesquisAI v0.2.1

Funcionalidades:
  1. Criptografia das chaves de API com Fernet (AES-128-CBC + HMAC-SHA256)
  2. Sanitização de comandos para evitar command injection
  3. Gerenciamento seguro do arquivo de chaves no Google Drive

Estratégia (adaptada para Colab sem sessão persistente):
  - Usa cryptography.fernet.Fernet (disponível no Colab)
  - Gera chave aleatória na primeira execução
  - Salva em .keys_encryption_key no Drive (arquivo SEPARADO)
  - .keys.json fica criptografado com esta chave
  - Um invasor precisa de AMBOS os arquivos para obter as keys
"""

import os
import json
import base64
import logging
from typing import Optional

logger = logging.getLogger("pesquisai.security")

# ── Arquivos no Drive ────────────────────────────────────────
KEYS_FILENAME: str = ".keys.json"
KEYFILE_FILENAME: str = ".keys_encryption_key"


# ═══════════════════════════════════════════════════════════════
# 1. CRIPTOGRAFIA COM FERNET
# ═══════════════════════════════════════════════════════════════

def _get_fernet():
    """Importa e retorna a classe Fernet com fallback.

    Tenta cryptography.fernet primeiro (disponível no Colab).
    Se não estiver disponível, usa implementação simplificada.
    """
    try:
        from cryptography.fernet import Fernet as _Fernet
        return _Fernet, "cryptography"
    except ImportError:
        logger.warning(
            "cryptography não encontrado. Usando implementação "
            "simplificada (menos segura). pip install cryptography"
        )
        return _FernetFallback, "fallback"


class _FernetFallback:
    """Implementação simplificada de Fernet para quando cryptography não está disponível.

    Usa AES-CBC + HMAC-SHA256 via hashlib + hmac puros.
    NOTA: Requer pycryptodome para AES real. Sem ele, usa XOR (menos seguro).
    """

    def __init__(self, key: bytes):
        if isinstance(key, str):
            key = key.encode("ascii")
        # Aceita key de 32 bytes ou base64
        if len(key) == 44 and b"=" in key:  # provavelmente base64
            self._key = base64.urlsafe_b64decode(key)
        elif len(key) == 32:
            self._key = key
        else:
            # Deriva uma chave de 32 bytes
            import hashlib
            self._key = hashlib.sha256(key).digest()

    @classmethod
    def generate_key(cls) -> bytes:
        """Gera uma chave Fernet compatível (base64)."""
        import secrets
        return base64.urlsafe_b64encode(secrets.token_bytes(32))

    def _get_aes_key(self) -> tuple[bytes, bytes]:
        """Deriva chave de criptografia e HMAC da chave mestra."""
        import hashlib
        enc_key = hashlib.sha256(self._key + b"enc").digest()[:16]  # AES-128
        mac_key = hashlib.sha256(self._key + b"mac").digest()
        return enc_key, mac_key

    def encrypt(self, data: bytes) -> bytes:
        """Criptografa dados no formato Fernet-like."""
        import hashlib, hmac, secrets, struct

        # Tenta usar AES real
        try:
            from Crypto.Cipher import AES
            enc_key, mac_key = self._get_aes_key()
            iv = secrets.token_bytes(16)
            cipher = AES.new(enc_key, AES.MODE_CBC, iv)
            # PKCS7 padding
            pad_len = 16 - (len(data) % 16)
            padded = data + bytes([pad_len] * pad_len)
            ciphertext = cipher.encrypt(padded)
        except ImportError:
            # Fallback: XOR + HMAC (NÃO é AES, mas ao menos não é plaintext)
            enc_key, mac_key = self._get_aes_key()
            iv = secrets.token_bytes(16)
            # XOR simples com a chave derivada
            xor_key = hashlib.sha256(enc_key + iv).digest()
            xor_key = (xor_key * (len(data) // len(xor_key) + 1))[:len(data)]
            ciphertext = bytes(a ^ b for a, b in zip(data, xor_key))
            iv = b"XOR" + iv[3:]  # marca que é XOR fallback

        # Formato: version(1) + iv(16) + ciphertext + hmac(32)
        version = struct.pack("B", 0x81)  # versão 0x81 = fallback
        h = hmac.new(mac_key, iv + ciphertext, hashlib.sha256)
        return version + iv + ciphertext + h.digest()

    def decrypt(self, token: bytes) -> bytes:
        """Descriptografa dados no formato Fernet-like."""
        import hashlib, hmac, struct

        if len(token) < 49:
            raise ValueError("Token inválido (muito curto)")

        version = token[0]
        iv = token[1:17]
        mac = token[-32:]
        ciphertext = token[17:-32]

        enc_key, mac_key = self._get_aes_key()

        # Verifica HMAC
        h = hmac.new(mac_key, iv + ciphertext, hashlib.sha256)
        expected_mac = h.digest()
        if not hmac.compare_digest(mac, expected_mac):
            raise ValueError("HMAC inválido — dados corrompidos ou chave incorreta")

        # Descriptografa
        if version == 0x81:  # fallback XOR
            xor_key = hashlib.sha256(enc_key + iv).digest()
            iv = b"\x00" + iv[1:]  # remove marca XOR
            xor_key = (xor_key * (len(ciphertext) // len(xor_key) + 1))[:len(ciphertext)]
            return bytes(a ^ b for a, b in zip(ciphertext, xor_key))
        else:
            try:
                from Crypto.Cipher import AES
                # AES-128-CBC
                cipher = AES.new(enc_key, AES.MODE_CBC, iv)
                padded = cipher.decrypt(ciphertext)
                # Remove PKCS7 padding
                pad_len = padded[-1]
                if pad_len < 1 or pad_len > 16:
                    raise ValueError("Padding inválido")
                return padded[:-pad_len]
            except ImportError:
                raise ValueError(
                    "Dados criptografados com AES, mas pycryptodome não está instalado. "
                    "Execute: pip install pycryptodome"
                )


def _get_fernet_instance(key: bytes):
    """Retorna uma instância Fernet, tentando cryptography primeiro."""
    FernetCls, engine = _get_fernet()
    if engine == "cryptography":
        # cryptography.fernet.Fernet espera key base64
        if len(key) == 32:
            key_b64 = base64.urlsafe_b64encode(key)
        else:
            key_b64 = key
        return FernetCls(key_b64)
    else:
        return FernetCls(key)


def generate_key() -> bytes:
    """Gera uma nova chave Fernet."""
    FernetCls, engine = _get_fernet()
    if engine == "cryptography":
        # Retorna key raw de 32 bytes (não base64)
        import secrets
        return secrets.token_bytes(32)
    else:
        return FernetCls.generate_key()


def encrypt_data(key: bytes, plaintext: str) -> str:
    """Criptografa string com Fernet, retorna base64.

    Args:
        key: Chave de 32 bytes.
        plaintext: Texto a criptografar.

    Returns:
        String base64 do token Fernet.
    """
    f = _get_fernet_instance(key)
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt_data(key: bytes, token: str) -> str:
    """Descriptografa token Fernet.

    Args:
        key: Chave de 32 bytes.
        token: String base64 do token.

    Returns:
        Texto original.
    """
    f = _get_fernet_instance(key)
    data = f.decrypt(token.encode("ascii"))
    return data.decode("utf-8")


# ═══════════════════════════════════════════════════════════════
# 2. GERENCIAMENTO DO ARQUIVO DE CHAVES
# ═══════════════════════════════════════════════════════════════

def _get_keyfile_path(backup_dir: str) -> str:
    """Caminho no Drive para o arquivo de chave de criptografia."""
    return os.path.join(backup_dir, KEYFILE_FILENAME)


def _get_keysfile_path(backup_dir: str) -> str:
    """Caminho no Drive para o arquivo de keys criptografadas."""
    return os.path.join(backup_dir, KEYS_FILENAME)


def _load_or_create_encryption_key(backup_dir: str) -> bytes:
    """Carrega a chave de criptografia do Drive, ou cria uma nova.

    A chave fica em arquivo SEPARADO (.keys_encryption_key).
    Um invasor precisa de AMBOS arquivos para ler as keys.

    Args:
        backup_dir: Diretório no Drive.

    Returns:
        Chave de 32 bytes.
    """
    keyfile = _get_keyfile_path(backup_dir)
    if os.path.exists(keyfile):
        try:
            with open(keyfile, "rb") as f:
                raw = f.read()
            if len(raw) >= 32:
                logger.debug("Chave de criptografia carregada do Drive.")
                return raw[:32]
        except Exception as e:
            logger.warning("Erro ao ler chave: %s. Gerando nova.", e)

    # Gera nova chave
    new_key = generate_key()
    try:
        os.makedirs(backup_dir, exist_ok=True)
        with open(keyfile, "wb") as f:
            f.write(new_key)
        # Permissões restritivas (Linux apenas)
        try:
            os.chmod(keyfile, 0o600)
        except Exception:
            pass
        logger.info("Nova chave de criptografia gerada em %s", keyfile)
    except Exception as e:
        logger.error("Falha ao salvar chave: %s", e)

    return new_key


def load_encrypted_keys(backup_dir: str) -> dict:
    """Carrega e descriptografa as chaves de API do Drive.

    Args:
        backup_dir: Diretório no Drive.

    Returns:
        Dict {provedor: key, _env_provedor: env_var}.
        Vazio se não existir.
    """
    keys_path = _get_keysfile_path(backup_dir)
    if not os.path.exists(keys_path):
        return {}

    try:
        key = _load_or_create_encryption_key(backup_dir)

        with open(keys_path, "r") as f:
            encrypted_data = json.load(f)

        decrypted = {}
        for k, v in encrypted_data.items():
            if k.startswith("_env_"):
                # Metadados não criptografados
                decrypted[k] = v
            elif isinstance(v, str) and v and len(v) > 10:
                try:
                    decrypted[k] = decrypt_data(key, v)
                except Exception as e:
                    logger.warning("Falha ao descriptografar '%s': %s", k, e)
                    decrypted[k] = ""
            else:
                decrypted[k] = v

        return decrypted
    except Exception as e:
        logger.error("Falha ao carregar chaves: %s", e)
        return {}


def save_encrypted_keys(backup_dir: str, keys: dict) -> bool:
    """Criptografa e salva as chaves de API no Drive.

    Args:
        backup_dir: Diretório no Drive.
        keys: Dict {provedor: key, _env_provedor: env_var}.

    Returns:
        True se salvou com sucesso.
    """
    try:
        key = _load_or_create_encryption_key(backup_dir)
        keys_path = _get_keysfile_path(backup_dir)

        encrypted = {}
        for k, v in keys.items():
            if k.startswith("_env_"):
                encrypted[k] = v  # não criptografa metadados
            elif isinstance(v, str) and v:
                encrypted[k] = encrypt_data(key, v)
            else:
                encrypted[k] = v

        with open(keys_path, "w") as f:
            json.dump(encrypted, f, indent=2)

        try:
            os.chmod(keys_path, 0o600)
        except Exception:
            pass

        logger.info("Chaves salvas criptografadas (%d provedores).", len(keys))
        return True
    except Exception as e:
        logger.error("Falha ao salvar chaves: %s", e)
        return False


# ═══════════════════════════════════════════════════════════════
# 3. SANITIZAÇÃO DE COMANDOS
# ═══════════════════════════════════════════════════════════════

ALLOWED_COMMAND_PREFIXES: list[str] = [
    "opencode",
    "export ",
    "echo ",
    "ls ",
    "pwd",
    "whoami",
    "date",
    "env",
]

MAX_COMMAND_LENGTH: int = 500


def _check_injection(cmd: str) -> str | None:
    """Verifica se há caracteres/sequências de command injection.

    Retorna mensagem de erro string se encontrou algo, None se ok.
    Permite especificamente: && (AND lógico)
    Bloqueia: ; | ` $( ${ > < \n \r \0
    Bloqueia & isolado (não na forma &&)
    """
    # Null bytes, newlines, carriage returns
    for ch in ("\n", "\r", "\x00"):
        if ch in cmd:
            return f"Caractere de controle proibido: {repr(ch)}"

    # Command substitution: $(...)
    if "$(" in cmd:
        return "Command substitution proibida: $("

    # Parameter expansion: ${...}
    if "${" in cmd:
        return "Parameter expansion proibida: ${"

    # Backtick substitution
    if "`" in cmd:
        return "Backtick substitution proibida: `"

    # Pipe
    if "|" in cmd:
        return "Pipe (|) proibido"

    # Redirecionamentos
    if ">" in cmd:
        return "Redirecionamento de saída (>) proibido"
    if "<" in cmd:
        return "Redirecionamento de entrada (<) proibido"

    # Ponto-e-vírgula (separador de comandos incondicional)
    # Permite apenas dentro de {} ou como parte de comando export
    if ";" in cmd:
        # Se está dentro de export X="...;...", pode ser válido
        # Mas por segurança, só permitimos ; se o comando for export
        if not cmd.strip().startswith("export "):
            return "Ponto-e-vírgula (;) proibido"

    # & isolado (permitimos &&, mas não & sozinho)
    # Estratégia: se houver & que não faz parte de &&, bloqueia
    if "&" in cmd:
        # Remove todos os && e verifica se sobrou algum &
        without_andand = cmd.replace("&&", "")
        if "&" in without_andand:
            return "E-comercial isolado (&) proibido (permitido apenas &&)"

    return None


def sanitize_command(cmd: str) -> tuple[bool, str]:
    """Valida e sanitiza um comando contra command injection.

    Regras:
      1. Máximo 500 caracteres
      2. Sem injection: ; | ` $() ${} > < & (exceto &&)
      3. Sem NULL bytes ou newlines
      4. Deve começar com prefixo permitido
      5. Exceção: export VAR=value && opencode

    Args:
        cmd: Comando a validar.

    Returns:
        (True, comando_limpo) ou (False, mensagem_erro).
    """
    if len(cmd) > MAX_COMMAND_LENGTH:
        return False, f"Comando muito longo ({len(cmd)} > {MAX_COMMAND_LENGTH})"

    cmd_stripped = cmd.strip()
    if not cmd_stripped:
        return False, "Comando vazio"

    # Verificação de command injection
    inject_err = _check_injection(cmd_stripped)
    if inject_err:
        return False, inject_err

    # Verifica prefixos permitidos
    allowed = any(cmd_stripped.startswith(p) for p in ALLOWED_COMMAND_PREFIXES)

    # export VAR="value" && opencode (usado pelo modal de providers)
    if not allowed and cmd_stripped.startswith("export "):
        partes = cmd_stripped.split("&&", 1)
        # 'export NOME=valor' ou 'export "NOME=valor"' no lado esquerdo
        if partes[0].strip().startswith("export ") and "=" in partes[0]:
            allowed = True

    # opencode -s <session_id>
    if not allowed and cmd_stripped.startswith("opencode -s "):
        rest = cmd_stripped[len("opencode -s "):].strip()
        if rest and all(c.isalnum() or c in "_-." for c in rest):
            allowed = True

    if not allowed:
        return False, (
            f"Comando não permitido. Prefixos aceitos: "
            f"{', '.join(ALLOWED_COMMAND_PREFIXES)}"
        )

    return True, cmd_stripped

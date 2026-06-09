"""Clonagem e instalação das skills do PesquisAI a partir de repositórios Git."""

import subprocess
import os
import shutil
import time

from constants import SKILLS_DIR, logger
from jokes import next_joke

SKILLS = [
    ("https://github.com/gustavobraga-byte/Skill-IBGE.git", "ibge-br"),
    ("https://github.com/gustavobraga-byte/Skill-DataSus.git", "opendatasus"),
    ("https://github.com/gustavobraga-byte/scientific-agent-skills.git", "scientific"),
    ("https://github.com/gustavobraga-byte/PesquisAI.git", "pesquisai"),
    ("https://github.com/gustavobraga-byte/UFV-ABNT.git", "ufv-abnt"),
    ("https://github.com/gustavobraga-byte/Skill_Analise_qualitativa.git", "qualitativa"),  
    ("https://github.com/gustavobraga-byte/skill_dados_brasil.git", "dados-brasil"),
    ("https://github.com/gustavobraga-byte/skill_agrobr.git", "agrobr"), 
]


def run(cmd, check=True, **kw):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    if check and result.returncode != 0:
        logger.warning("Aviso: comando falhou: %s", cmd)
    return result


def _retry_clone(repo_url, dest_name, max_attempts=3, delay=2):
    """Clone um repositório Git com retry e exponential backoff."""
    tmp = f"/tmp/skill_{dest_name}"
    for attempt in range(1, max_attempts + 1):
        if os.path.exists(tmp):
            shutil.rmtree(tmp)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, tmp],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ {dest_name} clonado.")
            return True
        if attempt < max_attempts:
            logger.warning("Tentativa %d/%d falhou para %s. Tentando novamente em %ds...",
                           attempt, max_attempts, dest_name, delay)
            time.sleep(delay)
            delay *= 2
    print(f"❌ Falha ao clonar {repo_url} após {max_attempts} tentativas")
    return False


def clone_skill(repo_url, dest_name):
    """Clone uma skill do GitHub."""
    return _retry_clone(repo_url, dest_name)


def install_skills():
    print(f"\n{next_joke()}")
    print("🔧 Instalando skills...")
    os.makedirs(SKILLS_DIR, exist_ok=True)
    
    for repo, name in SKILLS:
        clone_skill(repo, name)
    
    print(f"\n{next_joke()}")
    print("📋 Copiando skills para o diretório do agente...")
    
    mappings = [
        ("/tmp/skill_ibge-br", "ibge-br"),
        ("/tmp/skill_opendatasus", "opendatasus"),
        ("/tmp/skill_scientific/skills", "scientific"),
        ("/tmp/skill_ufv-abnt", "ufv-abnt"),
        ("/tmp/skill_qualitativa", "qualitativa"),
        ("/tmp/skill_dados-brasil", "dados-brasil"),
        ("/tmp/skill_agrobr", "agrobr"),
    ]
    
    for src, dest_name in mappings:
        dest = os.path.join(SKILLS_DIR, dest_name)
        if os.path.exists(src):
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(src, dest, dirs_exist_ok=True)
            print(f"✅ {dest_name} instalado.")
    
    print(f"\n{next_joke()}")
    print("\n🎉 Todas as skills instaladas com sucesso!")


if __name__ == "__main__":
    install_skills()

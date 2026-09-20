"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_KEY = "bug_to_user_story_v2"
PROMPTS_FILE = "prompts/bug_to_user_story_v2.yml"


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    required_fields = ["description", "system_prompt", "user_prompt", "version"]
    for field in required_fields:
        if not str(prompt_data.get(field, "")).strip():
            errors.append(f"Campo obrigatório ausente ou vazio: {field}")

    system_prompt = prompt_data.get("system_prompt", "") or ""
    user_prompt = prompt_data.get("user_prompt", "") or ""

    if "TODO" in system_prompt or "TODO" in user_prompt:
        errors.append("O prompt ainda contém TODOs")

    if "{bug_report}" not in system_prompt and "{bug_report}" not in user_prompt:
        errors.append("Nenhuma mensagem referencia a variável {bug_report}")

    techniques = prompt_data.get("techniques_applied", [])
    if len(techniques) < 2:
        errors.append(f"Mínimo de 2 técnicas requeridas, encontradas: {len(techniques)}")

    return (len(errors) == 0, errors)


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt no formato "owner/nome"
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    system_prompt = prompt_data["system_prompt"]
    user_prompt = prompt_data["user_prompt"]

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )

    techniques = prompt_data.get("techniques_applied", [])
    base_tags = list(prompt_data.get("tags", []))
    technique_tags = [f"technique:{t}" for t in techniques]
    tags = base_tags + technique_tags

    description = prompt_data.get("description", "")
    if techniques:
        description = f"{description} | Técnicas: {', '.join(techniques)}"

    readme_lines = [
        f"# {prompt_name}",
        "",
        prompt_data.get("description", ""),
        "",
        "## Técnicas aplicadas",
    ]
    readme_lines += [f"- {t}" for t in techniques]
    readme_lines += ["", f"## Versão", prompt_data.get("version", "v2")]
    readme = "\n".join(readme_lines)

    url = hub.push(
        prompt_name,
        prompt_template,
        new_repo_is_public=True,
        new_repo_description=description,
        readme=readme,
        tags=tags,
    )

    print(f"   ✓ Prompt publicado com sucesso!")
    print(f"   URL: {url}")

    return True


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS PARA O LANGSMITH HUB")

    required_vars = ["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]
    if not check_env_vars(required_vars):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB")

    print(f"Lendo prompts de: {PROMPTS_FILE}")
    prompts = load_yaml(PROMPTS_FILE)

    if not prompts:
        print(f"❌ Não foi possível carregar {PROMPTS_FILE}")
        return 1

    if PROMPT_KEY not in prompts:
        print(f"❌ Chave '{PROMPT_KEY}' não encontrada em {PROMPTS_FILE}")
        return 1

    prompt_data = prompts[PROMPT_KEY]

    print(f"\nValidando prompt '{PROMPT_KEY}'...")
    is_valid, errors = validate_prompt(prompt_data)

    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1

    print("   ✓ Prompt válido\n")

    prompt_name = f"{username}/{PROMPT_KEY}"
    print(f"Fazendo push para: {prompt_name} (público)")

    try:
        success = push_prompt_to_langsmith(prompt_name, prompt_data)
    except Exception as e:
        print(f"\n❌ Erro ao fazer push do prompt: {e}")
        print("\nVerifique:")
        print("- LANGSMITH_API_KEY está configurada corretamente no .env")
        print("- USERNAME_LANGSMITH_HUB está correto (deve ser seu handle no Hub)")
        return 1

    if success:
        print("\n✅ Push concluído com sucesso!")
        print("   Confira em: https://smith.langchain.com/prompts")
        return 0

    print("\n❌ Falha ao fazer push do prompt")
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts.string import StringPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_NAME = "leonanluppi/bug_to_user_story_v1"
PROMPT_KEY = "bug_to_user_story_v1"
OUTPUT_PATH = "prompts/bug_to_user_story_v1.yml"

# Comentário explicativo mantido no topo do YAML gerado (não faz parte do
# objeto Python — PyYAML não preserva comentários em round-trips, então é
# escrito manualmente antes do corpo do YAML).
HEADER_COMMENT = (
    "# Este arquivo contém o prompt inicial de BAIXA QUALIDADE que você deve otimizar.\n"
    "# Os problemas são intencionais (ex: {bug_report} duplicado no system e user prompt,\n"
    "# instruções vagas, falta de exemplos, sem persona definida).\n"
    "# Use-o como base para entender o que precisa ser melhorado na v2.\n"
    "#\n"
    "# Gerado/atualizado por src/pull_prompts.py a partir do LangSmith Hub.\n"
    "\n"
)


class _LiteralDumper(yaml.Dumper):
    """Dumper que força bloco literal (|) para strings multi-linha, em vez do
    estilo padrão do PyYAML (aspas simples com quebras de linha embutidas),
    mantendo o YAML legível para humanos."""


def _str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_LiteralDumper.add_representer(str, _str_presenter)


def _write_prompt_yaml(prompt_data: dict, output_path: str) -> bool:
    """
    Salva o prompt em YAML preservando formatação legível (bloco literal
    para textos multi-linha) e o comentário explicativo no topo do arquivo.

    Args:
        prompt_data: Dicionário completo (com a chave de nível superior)
        output_path: Caminho do arquivo de saída

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        body = yaml.dump(
            prompt_data,
            Dumper=_LiteralDumper,
            allow_unicode=True,
            sort_keys=False,
            indent=2,
            default_flow_style=False,
            width=1000,
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(HEADER_COMMENT)
            f.write(body)

        return True
    except Exception as e:
        print(f"❌ Erro ao salvar arquivo: {e}")
        return False


def _extract_template_text(prompt_part) -> str:
    """
    Extrai o texto bruto (com placeholders tipo {bug_report}) de uma
    mensagem de um ChatPromptTemplate, cobrindo os formatos mais comuns
    retornados pelo LangChain Hub.
    """
    # Caso 1: mensagem já "templatizada" (Message*PromptTemplate)
    prompt_attr = getattr(prompt_part, "prompt", None)
    if prompt_attr is not None:
        if isinstance(prompt_attr, StringPromptTemplate):
            return prompt_attr.template
        if isinstance(prompt_attr, list):
            # multi-part (texto + imagem, por exemplo): pega só as partes de texto
            texts = [
                p.template for p in prompt_attr if isinstance(p, StringPromptTemplate)
            ]
            return "\n".join(texts)

    # Caso 2: mensagem já formatada (BaseMessage simples, ex: SystemMessage)
    content = getattr(prompt_part, "content", None)
    if isinstance(content, str):
        return content

    return str(prompt_part)


def pull_prompts_from_langsmith():
    """
    Conecta ao LangSmith, puxa o prompt de baixa qualidade do Hub
    e salva localmente em formato YAML.

    Returns:
        True se sucesso, False caso contrário
    """
    print(f"Conectando ao LangSmith e puxando prompt: {PROMPT_NAME}")

    prompt = hub.pull(PROMPT_NAME)

    system_prompt = ""
    user_prompt = ""

    messages = getattr(prompt, "messages", None)

    if messages:
        for message in messages:
            message_type = message.__class__.__name__
            text = _extract_template_text(message)

            if "System" in message_type:
                system_prompt = text
            elif "Human" in message_type or "User" in message_type:
                user_prompt = text
    else:
        # Prompt não é um ChatPromptTemplate (ex: PromptTemplate simples)
        system_prompt = _extract_template_text(prompt)

    if not system_prompt and not user_prompt:
        print(f"⚠️  Não foi possível extrair o conteúdo do prompt '{PROMPT_NAME}'")
        return False

    print("   ✓ Prompt puxado com sucesso do Hub")
    print(f"\n--- system_prompt ---\n{system_prompt}\n")
    print(f"--- user_prompt ---\n{user_prompt}\n")

    # Preserva metadados de documentação (tags, created_at) já existentes
    # localmente, caso o arquivo já tenha sido curado manualmente antes.
    # Esses campos não vêm do Hub (o Hub só guarda o ChatPromptTemplate).
    extra_fields = {}
    if Path(OUTPUT_PATH).exists():
        existing = load_yaml(OUTPUT_PATH)
        if existing and PROMPT_KEY in existing:
            for key in ("created_at", "tags"):
                if key in existing[PROMPT_KEY]:
                    extra_fields[key] = existing[PROMPT_KEY][key]

    prompt_entry = {
        "description": "Prompt para converter relatos de bugs em User Stories (baixa qualidade, puxado do LangSmith Hub)",
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "version": "v1",
    }
    if "created_at" in extra_fields:
        prompt_entry["created_at"] = extra_fields["created_at"]
    prompt_entry["source"] = PROMPT_NAME
    if "tags" in extra_fields:
        prompt_entry["tags"] = extra_fields["tags"]

    prompt_data = {PROMPT_KEY: prompt_entry}

    success = _write_prompt_yaml(prompt_data, OUTPUT_PATH)

    if success:
        print(f"✓ Prompt salvo em: {OUTPUT_PATH}")
    else:
        print(f"❌ Erro ao salvar o prompt em {OUTPUT_PATH}")

    return success


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    try:
        success = pull_prompts_from_langsmith()
    except Exception as e:
        print(f"\n❌ Erro ao puxar prompt do LangSmith: {e}")
        print("\nVerifique:")
        print("- LANGSMITH_API_KEY está configurada corretamente no .env")
        print(f"- O prompt '{PROMPT_NAME}' existe e está acessível no Hub")
        return 1

    if success:
        print("\n✅ Pull concluído com sucesso!")
        return 0

    print("\n❌ Falha ao fazer pull do prompt")
    return 1


if __name__ == "__main__":
    sys.exit(main())

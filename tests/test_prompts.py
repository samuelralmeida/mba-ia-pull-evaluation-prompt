"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
V2_PATH = PROMPTS_DIR / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class TestPrompts:
    @classmethod
    def setup_class(cls):
        """Carrega o prompt v2 uma única vez para todos os testes da classe."""
        data = load_prompts(str(V2_PATH))
        assert data is not None, f"Não foi possível carregar {V2_PATH}"
        assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada em {V2_PATH}"
        cls.prompt_data = data[PROMPT_KEY]

        # Sanity check estrutural geral, usando o validador já pronto em utils.py
        is_valid, errors = validate_prompt_structure(cls.prompt_data)
        assert is_valid, f"Estrutura do prompt inválida: {errors}"

    def test_prompt_has_system_prompt(self):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in self.prompt_data, "Campo 'system_prompt' ausente"
        system_prompt = self.prompt_data["system_prompt"]
        assert isinstance(system_prompt, str) and system_prompt.strip(), (
            "'system_prompt' está vazio"
        )

    def test_prompt_has_role_definition(self):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        system_prompt = self.prompt_data.get("system_prompt", "")
        normalized = system_prompt.lower()
        role_markers = ["você é um", "você é uma", "you are a", "atue como"]
        assert any(marker in normalized for marker in role_markers), (
            "Nenhuma definição de persona/papel encontrada no system_prompt "
            "(esperado algo como 'Você é um...')"
        )

    def test_prompt_mentions_format(self):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        system_prompt = self.prompt_data.get("system_prompt", "")
        normalized = system_prompt.lower()
        format_markers = ["markdown", "como um", "eu quero", "para que", "user story"]
        assert any(marker in normalized for marker in format_markers), (
            "O prompt não menciona explicitamente o formato Markdown nem a "
            "estrutura padrão de User Story (Como um/Eu quero/Para que)"
        )

    def test_prompt_has_few_shot_examples(self):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = self.prompt_data.get("system_prompt", "")
        normalized = system_prompt.lower()

        has_example_marker = "exemplo" in normalized or "example" in normalized
        assert has_example_marker, (
            "Nenhum marcador de exemplo (ex: 'Exemplo 1') encontrado no system_prompt"
        )

        techniques = [t.lower() for t in self.prompt_data.get("techniques_applied", [])]
        has_fewshot_technique = any("few-shot" in t or "few shot" in t for t in techniques)
        assert has_fewshot_technique, (
            "'Few-shot Learning' não está listado em 'techniques_applied'"
        )

    def test_prompt_no_todos(self):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        system_prompt = self.prompt_data.get("system_prompt", "")
        user_prompt = self.prompt_data.get("user_prompt", "")
        assert "TODO" not in system_prompt, "system_prompt ainda contém um TODO"
        assert "TODO" not in user_prompt, "user_prompt ainda contém um TODO"

    def test_minimum_techniques(self):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = self.prompt_data.get("techniques_applied", [])
        assert isinstance(techniques, list), "'techniques_applied' deve ser uma lista"
        assert len(techniques) >= 2, (
            f"Mínimo de 2 técnicas requeridas, encontradas: {len(techniques)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

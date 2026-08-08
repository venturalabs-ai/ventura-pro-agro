"""Testes básicos de validação estrutural"""
import pytest
from pathlib import Path

def test_readme_exists():
    """Verifica que README existe"""
    assert Path("README.md").exists()

def test_license_exists():
    """Verifica que LICENSE existe"""
    assert Path("LICENSE").exists() or Path("LICENSE.md").exists()

def test_basic_structure():
    """Verifica estrutura básica do projeto"""
    root = Path(".")
    assert root.exists()
    # Adicione mais validações específicas aqui

import sys
from pathlib import Path

# Adicionar a pasta src/limpeza ao caminho de busca do Python
pasta_limpeza = Path(__file__).resolve().parent / "limpeza"
sys.path.append(str(pasta_limpeza))

from limpeza import executar_pipeline_limpeza

if __name__ == "__main__":
    executar_pipeline_limpeza()

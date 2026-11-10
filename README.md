# datathon-unisenai

Script que transforma os microdados do Novo CAGED (movimentações) em um CSV
legível, trocando os códigos pelas descrições do dicionário de dados.
Por exemplo, `42` vira "Santa Catarina" e `715505` vira "Carpinteiro".

## O que você precisa

- Python 3.10 ou mais recente
- As bibliotecas pandas e openpyxl:

  ```
  python -m pip install pandas openpyxl
  ```

- Os dois arquivos de dados, que não estão no repositório por serem grandes:
  - `Novo_Caged_MOV_Limpo.csv`
  - `Dicionario_de_dados.xlsx`

## Como gerar o arquivo legível

1. Coloque os dois arquivos de dados na mesma pasta do `decodificar_caged.py`:

   ```
   datathon-unisenai/
   ├── decodificar_caged.py
   ├── Novo_Caged_MOV_Limpo.csv
   └── Dicionario_de_dados.xlsx
   ```

2. Abra um terminal nessa pasta e rode:

   ```
   python decodificar_caged.py
   ```

3. Depois de alguns minutos, a mesma pasta terá:
   - `Novo_Caged_MOV_Legivel.csv`: os dados com as descrições
   - `relatorio_decodificacao.txt`: quantidade de linhas e códigos que não
     constam no dicionário

Nenhuma subpasta é criada. Se os arquivos já existirem, são substituídos.

Se os dados estiverem em outra pasta, informe o caminho:

```
python decodificar_caged.py "C:\caminho\dos\dados"
```

## Formato do CSV gerado

- Separador `;`, vírgula decimal e UTF-8, para abrir no Excel em português.
- O arquivo tem cerca de 3,4 milhões de linhas e 1,5 GB. O Excel abre no máximo
  1.048.576 linhas; para o arquivo completo, use pandas, Power BI ou um banco
  de dados.
- Códigos que não existem no dicionário aparecem como
  `Código X (não consta no dicionário)` e são listados no relatório.

Os arquivos `.csv` e o relatório estão no `.gitignore` e não são enviados ao GitHub.

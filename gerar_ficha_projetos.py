import os
import requests
from datetime import datetime
from collections import defaultdict

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NOME = os.environ.get("GITHUB_REPOSITORY")
ARQUIVO_SAIDA = "ficha-projetos/README.md"
PROJECT_NAME = os.environ.get("PROJECT_NAME", "teste AID")  # Nome do seu projeto

def get_project_columns_and_cards(token, repo, project_name):
    """Busca colunas e cards do Project Board"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. Buscar todos os projects do repositório
    url_projects = f"https://api.github.com/repos/{repo}/projects"
    response = requests.get(url_projects, headers=headers)
    
    if response.status_code != 200:
        print(f"Erro ao buscar projects: {response.status_code}")
        print(f"Resposta: {response.json() if response.text else 'vazia'}")
        return {}
    
    projects = response.json()
    
    # 2. Filtrar pelo nome do projeto
    project = None
    for p in projects:
        if project_name.lower() in p['name'].lower():
            project = p
            break
    
    if not project:
        print(f"Projeto '{project_name}' não encontrado!")
        print(f"Projetos disponíveis: {[p['name'] for p in projects]}")
        return {}
    
    print(f"✅ Projeto encontrado: {project['name']}")
    
    # 3. Buscar as colunas do projeto
    url_columns = f"https://api.github.com/projects/{project['id']}/columns"
    response = requests.get(url_columns, headers=headers)
    
    if response.status_code != 200:
        print(f"Erro ao buscar colunas: {response.status_code}")
        return {}
    
    columns = response.json()
    print(f"✅ Colunas encontradas: {[c['name'] for c in columns]}")
    
    # 4. Buscar os cards (issues/PRs) em cada coluna
    resultado = defaultdict(list)
    
    for column in columns:
        url_cards = f"https://api.github.com/projects/columns/{column['id']}/cards"
        response = requests.get(url_cards, headers=headers)
        
        if response.status_code != 200:
            continue
        
        cards = response.json()
        
        for card in cards:
            if not card.get('content_url'):
                continue
            
            # Buscar detalhes do issue/PR
            content_response = requests.get(card['content_url'], headers=headers)
            if content_response.status_code != 200:
                continue
            
            content = content_response.json()
            
            # Determinar se é Issue ou PR
            tipo = "Pull Request" if 'pull_request' in content else "Issue"
            
            item_info = {
                'titulo': content['title'],
                'numero': content['number'],
                'data_criacao': content['created_at'],
                'autor': content['user']['login'],
                'url': content['html_url'],
                'tipo': tipo,
                'status': column['name'],  # ← STATUS (coluna do board)
                'estado': content['state']  # open/closed
            }
            
            resultado[column['name']].append(item_info)
    
    return resultado

def gerar_markdown(projetos_por_status):
    """Gera o Markdown organizado por status/coluna"""
    agora = datetime.now()
    
    linhas = [
        "# 📊 Ficha de Projetos\n",
        f"*Última atualização: {agora.strftime('%d/%m/%Y às %H:%M:%S')}*\n",
        f"**Projeto: {PROJECT_NAME}**\n",
        "---\n"
    ]
    
    total_itens = sum(len(itens) for itens in projetos_por_status.values())
    linhas.append(f"## 📈 Resumo\n")
    linhas.append(f"- **Total de itens:** {total_itens}\n")
    linhas.append(f"- **Status disponíveis:** {len(projetos_por_status)}\n")
    linhas.append("\n---\n")
    
    # Organizar por status/coluna
    for status, itens in projetos_por_status.items():
        linhas.append(f"## 🏷️ {status}\n")
        linhas.append(f"*{len(itens)} itens*\n\n")
        
        for item in sorted(itens, key=lambda x: x['data_criacao'], reverse=True):
            data = datetime.strptime(item['data_criacao'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y")
            emoji = "🐛" if item['tipo'] == "Issue" else "🔀"
            linhas.append(f"{emoji} **[{item['titulo']}]({item['url']})** (##{item['numero']})\n")
            linhas.append(f"   - 👤 @{item['autor']} | 📅 {data}\n")
        linhas.append("\n")
    
    return "".join(linhas)

def main():
    if not GITHUB_TOKEN or not REPO_NOME:
        raise ValueError("GITHUB_TOKEN e GITHUB_REPOSITORY são necessários")
    
    print(f"Buscando projeto '{PROJECT_NAME}' no repositório: {REPO_NOME}")
    
    resultado = get_project_columns_and_cards(GITHUB_TOKEN, REPO_NOME, PROJECT_NAME)
    
    if not resultado:
        print("Nenhum item encontrado no projeto!")
        os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
        with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
            f.write(f"# 📊 Ficha de Projetos\n\nNenhum item encontrado no projeto '{PROJECT_NAME}'.\n\nCertifique-se que:\n1. O projeto '{PROJECT_NAME}' existe\n2. Existem issues/PRs associados a ele\n3. Os cards estão em alguma coluna")
        return
    
    print(f"✅ Encontrados itens em {len(resultado)} colunas")
    for status, itens in resultado.items():
        print(f"   - {status}: {len(itens)} itens")
    
    conteudo = gerar_markdown(resultado)
    
    os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        f.write(conteudo)
    
    print(f"✅ Arquivo gerado: {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    main()
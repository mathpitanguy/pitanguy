import os
import json
import requests
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any

# Configurações
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NOME = os.environ.get("GITHUB_REPOSITORY")
ARQUIVO_SAIDA = "ficha-projetos/README.md"

# Nome do seu Project Board (opcional - se vazio, pega todos)
PROJECT_NAME = os.environ.get("PROJECT_NAME", "")  # Ex: "Sprint 1" ou "Backlog"

def get_project_issues_and_prs(token: str, repo: str, project_name: str = "") -> Dict[str, List[Dict]]:
    """
    Busca Issues e PRs que estão em Project Boards
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "GraphQL": "application/vnd.github.v3+json"  # Para GraphQL
    }
    
    # Primeiro, vamos usar GraphQL que é melhor para Projects v2
    # Mas também vou incluir fallback para REST API
    
    # Buscar projects do repositório
    url_api = f"https://api.github.com/repos/{repo}/projects"
    params = {"state": "open", "per_page": 100}
    
    response = requests.get(url_api, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"Erro ao buscar projects: {response.status_code}")
        print("Tentando método alternativo para Projects v2...")
        return get_project_v2_items(token, repo, project_name)
    
    projects = response.json()
    
    # Filtrar por nome do projeto, se especificado
    if project_name:
        projects = [p for p in projects if project_name.lower() in p['name'].lower()]
    
    resultado = defaultdict(list)
    
    for project in projects:
        # Buscar cards do project
        cards_url = f"https://api.github.com/projects/{project['id']}/cards"
        cards_response = requests.get(cards_url, headers=headers)
        
        if cards_response.status_code != 200:
            continue
            
        cards = cards_response.json()
        
        for card in cards:
            if not card.get('content_url'):
                continue
            
            # Extrair número do issue/PR da URL
            content_url = card['content_url']
            content_number = content_url.split('/')[-1]
            
            # Buscar detalhes do conteúdo (issue ou PR)
            content_response = requests.get(content_url, headers=headers)
            if content_response.status_code != 200:
                continue
                
            content = content_response.json()
            
            # Determinar se é Issue ou PR
            tipo = "Pull Request" if 'pull_request' in content else "Issue"
            
            # Extrair informações
            item_info = {
                'titulo': content['title'],
                'numero': content['number'],
                'data_criacao': content['created_at'],
                'autor': content['user']['login'],
                'url': content['html_url'],
                'tipo': tipo,
                'estado': content['state'],
                'projeto': project['name']
            }
            
            resultado[project['name']].append(item_info)
    
    return dict(resultado)

def get_project_v2_items(token: str, repo: str, project_name: str = "") -> Dict[str, List[Dict]]:
    """
    Método alternativo usando GraphQL para Projects v2 (beta/novo)
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Query GraphQL para buscar projetos
    query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        projectsV2(first: 10) {
          nodes {
            id
            title
            items(first: 50) {
              nodes {
                id
                content {
                  ... on Issue {
                    title
                    number
                    createdAt
                    url
                    author {
                      login
                    }
                    state
                  }
                  ... on PullRequest {
                    title
                    number
                    createdAt
                    url
                    author {
                      login
                    }
                    state
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    owner, repo_name = repo.split('/')
    
    response = requests.post(
        "https://api.github.com/graphql",
        headers=headers,
        json={'query': query, 'variables': {'owner': owner, 'repo': repo_name}}
    )
    
    if response.status_code != 200:
        print(f"Erro GraphQL: {response.status_code}")
        return {}
    
    data = response.json()
    resultado = defaultdict(list)
    
    if 'data' in data and data['data']['repository']['projectsV2']['nodes']:
        for project in data['data']['repository']['projectsV2']['nodes']:
            # Filtrar por nome do projeto
            if project_name and project_name.lower() not in project['title'].lower():
                continue
                
            for item in project['items']['nodes']:
                if not item['content']:
                    continue
                    
                content = item['content']
                tipo = "Pull Request" if '__typename' in content and content['__typename'] == 'PullRequest' else "Issue"
                
                item_info = {
                    'titulo': content['title'],
                    'numero': content['number'],
                    'data_criacao': content['createdAt'],
                    'autor': content['author']['login'] if content['author'] else 'unknown',
                    'url': content['url'],
                    'tipo': tipo,
                    'estado': content['state'],
                    'projeto': project['title']
                }
                
                resultado[project['title']].append(item_info)
    
    return dict(resultado)

def gerar_markdown(projetos: Dict[str, List[Dict]]):
    """Gera o arquivo Markdown com todos os itens organizados por projeto"""
    agora = datetime.now()
    
    linhas = [
        "# 📊 Ficha de Projetos\n",
        f"*Última atualização: {agora.strftime('%d/%m/%Y às %H:%M:%S')}*\n",
        "---\n"
    ]
    
    total_itens = sum(len(itens) for itens in projetos.values())
    total_issues = sum(1 for itens in projetos.values() for i in itens if i['tipo'] == 'Issue')
    total_prs = sum(1 for itens in projetos.values() for i in itens if i['tipo'] == 'Pull Request')
    
    linhas.append(f"## 📈 Resumo\n")
    linhas.append(f"- **Total de itens:** {total_itens}\n")
    linhas.append(f"- **Issues:** {total_issues}\n")
    linhas.append(f"- **Pull Requests:** {total_prs}\n")
    linhas.append(f"- **Projetos ativos:** {len(projetos)}\n")
    linhas.append("\n---\n")
    
    # Organizar por projeto
    for projeto_nome, itens in sorted(projetos.items()):
        linhas.append(f"## 🗂️ {projeto_nome}\n")
        linhas.append(f"*Total: {len(itens)} itens*\n\n")
        
        # Separar Issues e PRs
        issues = [i for i in itens if i['tipo'] == 'Issue']
        prs = [i for i in itens if i['tipo'] == 'Pull Request']
        
        if issues:
            linhas.append("### 📌 Issues\n")
            for issue in sorted(issues, key=lambda x: x['data_criacao'], reverse=True):
                data = datetime.strptime(issue['data_criacao'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y")
                linhas.append(f"- **[{issue['titulo']}]({issue['url']})** (##{issue['numero']})\n")
                linhas.append(f"  - 👤 Autor: @{issue['autor']} | 📅 Criado: {data} | 🏷️ Status: {issue['estado']}\n")
            linhas.append("\n")
        
        if prs:
            linhas.append("### 🔀 Pull Requests\n")
            for pr in sorted(prs, key=lambda x: x['data_criacao'], reverse=True):
                data = datetime.strptime(pr['data_criacao'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y")
                linhas.append(f"- **[{pr['titulo']}]({pr['url']})** (##{pr['numero']})\n")
                linhas.append(f"  - 👤 Autor: @{pr['autor']} | 📅 Criado: {data} | 🏷️ Status: {pr['estado']}\n")
            linhas.append("\n")
        
        linhas.append("---\n")
    
    return "".join(linhas)

def main():
    if not GITHUB_TOKEN or not REPO_NOME:
        raise ValueError("GITHUB_TOKEN e GITHUB_REPOSITORY são necessários")
    
    print(f"Buscando items do repositório: {REPO_NOME}")
    if PROJECT_NAME:
        print(f"Filtrando apenas projetos com: {PROJECT_NAME}")
    
    projetos = get_project_issues_and_prs(GITHUB_TOKEN, REPO_NOME, PROJECT_NAME)
    
    if not projetos:
        print("Nenhum item encontrado em projects. Tentando método alternativo...")
        projetos = get_project_v2_items(GITHUB_TOKEN, REPO_NOME, PROJECT_NAME)
    
    if not projetos:
        print("Nenhum projeto encontrado!")
        # Criar um arquivo indicando que não há projetos
        os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
        with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
            f.write("# 📊 Ficha de Projetos\n\nNenhum projeto encontrado. Adicione Issues/PRs a um Project Board para visualizá-los aqui.")
        return
    
    print(f"Encontrados {len(projetos)} projetos com {sum(len(i) for i in projetos.values())} itens")
    
    conteudo = gerar_markdown(projetos)
    
    os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        f.write(conteudo)
    
    print(f"Arquivo gerado: {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    main()
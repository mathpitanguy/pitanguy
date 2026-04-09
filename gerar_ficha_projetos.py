import os
import requests
from datetime import datetime
from collections import defaultdict
from typing import List, Dict

# Configurações
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NOME = os.environ.get("GITHUB_REPOSITORY")
ARQUIVO_SAIDA = "ficha-projetos/README.md"

# Nome do seu Project Board (opcional)
PROJECT_NAME = os.environ.get("PROJECT_NAME", "")

def get_project_issues_and_prs(token: str, repo: str, project_name: str = "") -> Dict[str, List[Dict]]:
    """Busca Issues e PRs que estão em Project Boards"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url_api = f"https://api.github.com/repos/{repo}/projects"
    params = {"state": "open", "per_page": 100}
    
    response = requests.get(url_api, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"Erro ao buscar projects: {response.status_code}")
        return {}
    
    projects = response.json()
    
    if project_name:
        projects = [p for p in projects if project_name.lower() in p['name'].lower()]
    
    resultado = defaultdict(list)
    
    for project in projects:
        cards_url = f"https://api.github.com/projects/{project['id']}/cards"
        cards_response = requests.get(cards_url, headers=headers)
        
        if cards_response.status_code != 200:
            continue
            
        cards = cards_response.json()
        
        for card in cards:
            if not card.get('content_url'):
                continue
            
            content_url = card['content_url']
            content_response = requests.get(content_url, headers=headers)
            if content_response.status_code != 200:
                continue
                
            content = content_response.json()
            
            tipo = "Pull Request" if 'pull_request' in content else "Issue"
            
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

def gerar_markdown(projetos: Dict[str, List[Dict]]):
    """Gera o arquivo Markdown"""
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
    
    for projeto_nome, itens in sorted(projetos.items()):
        linhas.append(f"## 🗂️ {projeto_nome}\n")
        linhas.append(f"*Total: {len(itens)} itens*\n\n")
        
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
        print("Nenhum projeto encontrado!")
        os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
        with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
            f.write("# 📊 Ficha de Projetos\n\nNenhum projeto encontrado. Adicione Issues/PRs a um Project Board para visualizá-los aqui.")
        print(f"Arquivo gerado: {ARQUIVO_SAIDA}")
        return
    
    print(f"Encontrados {len(projetos)} projetos com {sum(len(i) for i in projetos.values())} itens")
    
    conteudo = gerar_markdown(projetos)
    
    os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        f.write(conteudo)
    
    print(f"✅ Arquivo gerado com sucesso: {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    main()
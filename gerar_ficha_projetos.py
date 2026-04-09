import os
import requests
from datetime import datetime
from collections import defaultdict

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NOME = os.environ.get("GITHUB_REPOSITORY")
ARQUIVO_SAIDA = "ficha-projetos/README.md"
PROJECT_NAME = os.environ.get("PROJECT_NAME", "teste AID")

def get_project_v2_items(token, repo, project_name):
    """Busca items do Projects V2 usando GraphQL"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    owner, repo_name = repo.split('/')
    
    # Query GraphQL para buscar projects V2
    query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        projectsV2(first: 10) {
          nodes {
            id
            title
            fields(first: 20) {
              nodes {
                ... on ProjectV2Field {
                  id
                  name
                  dataType
                }
                ... on ProjectV2SingleSelectField {
                  id
                  name
                  options {
                    id
                    name
                  }
                }
              }
            }
            items(first: 50) {
              nodes {
                id
                fieldValues(first: 10) {
                  nodes {
                    ... on ProjectV2ItemFieldTextValue {
                      text
                      field {
                        ... on ProjectV2FieldCommon {
                          name
                        }
                      }
                    }
                    ... on ProjectV2ItemFieldSingleSelectValue {
                      name
                      field {
                        ... on ProjectV2FieldCommon {
                          name
                        }
                      }
                    }
                  }
                }
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
    
    response = requests.post(
        "https://api.github.com/graphql",
        headers=headers,
        json={'query': query, 'variables': {'owner': owner, 'repo': repo_name}}
    )
    
    if response.status_code != 200:
        print(f"Erro GraphQL: {response.status_code}")
        return {}
    
    data = response.json()
    
    if 'errors' in data:
        print(f"Erro na query: {data['errors']}")
        return {}
    
    resultado = defaultdict(list)
    
    projects = data.get('data', {}).get('repository', {}).get('projectsV2', {}).get('nodes', [])
    
    for project in projects:
        if project_name.lower() not in project['title'].lower():
            continue
        
        print(f"✅ Projeto V2 encontrado: {project['title']}")
        
        # Buscar status (campo "Status" do board)
        status_field_id = None
        status_options = {}
        for field in project.get('fields', {}).get('nodes', []):
            if field.get('name') == 'Status':
                status_field_id = field.get('id')
                for option in field.get('options', []):
                    status_options[option['id']] = option['name']
                break
        
        for item in project.get('items', {}).get('nodes', []):
            if not item.get('content'):
                continue
            
            content = item['content']
            tipo = "Pull Request" if content.get('__typename') == 'PullRequest' else "Issue"
            
            # Descobrir o status
            status = "Sem status"
            for field_value in item.get('fieldValues', {}).get('nodes', []):
                if hasattr(field_value, 'get') and field_value.get('name'):
                    status = field_value.get('name')
                    break
            
            item_info = {
                'titulo': content.get('title'),
                'numero': content.get('number'),
                'data_criacao': content.get('createdAt'),
                'autor': content.get('author', {}).get('login', 'unknown'),
                'url': content.get('url'),
                'tipo': tipo,
                'estado': content.get('state'),
                'status': status,  # Status do board V2
                'projeto': project['title']
            }
            
            resultado[status].append(item_info)
    
    return resultado

def gerar_markdown(projetos_por_status):
    """Gera o Markdown organizado por status"""
    agora = datetime.now()
    
    linhas = [
        "# 📊 Ficha de Projetos V2\n",
        f"*Última atualização: {agora.strftime('%d/%m/%Y às %H:%M:%S')}*\n",
        f"**Projeto: {PROJECT_NAME}**\n",
        "---\n"
    ]
    
    total_itens = sum(len(itens) for itens in projetos_por_status.values())
    linhas.append(f"## 📈 Resumo\n")
    linhas.append(f"- **Total de itens:** {total_itens}\n")
    linhas.append(f"- **Status disponíveis:** {len(projetos_por_status)}\n")
    linhas.append("\n---\n")
    
    for status, itens in sorted(projetos_por_status.items()):
        linhas.append(f"## 🏷️ {status}\n")
        linhas.append(f"*{len(itens)} itens*\n\n")
        
        for item in sorted(itens, key=lambda x: x['data_criacao'], reverse=True):
            data = datetime.strptime(item['data_criacao'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y")
            emoji = "🐛" if item['tipo'] == "Issue" else "🔀"
            linhas.append(f"{emoji} **[{item['titulo']}]({item['url']})** (##{item['numero']})\n")
            linhas.append(f"   - 👤 @{item['autor']} | 📅 {data} | 🏷️ Estado: {item['estado']}\n")
        linhas.append("\n")
    
    return "".join(linhas)

def main():
    if not GITHUB_TOKEN or not REPO_NOME:
        raise ValueError("GITHUB_TOKEN e GITHUB_REPOSITORY são necessários")
    
    print(f"Buscando projeto V2 '{PROJECT_NAME}' no repositório: {REPO_NOME}")
    
    resultado = get_project_v2_items(GITHUB_TOKEN, REPO_NOME, PROJECT_NAME)
    
    if not resultado:
        print(f"Nenhum item encontrado no projeto V2 '{PROJECT_NAME}'!")
        os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
        with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
            f.write(f"# 📊 Ficha de Projetos V2\n\nNenhum item encontrado no projeto V2 '{PROJECT_NAME}'.\n\nCertifique-se que:\n1. O projeto V2 '{PROJECT_NAME}' existe\n2. Existem issues/PRs associados a ele\n3. Os items têm status definido")
        return
    
    print(f"✅ Encontrados itens em {len(resultado)} status diferentes")
    for status, itens in resultado.items():
        print(f"   - {status}: {len(itens)} itens")
    
    conteudo = gerar_markdown(resultado)
    
    os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        f.write(conteudo)
    
    print(f"✅ Arquivo gerado: {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    main()
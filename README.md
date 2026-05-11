# CONTROLE DE ABASTECIMENTO DE FROTA (PWA + API)

## Publicar o PWA no GitHub Pages (sem depender do seu PC)

O workflow **Deploy PWA (branch gh-pages)** copia `app/` ou `Aplicativo/` e publica na branch **`gh-pages`** (evita o erro *Get Pages site failed* da API *GitHub Actions* em algumas organizacoes).

1. Envie o codigo (`git push`).
2. Espere **Actions** ficar **verde** (cria/atualiza a branch `gh-pages`).
3. No GitHub: **Settings** → **Pages** → **Build and deployment** / **Implantacao**:
   - Origem: **Implantar de um branch** / **Deploy from a branch** (NAO "GitHub Actions" para este fluxo).
   - Branch: **`gh-pages`**
   - Pasta: **`/`** (root)
4. Salve. O site ficara em:
   - `https://SEU_USUARIO.github.io/NOME_DO_REPO/`
5. **API em producao:** a pagina do GitHub e **HTTPS**. O navegador **bloqueia** chamar API **HTTP** de outro servidor. O backend precisa estar em **HTTPS** (ou mesmo dominio com proxy).
6. Edite `app/config.js`, preencha `PROD_API` com a URL, por exemplo:
   ```js
   var PROD_API = "https://sua-api-publica.com/api";
   ```
   Faca commit e push — o workflow republica o site automaticamente.

**Atalho sem alterar o arquivo (teste):** no navegador (console):

```js
localStorage.setItem("APP_API_BASE_URL", "https://sua-api.com/api");
location.reload();
```

O GitHub Pages **nao** executa o Node do `backend/`. A API continua em outro servico (servidor da empresa, Render, Railway, etc.) ou maquina com HTTPS.

---

## Rodar local (desenvolvimento)

### Backend (API + SQLite)

```bash
cd backend
npm install
npm start
```

- API: `http://localhost:3000/api`
- Health: `http://localhost:3000/api/health`

### Frontend

```bash
cd app
python -m http.server 8080
```

Abra `http://localhost:8080`. Com `config.js` atual, **localhost** ja aponta para `http://localhost:3000/api`.

Na mesma rede Wi-Fi (IP tipo 192.168.x.x), o `config.js` tenta `http://MESMO_IP:3000/api` automaticamente.

---

## Dados e sincronizacao

- Lancamentos salvos no aparelho; fila envia para a API quando houver rede.
- Analise oficial: banco via API (ex.: Power Query em `GET /api/lancamentos`).

---

## Banco (schema)

O backend cria a tabela ao iniciar (`backend/schema.sql`).

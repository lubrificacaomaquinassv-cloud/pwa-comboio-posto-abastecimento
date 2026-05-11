# CONTROLE DE ABASTECIMENTO DE FROTA (PWA + API)

## Publicar o PWA no GitHub Pages (sem depender do seu PC)

1. Crie um repositorio no GitHub e envie este projeto (`git push`).
2. No repositorio: **Settings** → **Pages** → **Build and deployment** → **Source**: **GitHub Actions**.
3. Faca um push na branch `main` ou `master` (ou abra **Actions** → **Deploy PWA to GitHub Pages** → **Run workflow**).
4. Quando terminar, o site estara em:
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

# Deploy em Producao

Este projeto esta pronto para deploy real com Flask + Gunicorn.

## 1) Variaveis obrigatorias

Copie `.env.example` para `.env` e preencha:

- `APP_ENV=production`
- `SECRET_KEY` forte e unica
- `DATABASE_URL` (ex.: `postgresql://usuario:senha@host:5432/sistema_congreso`)
- (Opcional) `DEFAULT_ADMIN_USER` e `DEFAULT_ADMIN_PASSWORD` apenas para bootstrap
- (Opcional) `SINGLE_LOGIN_USER` e `SINGLE_LOGIN_PASSWORD`

## 2) Executar com Docker

Build:

```bash
docker build -t sistema-congreso .
```

Run:

```bash
docker run --name sistema-congreso \
  --env-file .env \
  -p 8080:8080 \
  sistema-congreso
```

## 3) Recomendacoes de seguranca para ambiente real

- Colocar atras de proxy reverso com HTTPS (Nginx, Traefik, Cloudflare, etc).
- Manter `SESSION_COOKIE_SECURE=true`.
- Nao versionar `.env`.
- Fazer backup recorrente do banco PostgreSQL (dump/snapshot do provedor).
- Restringir acesso ao banco por IP/VPC e credenciais fortes no `DATABASE_URL`.

## 4) Validacoes apos subir

- Login funciona com credenciais validas.
- Limite de tentativas de login bloqueia brute force temporariamente.
- Dashboard carrega normalmente em Linux (`templates/dashboard.html`).
- Download de relatorios (PDF e planilha) funcionando.

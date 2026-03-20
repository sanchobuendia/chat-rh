# API examples

## Chat

```bash
curl -X POST http://localhost:8000/api/v1/chat   -H 'Content-Type: application/json'   -H 'X-User-Email: joao@empresa.com'   -d '{"thread_id":"t-1","question":"Como funciona a política de férias?"}'
```

## Payroll lookup

```bash
curl 'http://localhost:8000/api/v1/payroll/employee?employee_name=Pedro%20Alves'   -H 'X-User-Email: carlos@empresa.com'
```

## Create user

```bash
curl -X POST http://localhost:8000/api/v1/admin/users   -H 'Content-Type: application/json'   -H 'X-User-Email: ana@empresa.com'   -d '{"email":"nova@empresa.com","full_name":"Nova Pessoa","role":"employee","department":"RH","is_manager":false}'
```

## Create knowledge base

```bash
curl -X POST http://localhost:8000/api/v1/admin/bases   -H 'Content-Type: application/json'   -H 'X-User-Email: ana@empresa.com'   -d '{"name":"Gestores","slug":"gestores","description":"Base restrita para gestores","classification":"restricted"}'
```

## Grant base access

```bash
curl -X POST http://localhost:8000/api/v1/admin/bases/grant \
  -H 'Content-Type: application/json' \
  -H 'X-User-Email: ana@empresa.com' \
  -d '{"email":"joao@empresa.com","slug":"rh-geral"}'
```

## Revoke base access

```bash
curl -X POST http://localhost:8000/api/v1/admin/bases/revoke \
  -H 'Content-Type: application/json' \
  -H 'X-User-Email: ana@empresa.com' \
  -d '{"email":"joao@empresa.com","slug":"rh-geral"}'
```

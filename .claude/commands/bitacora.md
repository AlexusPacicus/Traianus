---
description: Cierra la sesión de trabajo rellenando docs/development/DEVLOG.md a partir del chat y de git
allowed-tools: Read, Edit, Bash(git log:*), Bash(git status:*), Bash(git diff:*), Bash(git show:*), Bash(git add docs/development/DEVLOG.md), Bash(git commit:*), Bash(date:*)
---

Rellena la bitácora de desarrollo con el trabajo de esta sesión. Es el cierre del trabajo del día.

## 1. Reúne los hechos, no los recuerdos

- Lee `docs/development/DEVLOG.md` entero: formato, última fecha, y los puntos «Sin resolver» y
  «Próximo paso» de la última entrada.
- `git log --since="<fecha de la última entrada>" --format='%h %an %ad %s' --date=short` en la
  rama actual. Separa los commits de esta sesión de los de otras sesiones (p. ej. el trabajo de
  motor de otra sesión): los ajenos se mencionan en una línea, no se describen como propios.
- `git status --short`: lo que queda sin commitear, y de quién es.
- De este chat: qué se intentó, qué se decidió y por qué, qué se descartó, qué quedó pendiente.
  Cada afirmación tiene que poder señalarse en el chat o en git. Nada inventado, ninguna cifra que
  no esté en un artefacto commiteado.

## 2. Decide si hay algo que escribir

- Si desde la última entrada no hay commits de esta sesión, ni decisiones, ni cambios de plan —
  por ejemplo, solo consultas puntuales —, **no escribas nada** y dilo en una línea.
- Si la última entrada ya es de hoy (`date +%F`), añade al final un bloque
  `### Cierre (HH:MM)` con solo lo nuevo desde esa entrada. Si no, crea una entrada `## AAAA-MM-DD`.

## 3. Escribe, en el formato de la bitácora

En español, entradas cortas a propósito (la cabecera del archivo explica por qué), con estas
secciones y solo las que tengan contenido:

- **Contexto:** una o dos frases: de dónde se partía.
- **Se hizo:** viñetas; los hallazgos que cambiaron algo, con su porqué en una línea.
- **Resultado:** estado al cerrar (commits, qué queda listo).
- **Resuelto de entradas anteriores:** puntos de «Sin resolver» o «Próximo paso» previos que hoy
  se cerraron, citando la fecha de la entrada.
- **Sin resolver / decisión pendiente:** lo abierto, con dueño si lo tiene.
- **Próximo paso:** lista corta y ordenada.

Reglas: el archivo es append-only — nunca edites entradas anteriores; sin secretos, tokens ni
rutas de scratchpad; sin copiar el chat, resumir.

## 4. Cierra

- `git add docs/development/DEVLOG.md` y commit solo de ese archivo:
  `docs(development): log AAAA-MM-DD — <tres o cuatro temas>`, terminado con la línea
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Responde con el hash del commit y la lista de encabezados de sección escritos, en una línea cada
  uno. Nada más.

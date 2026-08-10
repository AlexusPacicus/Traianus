"""Lexical auditor of Spanish technical terms (OSS Readiness Fase 6).

Scans Python sources (AST strings + tokenized comments) and Markdown prose
for Spanish-language content, so the main package can be normalized to
technical English while preserving signatures and behavior byte-for-byte.

Usage:
    python tools/audit/audit_spanish_terms.py            # whole repository
    python tools/audit/audit_spanish_terms.py traianus/ # single tree

Exit code 1 when findings are detected; 0 when clean.
"""
import ast
import io
import re
import sys
import tokenize
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SPANISH_MARKERS = {
    "acepta", "aceptada", "aceptado", "actual", "actualizacion", "actualizar",
    "afirmaciones", "agrega", "almacen", "almacena", "alrededor", "ancla",
    "anclar", "aprobado", "aprobada", "archivo", "archivos", "arista",
    "aristas", "asincrona", "asociada", "asociado", "atributo", "aun",
    "automatically", "base", "bitacora", "bloque", "bloques", "borrador",
    "borradores", "borrar", "cada", "cambios", "cancela", "cancelado",
    "capa", "carpeta", "clave", "cliente", "codigo", "coleccion", "comando",
    "como", "completado", "compuerta", "comun", "conectar", "conexion",
    "conjunto", "conocimiento", "conseguir", "consolidacion", "consolidada",
    "consolidado", "consolidados", "consolidar", "construir", "contenido",
    "contiene", "contrato", "corpus", "correcta", "correcto", "crea",
    "creacion", "crear", "cuando", "cuenta", "datos", "defecto", "definida",
    "definido", "definir", "desde", "despues", "desvincula", "devuelve",
    "direccion", "directorio", "dispositivo", "donde", "eje", "ejemplo",
    "ejes", "elimina", "eliminar", "empareja", "emparejado", "encontrado",
    "encuentra", "entrada", "entre", "especifica", "especificaciones",
    "especificos", "espacial", "espacio", "estado", "estructura", "etc",
    "etiqueta", "evaluacion", "evaluar", "existe", "existen", "existente",
    "extendida", "falta", "fallo", "fase", "final", "firmas", "flujo",
    "formato", "frecuencia", "funcion", "futura", "futuro", "general",
    "genera", "generacion", "generico", "genericos", "geodesica",
    "geodesico", "geodesicos", "guardar", "guardia", "guardianes",
    "hackathon", "historial", "historico", "histórico", "host", "incluye",
    "incubacion", "incubando", "inferior", "ingesta", "ingestas", "ingresar",
    "inicializa", "inicializada", "inicializar", "integridad", "interior",
    "invalid", "invalido", "invalida", "inventado", "lectura", "leer",
    "legajo", "lenguaje", "limbo", "limpieza", "linea", "lineas", "llama",
    "llamada", "llamado", "local", "luego", "lugar", "manera", "marcada",
    "marca", "matriz", "mediante", "mensaje", "metadato", "metodo", "mirada",
    "mismo", "modo", "modulo", "momento", "mostrar", "motivo", "movimiento",
    "muestra", "muestras", "mutacion", "mutaciones", "mutable", "nivel",
    "nodo", "nodos", "nombrada", "nombre", "normativa", "normativo", "nota",
    "notas", "nuestra", "nuevo", "nueva", "nulos", "objeto", "observacion",
    "observador", "obtener", "oculta", "octagono", "opcion", "operacion",
    "orden", "original", "origen", "pantalla", "paquete", "parametro",
    "pasado", "paso", "pequena", "pequeno", "perimetro", "permitida",
    "permitido", "permite", "permiten", "permiso", "pertenece", "pesos",
    "peticion", "poblacion", "poc", "posterior", "prefijada", "preparada",
    "presente", "previo", "primer", "primera", "principal", "procedimiento",
    "procesada", "procesado", "procesamiento", "procesar", "proceso",
    "procesos", "proposito", "propria", "propia", "propio", "prueba",
    "pruebas", "puede", "pueden", "puerto", "punto", "purgado", "purga",
    "purge", "rechazada", "rechazado", "rechazar", "recibe", "recibir",
    "recuperar", "recursos", "redirigir", "registra", "registrado",
    "registro", "registros", "relacion", "relaciones", "relleno", "resta",
    "resultado", "resumen", "retirada", "ruta", "rutas", "salida", "sector",
    "segunda", "seguridad", "semilla", "separada", "servidor", "sesion",
    "simbolo", "simbologia", "sintetica", "sintetico", "sistema", "sitio",
    "solicitud", "subconjunto", "substrato", "sustrato", "tabla", "tambien",
    "tamano", "tarea", "tareas", "telemetria", "telemetrico", "temporal",
    "termino", "texto", "tiempo", "tipo", "tipos", "token", "total",
    "trabajo", "trazas", "triden", "ultima", "ultimo", "unico", "usuario",
    "usuarios", "utiliza", "utilizada", "utilizado", "utilizando", "vacias",
    "vacia", "vacio", "valor", "valores", "valida", "validador", "validando",
    "validar", "valido", "variable", "vector", "vectores", "ventana",
    "verificacion", "verificador", "verificar", "version", "vida", "vista",
    "volver",
}

_ACCENTED_CHARS = re.compile(r"[áéíóúñÁÉÍÓÚÑ¿¡]")


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def is_spanish(text: str) -> bool:
    lowered = _norm(text).lower()
    if _ACCENTED_CHARS.search(text) and len(text.split()) >= 2:
        return True
    tokens = {re.sub(r"[^a-z0-9]", "", t) for t in lowered.split()}
    return bool(tokens & SPANISH_MARKERS)


def _scan_python(path: Path, findings: list) -> None:
    try:
        src = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    try:
        tree = ast.parse(src)
    except SyntaxError:
        tree = None

    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value.strip()
                if len(text) >= 3 and is_spanish(text):
                    findings.append((path, node.lineno, "string/docstring", text[:120]))

    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT and is_spanish(tok.string):
                findings.append((path, tok.start[0], "comment", tok.string.strip()[:120]))
    except (tokenize.TokenError, IndentationError):
        pass


def _scan_markdown(path: Path, findings: list) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    in_fence = False
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        if not is_spanish(stripped):
            continue
        findings.append((path, idx, "markdown", stripped[:120]))


def scan(paths: list[Path]) -> list:
    findings: list = []
    for path in paths:
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix in (".py", ".md"):
                    if child.suffix == ".py":
                        _scan_python(child, findings)
                    else:
                        _scan_markdown(child, findings)
        elif path.is_file():
            if path.suffix == ".py":
                _scan_python(path, findings)
            elif path.suffix == ".md":
                _scan_markdown(path, findings)
    return findings


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument("paths", nargs="*", help="paths to scan (default: repository root)")
    args = parser.parse_args(argv)

    targets = [Path(p) for p in args.paths] or [ROOT]
    findings = scan(targets)
    for path, line, kind, text in sorted(set(findings)):
        print(f"{path}:{line} [{kind}] {text!r}")
    print(f"\n{len(set(findings))} Spanish finding(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

import re

#version del esquema del descriptor json
SCHEMA_VERSION = 1

#limites para no inflar la salida
MAX_DUMP_LINES = 40
MAX_MAKE_TARGETS = 8
SUMMARY_TOP = 10

#directorios omitidos
IGNORED_DIRS = [
    ".git","node_modules","__pycache__","dist",
    "build","bin",".vscode",".angular",".freebuff",
    "obj",".venv","venv","target",".next","coverage",
    ".pytest_cache","vendor"
]

#archivos ignorados
IGNORED_FILES = [
    "package-lock.json","poetry.lock","yarn.lock",
    "pnpm-lock.yaml",".DS_Store"
]

#extenciones a ignorar
IGNORED_EXT = (
    ".png",".jpg",".jpeg",".gif",".svg",".ico",
    ".webp",".pdf",".zip",".rar",".so",".dll",
    ".exe",".bin",".pyc",".woff",".woff2",".ttf",
    ".mp3",".mp4",".pem",".key"
)

#archivos que pueden contener informacion util
HINT_FILES = [
    "README.md",".gitignore","package.json","angular.json",
    "Dockerfile","requirements.txt","Makefile","publish.ps1"
]

#extenciones de archivos que pueden contener informacion util
HINT_SUFFIXES = (
    ".csproj",".sln"
)

#extenciones de lenguajes
LANGUAGES_EXT = (
    ".py",".js",".jsx",".ts",".tsx",".cs",".cpp",".c",
    ".php",".html",".css",".java",".kt",".kts",".sql"
)

#mapeo de lenguajes
LANGUAGES_MAP = {
    "py": "python", "js": "javascript", "jsx": "javascript", "ts": "typescript",
    "tsx": "typescript", "cs": "c#", "cpp": "c++", "kt": "kotlin","kts": "kotlin",
    "sql": "sql"
}

#archivos de entrada
START_NAMES = ("main","run","Program","index","start")

#expresiones regulares
python_environment = re.compile("^(:?.[a-z]+[-_])?(:?entorno|env)$",re.IGNORECASE)
appsettings_re = re.compile("^appsettings(:?.[a-zA-z])?.json$",re.IGNORECASE)
env_files_re = re.compile("^.env(:?.[a-z]+)?$",re.IGNORECASE)

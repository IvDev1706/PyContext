import sys
import os
import json
from constants import *
from core.builder import ProjectTreeBuilder
from core.meta import ProjectMetaBuilder
from output.writer import ProjectMDWriter

#flags soportados
KNOWN_FLAGS = ("--env-values","--update-desc")

#separar argumentos de flags
FLAGS = [arg for arg in sys.argv[1:] if arg.startswith("--")]
ARGS = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

#punto de entrada del script
if not ARGS:
    #mensaje de uso
    print("error: not enough parameters")
    print("correct usage -> python main.py <project-absolute-path> (<output-dir> optional) (--env-values optional)")
    sys.exit(1)

#validar flags desconocidos
INVALID = [flag for flag in FLAGS if flag not in KNOWN_FLAGS]
if INVALID:
    print("error: unknown flag(s) -> "+", ".join(INVALID))
    print("known flags -> "+", ".join(KNOWN_FLAGS))
    sys.exit(1)

#tools
builder = ProjectTreeBuilder()

#guardar argumentos
PROJECT_PATH = ARGS[0]
PROJECT_NAME = os.path.basename(os.path.normpath(ARGS[0]))
OUTPUT_DIR = (
    ARGS[1] if len(ARGS) > 1 else 
    os.path.join(os.environ.get("OUTPUT_DIR"),PROJECT_NAME) if os.environ.get("OUTPUT_DIR") else 
    os.path.join(os.path.dirname(os.path.abspath(__name__)),PROJECT_NAME)
)
OUTPUT_TREE = os.path.join(OUTPUT_DIR,PROJECT_NAME+".tree")
OUTPUT_JSON = os.path.join(OUTPUT_DIR,PROJECT_NAME+"_desc.json")
OUTPUT_MD = os.path.join(OUTPUT_DIR,PROJECT_NAME+"_desc.md")
INCLUDE_ENV_VALUES = "--env-values" in FLAGS

### Barrido del proyecto (directorios y archivos) ###
print("listing project directories...")

#construir arbol
builder.build(PROJECT_PATH)

print("project directory tree built successfully!!")

### Metadatos (dependencias, puntos de entrada, lenguajes, envs, etc.) ###
meta = ProjectMetaBuilder(builder)

print("building project metadata...")

#construir metadatos
meta.build_meta()

print("metadata built successfully!!")

### Descriptor (json) y markdown ###
print("generating descriptor...")

#se le pasa la ruta para conservar la seccion manual
writer = ProjectMDWriter(builder,meta,OUTPUT_MD,INCLUDE_ENV_VALUES)

#se genera antes de abrir los archivos
descriptor = writer.build_data()
markdown = writer.write_markdown()

### Salida del pipe, archivos md, json y tree ###
#consturir carpeta de destino
if not os.path.exists(OUTPUT_DIR):
    os.mkdir(OUTPUT_DIR)
    print("output dir created!!")
else:
    print("output dir already exists")

#volcado a archivo txt
with open(OUTPUT_TREE,"w",encoding="utf-8",newline="\n") as f:
    f.write(builder.tree_to_string())

#volcado a archivo json
with open(OUTPUT_JSON,"w",encoding="utf-8",newline="\n") as f:
    json.dump(descriptor,f,indent=2,ensure_ascii=False)
    f.write("\n")

#volcado a archivo md
with open(OUTPUT_MD,"w",encoding="utf-8",newline="\n") as f:
    f.write(markdown)

#mensaje final
print("Project description files dumped successfully!!")

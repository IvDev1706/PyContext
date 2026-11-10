import os
from .builder import ProjectTreeBuilder, TreeNode
from constants import (
    HINT_FILES, HINT_SUFFIXES, LANGUAGES_EXT, START_NAMES, LANGUAGES_MAP,
    SUMMARY_TOP, appsettings_re, env_files_re
)

class ProjectMetaBuilder:
    #constructor
    def __init__(self, builder:ProjectTreeBuilder):
        #atributos
        self.builder = builder
        self.hint_files:list = []
        self.environments:list = []
        self.entry_points:list = []
        self.languages = set()
        self.summary:dict = {}

    def build_meta(self):
        #recorrer los nodos (la clave ya es la ruta relativa a la raiz)
        for key in sorted(self.builder.tree.keys()):
            self.__explore_node(self.builder.tree[key])

        #conteos y archivos mas pesados
        self.__build_summary()

    #construir meta datos de un nodo
    def __explore_node(self, node:TreeNode):
        #lenguajes
        for file in sorted(node["files"]):
            if file.endswith(LANGUAGES_EXT):
                ext = file.split(".")[-1]
                self.languages.add(LANGUAGES_MAP.get(ext,ext))

        #archivos con ruta completa (solo los que guardo el builder)
        for file in sorted(node["paths"].keys()):
            path = node["paths"][file]

            #archivos de pista
            if file in HINT_FILES or file.endswith(HINT_SUFFIXES) or appsettings_re.match(file):
                self.hint_files.append(path)
                continue

            #archivos de entorno
            if env_files_re.match(file):
                self.environments.append(path)
                continue

            #posibles puntos de entrada
            if file.endswith(LANGUAGES_EXT) and file.split(".")[0] in START_NAMES:
                self.entry_points.append(path)

    #resumen del proyecto (conteos, lenguajes y archivos mas grandes)
    def __build_summary(self):
        by_language = {}
        files = []

        for key in sorted(self.builder.tree.keys()):
            for name in self.builder.tree[key]["files"]:
                path = os.path.join(self.builder.root_dir,key,name) if key else os.path.join(self.builder.root_dir,name)

                try:
                    size = os.path.getsize(path)
                    lines = self.__count_lines(path)
                except OSError:
                    continue

                #lenguaje por extension (el resto cuenta como "otros")
                ext = name.split(".")[-1].lower() if "." in name else ""
                language = LANGUAGES_MAP.get(ext) or (ext if "."+ext in LANGUAGES_EXT else "otros")
                by_language[language] = by_language.get(language,0)+1

                files.append({
                    "path": (key+"/"+name if key else name).replace(os.sep,"/"),
                    "bytes": size,
                    "lines": lines,
                })

        self.summary = {
            "files": len(files),
            "directories": len(self.builder.tree),
            "bytes": sum(f["bytes"] for f in files),
            "lines": sum(f["lines"] for f in files),
            "by_language": dict(sorted(by_language.items(),key=lambda kv: (-kv[1],kv[0]))),
            "largest": sorted(files,key=lambda f: (-f["bytes"],f["path"]))[:SUMMARY_TOP],
            "longest": sorted(files,key=lambda f: (-f["lines"],f["path"]))[:SUMMARY_TOP],
        }

    #contar lineas sin depender del encoding
    def __count_lines(self, path:str)->int:
        try:
            with open(path,"rb") as f:
                return f.read().count(b"\n")
        except OSError:
            return 0

    def get_str_meta(self):
        #impresion de lenguajes
        langs = "Lenguajes: "+", ".join(self.languages)+"\n"
        envs = "Archivos de entorno: "+", ".join(map(lambda e: os.path.basename(e),self.environments))+"\n"
        hints = "Archivos de pista: "+", ".join(map(lambda h: os.path.basename(h),self.hint_files))+"\n"
        entries = "Posibles puntos de entrada: "+", ".join(map(lambda i: os.path.basename(i),self.entry_points))+"\n"

        return langs + envs + hints + entries

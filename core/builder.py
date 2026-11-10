import os
import fnmatch
from typing import TypedDict
from constants import (
    HINT_FILES, HINT_SUFFIXES, IGNORED_DIRS, IGNORED_EXT, IGNORED_FILES,
    LANGUAGES_EXT, START_NAMES, appsettings_re, env_files_re,
    python_environment
)

#modelo de nodo de arbol
class TreeNode(TypedDict):
    #claves (siempre relativas a la raiz del proyecto)
    subdirectories: list[str]
    files: list[str]
    #ruta completa, solo de los archivos que le interesan a meta
    paths: dict[str,str]

#constructor del arbol de directorios
class ProjectTreeBuilder:
    #constructor de clase
    def __init__(self):
        #atributos
        self.tree:dict[str,TreeNode] = {}
        self.root_dir:str = ""
        self.str_tree:str = ""
        self.__visited:set[str] = set()
        #patrones del .gitignore raiz: (patron, negado, solo directorios)
        self.__patterns:list[tuple[str,bool,bool]] = []

    #metodos
    def build(self, path:str):
        #limpiar el arbol
        if self.tree and self.root_dir:
            self.tree = {}
            self.root_dir = ""
            self.str_tree = ""
            self.__visited = set()
            self.__patterns = []

        #leer el .gitignore de la raiz
        self.__load_gitignore(os.path.join(path,".gitignore"))

        #guardar raiz
        self.root_dir = os.path.normpath(path)

        #metodo recursivo (la raiz se guarda con la clave vacia)
        self.__build_tree(path,"")

        return self.tree

    #utilerias de path
    def __is_file(self, path:str):
        return os.path.isfile(path)

    def __get_basename(self, path:str):
        return os.path.basename(path)

    #validar si el archivo se usa para construir metadatos
    def __is_meta_file(self, name:str)->bool:
        if name in HINT_FILES or name.endswith(HINT_SUFFIXES):
            return True
        if appsettings_re.match(name) or env_files_re.match(name):
            return True
        return name.endswith(LANGUAGES_EXT) and name.split(".")[0] in START_NAMES

    #metodo build recursivo
    # key = directorio relativo a la raiz ("" para la raiz)
    def __build_tree(self, path:str, key:str):
        #evitar ciclos por enlaces
        real = os.path.realpath(path)
        if real in self.__visited:
            return
        self.__visited.add(real)

        #crear nodo del directorio
        node = TreeNode(subdirectories=[],files=[],paths={})
        self.tree[key] = node

        #listar contenido (ordenado para que el arbol sea estable)
        try:
            elements = sorted(os.listdir(path))
        except OSError:
            elements = []

        for element in elements:
            element_path = os.path.join(path,element)
            is_file = self.__is_file(element_path)
            #ruta relativa del elemento
            relative = os.path.join(key,element) if key else element

            #omitir lo que marca el .gitignore
            if self.__gitignored(relative,element,not is_file):
                continue

            #caso archivo
            if is_file:
                if element in IGNORED_FILES or element.endswith(IGNORED_EXT):
                    continue
                node["files"].append(element)
                #solo los archivos de meta guardan su ruta completa
                if self.__is_meta_file(element):
                    node["paths"][element] = element_path
                continue

            #validar si el directorio es omitido
            if element in IGNORED_DIRS or python_environment.match(element):
                continue

            #clave relativa del subdirectorio
            node["subdirectories"].append(relative)

            #llamada recursiva
            self.__build_tree(element_path,relative)

    #leer los patrones del .gitignore de la raiz
    def __load_gitignore(self, path:str):
        try:
            with open(path,"r",encoding="utf-8",errors="replace") as f:
                lines = f.read().splitlines()
        except OSError:
            return

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            negate = line.startswith("!")
            if negate:
                line = line[1:]

            dir_only = line.endswith("/")
            line = line.strip("/")

            if line:
                self.__patterns.append((line,negate,dir_only))

    #validar si un elemento esta ignorado (manda el ultimo patron que coincide)
    def __gitignored(self, relative:str, name:str, is_dir:bool)->bool:
        ignored = False
        target = relative.replace(os.sep,"/")

        for pattern,negate,dir_only in self.__patterns:
            #un patron de directorio no aplica a archivos
            if dir_only and not is_dir:
                continue

            if "/" in pattern:
                matched = fnmatch.fnmatch(target,pattern) or target.startswith(pattern+"/")
            else:
                matched = fnmatch.fnmatch(name,pattern)

            if matched:
                ignored = not negate

        return ignored

    #imprimir el arbol
    def print(self):
        #validar si hay arbol
        if not self.tree:
            print("/")
            return

        #str cacheado
        if self.str_tree:
            print(self.str_tree)
            return

        #constuir string
        self.str_tree = self.__str_tree("")
        print(self.str_tree)

    def __str_tree(self, node:str, level:int = 0, output="")->str:
        #la raiz se muestra con el nombre del proyecto
        name = self.__get_basename(self.root_dir) if level == 0 else self.__get_basename(node)
        output += level*"  "+name+"/\n"

        #caso base no es carpeta
        if not node in self.tree.keys():
            return output

        #imprimir subdirectorios
        for subdir in self.tree[node]["subdirectories"]:
            output = self.__str_tree(subdir,level+1,output)

        #imprimir archivos
        for file in self.tree[node]["files"]:
            output += (level+1)*"  "+file+"\n"

        return output

    def tree_to_string(self):
        #validar cache
        if not self.str_tree:
            self.str_tree = self.__str_tree("")

        #retornar arbol en string
        return self.str_tree

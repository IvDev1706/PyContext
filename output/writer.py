import os
import json
import re
import xml.etree.ElementTree as ET
from core.builder import ProjectTreeBuilder
from core.meta import ProjectMetaBuilder
from output.json_to_md import DescriptorMDConverter
from constants import MAX_DUMP_LINES, MAX_MAKE_TARGETS, SCHEMA_VERSION


class ProjectMDWriter:
    #constructor
    def __init__(
            self,
            builder:ProjectTreeBuilder,
            meta:ProjectMetaBuilder,
            output_md:str = "",
            include_env_values:bool = False
        ):
        #atributos
        self.__builder = builder
        self.__meta = meta
        #ruta del archivo, se usa para conservar la seccion manual
        self.__output_path = output_md
        self.__include_env_values = include_env_values
        self.__data:dict = {}

    #construir el descriptor (json)
    def build_data(self)->dict:
        if self.__data:
            return self.__data

        self.__data = {
            "schema": SCHEMA_VERSION,
            "project": {"name": os.path.basename(self.__builder.root_dir)},
            "summary": self.__meta.summary,
            "metadata": {
                "languages": sorted(self.__meta.languages),
                "environments": self.__relative(self.__meta.environments),
                "hint_files": self.__relative(self.__meta.hint_files),
                "entry_points": self.__relative(self.__meta.entry_points),
            },
            "dependencies": self.__build_dependencies(),
            "commands": self.__build_commands(),
            "entries": self.__build_entries(),
            "secrets": self.__build_secrets(),
            "manual": {"text": self.__read_manual_section()},
        }

        return self.__data

    #generar el markdown desde el descriptor
    def write_markdown(self)->str:
        return DescriptorMDConverter().render(self.build_data())

    #arbol sin rutas absolutas
    def __tree_data(self)->dict:
        tree = {}

        for key,node in self.__builder.tree.items():
            tree[key.replace(os.sep,"/")] = {
                "subdirectories": [s.replace(os.sep,"/") for s in node["subdirectories"]],
                "files": list(node["files"]),
            }

        return tree

    #utilerias
    def __relative(self, paths:list)->list:
        return [self.__rel(p) for p in paths]

    def __rel(self, path:str)->str:
        try:
            return os.path.relpath(os.path.join(self.__builder.root_dir,path)).replace(os.sep,"/")
        except ValueError:
            return os.path.basename(path)

    def __read(self, path:str)->str:
        #lectura tolerante (encoding o archivo ausente no tumban la corrida)
        try:
            with open(path,"r",encoding="utf-8",errors="replace") as f:
                return f.read().replace("\r\n","\n").replace("\r","\n")
        except OSError:
            return ""

    #nombre de imagen para docker
    def __image_name(self)->str:
        name = re.sub(r"[^a-z0-9_.-]","-",self.__builder.root_dir.lower()).strip("-")
        return name or "app"

    #dependencias de cada archivo soportado
    def __build_dependencies(self)->list:
        result = []

        for hint_file in self.__meta.hint_files:
            base = os.path.basename(hint_file).lower()

            #python
            if base.endswith("requirements.txt"):
                items = self.__read_requirements(hint_file)
                if items:
                    result.append({
                        "file": self.__rel(hint_file),
                        "type": "requirements",
                        "items": items,
                    })
            #node
            elif base == "package.json":
                result.append({"file": self.__rel(hint_file),"type": "npm",**self.__read_package(hint_file)})
            #.net
            elif base.endswith(".csproj"):
                result.append({"file": self.__rel(hint_file),"type": "dotnet",**self.__read_csproj(hint_file)})

        return result

    def __read_requirements(self, path:str)->list:
        deps = []

        for line in self.__read(path).split("\n"):
            line = line.strip()
            #omitir lineas vacias y comentarios
            if line and not line.startswith("#"):
                deps.append(line)

        return deps

    def __read_package(self, path:str)->dict:
        try:
            package = json.loads(self.__read(path) or "{}")
        except json.JSONDecodeError:
            return {"error": "No se pudo leer el archivo."}

        return {
            "dependencies": package.get("dependencies") or {},
            "dev_dependencies": package.get("devDependencies") or {},
        }

    #comandos por stack
    def __build_commands(self)->list:
        commands = []
        project_file = ""

        #detectar solucion o proyecto de test de .net
        for hint_file in self.__meta.hint_files:
            base = os.path.basename(hint_file).lower()
            if base.endswith(".sln") or (base.endswith(".csproj") and "test" in base):
                project_file = self.__rel(hint_file)
                break

        for hint_file in self.__meta.hint_files:
            base = os.path.basename(hint_file).lower()
            rel = self.__rel(hint_file)

            #.net
            if base.endswith(".csproj"):
                commands.append({"file": rel,"command": f'dotnet build "{rel}"'})
                #un proyecto de test no se ejecuta
                if "test" not in base:
                    commands.append({"file": rel,"command": f'dotnet run --project "{rel}"'})
            elif base.endswith(".sln"):
                commands.append({"file": rel,"command": f'dotnet build "{rel}"'})
            #scripts de despliegue
            elif base == "publish.ps1":
                commands.append({"file": rel,"command": f'pwsh "./{rel}"'})
            #python
            elif base.endswith("requirements.txt"):
                commands.append({"file": rel,"command": f'pip install -r "{rel}"'})
            #node
            elif base == "package.json":
                commands.append({"file": rel,"command": "npm install"})
            #make
            elif base == "makefile":
                for target in self.__read_make_targets(hint_file):
                    commands.append({"file": rel,"command": f"make {target}"})
            #docker
            elif base == "dockerfile":
                commands.append({"file": rel,"command": f"docker build -t {self.__image_name()} ."})
                commands.append({"file": rel,"command": f"docker run --rm {self.__image_name()}"})

        #tests de .net
        if project_file:
            commands.append({"file": project_file,"command": "dotnet test"})

        return self.__unique_commands(commands)

    def __unique_commands(self, commands:list)->list:
        seen = set()
        unique = []

        for item in commands:
            if item["command"] in seen:
                continue
            seen.add(item["command"])
            unique.append(item)

        return unique

    def __read_make_targets(self, path:str)->list:
        targets = []

        for line in self.__read(path).split("\n"):
            match = re.match(r"^([A-Za-z0-9_.-]+)\s*:(?!=)",line)
            if not match:
                continue

            target = match.group(1)
            #ignorar objetivos especiales y repetidos
            if target.startswith(".") or target in targets:
                continue

            targets.append(target)

        return targets[:MAX_MAKE_TARGETS]

    #puntos de entrada y scripts
    def __build_entries(self)->list:
        result = []

        for hint_file in self.__meta.hint_files:
            base = os.path.basename(hint_file).lower()

            if base == "dockerfile":
                items = self.__read_dockerfile(hint_file)
                if items:
                    result.append({"file": self.__rel(hint_file),"type": "dockerfile","items": items})
            elif base == "package.json":
                items = self.__read_scripts(hint_file)
                if items:
                    result.append({"file": self.__rel(hint_file),"type": "scripts","items": items})

        return result

    def __read_dockerfile(self, path:str)->list:
        items = []

        for line in self.__read(path).split("\n"):
            line = line.strip()
            #comando de arranque del contenedor
            if line.startswith(("ENTRYPOINT","CMD")):
                items.append(line)

        return items

    def __read_scripts(self, path:str)->list:
        try:
            package = json.loads(self.__read(path) or "{}")
        except json.JSONDecodeError:
            return []

        scripts = package.get("scripts") or {}

        return [{"name": name,"command": command} for name,command in scripts.items()]

    #secretos: solo nombres de variables, salvo que se pidan los valores
    def __build_secrets(self)->list:
        secrets = []

        for env in self.__meta.environments:
            #solo se muestra el formato de ejemplo
            if not env.lower().endswith(".example"):
                continue

            keys = []
            lines = []

            for line in self.__read(env).split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key = line.split("=",1)[0].strip()
                if not key:
                    continue

                keys.append(key)
                lines.append(line if self.__include_env_values else key+"=")

            if not keys:
                continue

            secrets.append({
                "file": self.__rel(env),
                "keys": keys,
                "lines": lines[:MAX_DUMP_LINES],
                "omitted": max(0,len(lines)-MAX_DUMP_LINES),
                "values_included": self.__include_env_values,
            })

        return secrets

    #contenido manual escrito en la corrida anterior ("" si no hay nada)
    def __read_manual_section(self)->str:
        if not self.__output_path:
            return ""

        content = self.__read(self.__output_path)
        if not content:
            return ""

        #buscar el encabezado de la seccion
        lines = content.split("\n")
        start = -1
        for index,line in enumerate(lines):
            if line.strip().lower().startswith("## seccion manual"):
                start = index
                break

        if start < 0:
            return ""

        #tomar lineas hasta la siguiente seccion
        body = []
        for line in lines[start+1:]:
            if line.strip().startswith("## "):
                break
            body.append(line.rstrip())

        #quitar lineas en blanco repetidas y de los extremos
        cleaned = []
        for line in body:
            if line == "" and (not cleaned or cleaned[-1] == ""):
                continue
            cleaned.append(line)
        while cleaned and cleaned[-1] == "":
            cleaned.pop()

        #si solo quedaron los placeholders no hay nada que conservar
        placeholder = re.compile(r"^-?\s*\*\*[^*]+:\*\*\s*$")
        if not any(line and not placeholder.match(line) for line in cleaned):
            return ""
        
        return "\n".join(cleaned)

    #proyecto de .net: target framework y paquetes nuget
    def __read_csproj(self, path:str)->dict:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError):
            return {"error": "No se pudo leer el archivo."}

        def local(tag:str)->str:
            #ignorar el namespace del xml
            return tag.split("}")[-1]

        frameworks = []
        packages = []

        for node in root.iter():
            tag = local(node.tag)
            text = (node.text or "").strip()

            #frameworks destino
            if tag == "TargetFramework" and text:
                frameworks.append(text)
            elif tag == "TargetFrameworks" and text:
                frameworks += [t.strip() for t in text.split(";") if t.strip()]

            #paquetes nuget
            elif tag == "PackageReference":
                name = node.get("Include") or node.get("Update")
                version = node.get("Version")
                if not version:
                    for child in node:
                        if local(child.tag) == "Version" and (child.text or "").strip():
                            version = child.text.strip()
                if name:
                    packages.append({"name": name,"version": version or ""})

        return {"frameworks": frameworks,"packages": packages}

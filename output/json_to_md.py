import json
import sys


class DescriptorMDConverter:
    #render del descriptor json a markdown
    def render(self,data:dict)->str:
        sections = [
            self.__title(data),
            self.__summary(data),
            self.__manual(data),
            self.__metadata(data),
            self.__dependencies(data),
            self.__secrets(data),
            self.__entries(data),
        ]

        return "\n\n".join(section for section in sections if section)+"\n"

    #encabezado
    def __title(self,data:dict)->str:
        name = (data.get("project") or {}).get("name") or "proyecto"
        return f"# {name} - descripcion de proyecto"

    #resumen del proyecto
    def __summary(self,data:dict)->str:
        summary = data.get("summary") or {}
        if not summary:
            return ""

        lines = ["## RESUMEN",""]
        lines.append(f"- **Archivos:** {summary.get('files',0)} en {summary.get('directories',0)} directorios")
        lines.append(f"- **Tamaño:** {self.__size(summary.get('bytes',0))} · {summary.get('lines',0)} lineas")

        languages = summary.get("by_language") or {}
        if languages:
            lines.append("- **Lenguajes:** "+", ".join(f"{name} ({count})" for name,count in languages.items()))

        longest = summary.get("longest") or []
        if longest:
            lines += ["","**Archivos con mas lineas**","","| Archivo | Lineas | Tamaño |","| --- | --- | --- |"]
            for item in longest:
                lines.append(f"| `{item['path']}` | {item['lines']} | {self.__size(item['bytes'])} |")

        largest = summary.get("largest") or []
        if largest:
            lines += ["","**Archivos mas grandes**","","| Archivo | Tamaño | Lineas |","| --- | --- | --- |"]
            for item in largest:
                lines.append(f"| `{item['path']}` | {self.__size(item['bytes'])} | {item['lines']} |")

        return "\n".join(lines)

    #seccion manual (se conserva entre corridas)
    def __manual(self,data:dict)->str:
        heading = "## SECCION MANUAL (agregar a mano)"
        text = (data.get("manual") or {}).get("text") or ""

        if text:
            return heading+"\n\n"+text

        return (
            heading+"\n\n"
            "- **Arquitectura:** \n"
            "- **Convenciones de nombres:** \n"
            "- **Como correr test y linters:** \n"
            "- **Zonas que NO se deben tocar:** \n"
            "- **Decisiones importantes y porque:** "
        )

    #metadatos detectados
    def __metadata(self,data:dict)->str:
        metadata = data.get("metadata") or {}

        lines = ["## SECCION DE METADATOS",""]
        lines.append("**Lenguajes:** "+(", ".join(metadata.get("languages") or []) or "_(ninguno)_"))
        lines.append("**Archivos de entorno:** "+self.__names(metadata.get("environments")))
        lines.append("**Archivos de pista:** "+self.__names(metadata.get("hint_files")))
        lines.append("**Posibles puntos de entrada:** "+self.__names(metadata.get("entry_points")))

        return "\n".join(lines)

    def __names(self,paths:list)->str:
        if not paths:
            return "_(ninguno)_"
        return ", ".join(sorted("`"+path+"`" for path in paths))

    #dependencias
    def __dependencies(self,data:dict)->str:
        blocks = []

        for dependency in data.get("dependencies") or []:
            body = self.__dependency_body(dependency)
            if body:
                blocks.append(f"**`{dependency.get('file','')}`**\n\n"+body)

        if not blocks:
            return "## SECCION DE DEPENDENCIAS\n\nNo se encontraron archivos de dependencias"

        return "## SECCION DE DEPENDENCIAS\n\n"+"\n\n".join(blocks)

    def __dependency_body(self,dependency:dict)->str:
        kind = dependency.get("type")

        if dependency.get("error"):
            return "_"+dependency["error"]+"_"

        #requirements de python
        if kind == "requirements":
            items = dependency.get("items") or []
            return "\n".join(f"- `{item}`" for item in items)

        #package.json
        if kind == "npm":
            blocks = []
            for title,key in (("Dependencias","dependencies"),("Dependencias de desarrollo","dev_dependencies")):
                deps = dependency.get(key) or {}
                if not deps:
                    continue
                blocks.append(title+":\n\n"+"\n".join(f"- `{name}` = {version}" for name,version in deps.items()))
            return "\n\n".join(blocks)

        #proyecto de .net
        if kind == "dotnet":
            lines = []
            frameworks = dependency.get("frameworks") or []
            if frameworks:
                lines.append("- **Target framework:** "+", ".join(f"`{framework}`" for framework in frameworks))

            packages = dependency.get("packages") or []
            if packages:
                lines.append("\nPaquetes NuGet:\n")
                lines.append("\n".join(
                    "- `"+package.get("name","")+"`"+(f" = {package['version']}" if package.get("version") else "")
                    for package in packages
                ))

            return "\n".join(lines)

        return ""

    #secretos (solo nombres de variables por defecto)
    def __secrets(self,data:dict)->str:
        blocks = []

        for secret in data.get("secrets") or []:
            lines = secret.get("lines") or []
            body = "```dotenv\n"+"\n".join(lines)+"\n```"

            if secret.get("omitted"):
                body += f"\n\n_... {secret['omitted']} lineas omitidas._"
            if not secret.get("values_included"):
                body += "\n\n_Solo se muestran los nombres de las variables (valores omitidos)._"

            blocks.append(f"**`{secret.get('file','')}`**\n\n"+body)

        if not blocks:
            return "## SECCION DE SECRETOS\n\nNo se encontraron plantillas de secretos"

        return "## SECCION DE SECRETOS\n\n"+"\n\n".join(blocks)

    #comandos y puntos de entrada agrupados por archivo
    def __entries(self,data:dict)->str:
        groups = {}
        order = []

        def add(file:str,line:str):
            if file not in groups:
                groups[file] = []
                order.append(file)
            groups[file].append(line)

        for command in data.get("commands") or []:
            add(command.get("file") or "","- `"+command.get("command","")+"`")

        for entry in data.get("entries") or []:
            file = entry.get("file") or ""
            if entry.get("type") == "scripts":
                for item in entry.get("items") or []:
                    add(file,"- `"+item.get("name","")+"` -> `"+item.get("command","")+"`")
            else:
                for item in entry.get("items") or []:
                    add(file,"- `"+item+"`")

        if not order:
            return "## SECCION DE ENTRADAS\n\nNo se encontraron comandos ni puntos de entrada"

        blocks = []
        for file in order:
            heading = f"**`{file}`**" if file else "**Comandos**"
            blocks.append(heading+"\n\n"+"\n".join(groups[file]))

        return "## SECCION DE ENTRADAS\n\n"+"\n\n".join(blocks)

    #tamaño legible
    def __size(self,value:int)->str:
        if value < 1024:
            return f"{value} B"
        if value < 1024*1024:
            return f"{value/1024:.1f} KB"
        return f"{value/(1024*1024):.1f} MB"


#conversion directa desde la linea de comandos
if __name__ == "__main__":
    #uso: python json_to_md.py <descriptor.json> (<salida.md> opcional)
    if len(sys.argv) < 2:
        print("error: not enough parameters")
        print("correct usage -> python json_to_md.py <descriptor.json> (<output.md> optional)")
        sys.exit(1)

    with open(sys.argv[1],"r",encoding="utf-8") as f:
        descriptor = json.load(f)

    markdown = DescriptorMDConverter().render(descriptor)

    if len(sys.argv) > 2:
        with open(sys.argv[2],"w",encoding="utf-8",newline="\n") as f:
            f.write(markdown)
        print("markdown file generated successfully!!")
    else:
        print(markdown)

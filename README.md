# PyContext - project context descriptor
PyContext is a python cli tool made with the purpose of provide a simple and optimized
project description to AI agents in familiar formats (JSON and MarkDown) all stored
in a context file base.

## Features
PyContext provides the following features:

### Project description
PyContexts reads project directory (in local machine) and builds 3 files with
fetched information, this files contains the next information:

- project.tree: project directory tree without innecesary nodes (files and dirs).
- project_desc.json: a brief project description that contains metadata, file stats,
  dependencies, posible entry points and environment templates in JSON format.
- project_desc.md: this file contains all information mentioned on JSON file but in
  markdown format.

### Local storage base
The ouput files can be stored in an output directory specified directly in cli, provided by `OUTPUT_DIR` environment var all files are stored inside a folder named
as same as project's name.

## Usage
The tool usage is simple just execute the following command in the current directory

`python main.py <project-absolute-path> (<output-absolute-path> optional) (--env-values optional)`

And see the magic make its effect, later you can check the output directory for
contxt files.
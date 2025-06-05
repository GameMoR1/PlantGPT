# PlantUML Generator with ChatGPT

---

## Description

This application is a convenient tool for generating UML diagrams using ChatGPT and visualizing them via PlantUML. It combines the power of artificial intelligence for generating diagram code and the PlantUML tool for creating graphical diagrams based on text descriptions.

The application stores generated diagrams and their codes in a local SQLite database, provides previews of diagrams, and manages generation methodologies and settings.

---

## Key features

- **Generating PlantUML code via ChatGPT**
Enter a text prompt — a description of the desired diagram, and AI will create the correct PlantUML code.

- **Automatic generation of PNG diagrams**
Based on the PlantUML code, the application generates visual diagrams using the local `plantuml.jar`.

- **Storing schemas in SQLite**
All schemas and their codes are stored in the database, including binary image data for quick viewing.

- **Viewing and managing schemas**
View the list of saved schemas, output the code, load the code back into the prompt, export files, delete schemas.

- **Generation methodologies**
Add, view and delete text methodologies that affect schema generation.

- **Application settings**
- Specify the path to `plantuml.jar` or download it automatically
- Configure the image output folder
- Enable/disable prompt enhancement and set your own enhancement templates
- Manage methodologies

---

## Technologies

- Python 3.8+
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — modern GUI
- SQLite — local schema storage
- PlantUML — generating UML diagrams from text
- ChatGPT (via `g4f` library) — generating diagram code
- Pillow — working with images

---

## Installation and launch

1. **Clone the repository:**

```sh
git clone https://github.com/yourusername/plantuml-chatgpt-generator.git
cd plantuml-chatgpt-generator
```

2. **Install dependencies:**

```sh
pip install -r requirements.txt
```

`requirements.txt` should contain:
customtkinter
pillow
g4f

3. **Run the application:**

```sh
python main.py
```

4. **Configure the path to `plantuml.jar` via the "Settings" menu**
If you don't have `plantuml.jar`, use the download button in the settings.

---

## How to use

### Generate a scheme

1. Enter the name of the scheme file (without extension).
2. Select a methodology or leave "Don't select".
3. Enter a description of the scheme in the prompt field.
4. If necessary, enable "Improve prompt" and configure improvement templates in the settings.
5. Click "Generate scheme".
6. After generation, the scheme will be saved in the database and a preview will be displayed.

### Scheme management

- Select a scheme from the list on the left.
- Use the buttons to view the code, load the code into the prompt, export files or delete the scheme.

### Methodologies

- Add new methodologies in the settings — text templates that affect generation.
- Delete selected methodologies through a separate delete window.

### Settings

- Specify the path to `plantuml.jar` or download it.
- Configure the image output folder.
- Enable prompt improvement and set templates.
- Manage methodologies and clear the image folder.
- Reset settings to default values.

---

## Implementation Features

- Schemas are stored in SQLite with binary image data - fast preview without accessing files.
- Schema generation is repeated up to a specified maximum of attempts if PlantUML reports errors.
- The application works autonomously, only Java is required to run `plantuml.jar`.

---

## PlantUML Examples

The application generates code based on [PlantUML](https://plantuml.com), which supports:

- Sequence diagrams
- Class diagrams
- Use case diagrams
- State diagrams
- Activities and more

@startuml
Alice -> Bob: Authentication Request
Bob --> Alice: Authentication Response
@enduml

---

## Contacts and support

If you have any questions or suggestions, create an issue in the repository or contact me by email:

---

*Thank you for using the application!*

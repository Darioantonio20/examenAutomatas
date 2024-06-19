from flask import Flask, request, render_template_string
import re
import ply.lex as lex

app = Flask(__name__)

# Definición de tokens para el analizador léxico
tokens = [
    'PR', 'ID', 'NUM', 'SYM', 'ERR'
]

t_PR = r'\b(Inicio|cadena|proceso|si|ver|Fin)\b'
t_ID = r'\b[a-zA-Z_][a-zA-Z_0-9]*\b'
t_NUM = r'\b\d+\b'
t_SYM = r'[;{}()\[\]=<>!+-/*]'
t_ERR = r'.'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"Carácter ilegal '{t.value[0]}'")
    t.lexer.skip(1)

# Plantilla HTML para mostrar resultados
html_template = '''
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
  <style>
                .contenedor {
                    width: 100%;
                    margin: 20px auto;
                    padding: 20px;
                    background-color: #fff;
                }
                h1 {
                    color: #333;
                }
                textarea {
                    width: 100%;
                    height: 200px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 10px;
                    margin-bottom: 10px;
                    font-size: 16px;
                }
                input[type="submit"] {
                    background-color: #007BFF;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 18px;
                }
                input[type="submit"]:hover {
                    background-color: #0056b3;
                }
                pre {
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    font-size: 16px;
                }
                .error {
                    color: red;
                    font-weight: bold;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                th, td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: center;
                }
                th {
                    background-color: #f2f2f2;
                    color: #333;
                }
            </style>
  <title>Analizador</title>
</head>
<body>
  <div class="container">
    <h1>Analizador</h1>
    <form method="post">
      <textarea name="code" rows="10" cols="50">{{ code }}</textarea><br>
      <input type="submit" value="Analizar">
    </form>
    <div>
      <h2>Analizador Léxico</h2>
      <table>
        <tr>
          <th>Tokens</th><th>PR</th><th>ID</th><th>Números</th><th>Símbolos</th><th>Error</th>
        </tr>
        {% for row in lexical %}
        <tr>
          <td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td><td>{{ row[3] }}</td><td>{{ row[4] }}</td><td>{{ row[5] }}</td>
        </tr>
        {% endfor %}
        <tr>
          <td>Total</td><td>{{ total['PR'] }}</td><td>{{ total['ID'] }}</td><td>{{ total['NUM'] }}</td><td>{{ total['SYM'] }}</td><td>{{ total['ERR'] }}</td>
        </tr>
      </table>
    </div>
    <div>
      <h2>Analizador Sintáctico y Semántico</h2>
      <table>
        <tr>
          <th>Sintáctico</th><th>Semántico</th>
        </tr>
        <tr>
          <td>{{ syntactic }}</td><td>{{ semantic }}</td>
        </tr>
      </table>
    </div>
  </div>
</body>
</html>
'''

def analyze_lexical(code):
    lexer = lex.lex()
    lexer.input(code)
    results = {'PR': 0, 'ID': 0, 'NUM': 0, 'SYM': 0, 'ERR': 0}
    rows = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        row = [''] * 6
        if tok.type in results:
            results[tok.type] += 1
            row[list(results.keys()).index(tok.type)] = 'x'
        rows.append(row)
    return rows, results

def analyze_syntactic(code):
    errors = []

    # Verificar la estructura de "Inicio" y "Fin"
    if not code.startswith("Inicio;"):
        errors.append("El código debe comenzar con 'Inicio;'.")
    if not code.endswith("Fin;"):
        errors.append("El código debe terminar con 'Fin;'.")

    # Verificar la estructura de bloques y sentencias
    if "proceso;" not in code:
        errors.append("Falta la declaración de 'proceso;'.")
    if "si (" in code and not re.search(r"si\s*\(.+\)\s*\{", code):
        errors.append("Estructura incorrecta de 'si'. Debe ser 'si (condición) {'.")
    if "{" in code and "}" not in code:
        errors.append("Falta cerrar un bloque con '}'.")
    if "}" in code and "{" not in code:
        errors.append("Falta abrir un bloque con '{'.")

    
    lines = code.split('\n')
    for i, line in enumerate(lines):
        # Ignorar líneas que no requieren punto y coma
        if line.strip() and not line.strip().endswith(';') and not line.strip().endswith('{') and not line.strip().endswith('}') and "si (" not in line and "Inicio;" not in line and "Fin;" not in line:
            errors.append(f"Falta punto y coma al final de la línea {i + 1}.")

    if not errors:
        return "Sintaxis correcta"
    else:
        return " ".join(errors)

def analyze_semantic(code):
  errors = []
  variable_types = {}

  # Identificar y almacenar los tipos de las variables
  for var_declaration in re.findall(r"\b(cadena|entero)\s+'(\w+)'\s*=\s*(.*);", code):
    var_type, var_name, value = var_declaration
    variable_types[var_name] = var_type
    if var_type == "cadena" and not re.match(r'^".*"$', value):
      errors.append(f"Error semántico en la asignación de '{var_name}'. Debe ser una cadena entre comillas.")
    elif var_type == "entero" and not re.match(r'^\d+$', value):
      errors.append(f"Error semántico en la asignación de '{var_name}'. Debe ser un valor numérico.")

  # Verificar comparaciones lógicas
  logical_checks = re.findall(r"si\s*\((.+)\)", code)
  for check in logical_checks:
    match = re.search(r"(\w+)\s*(==|!=)\s*(\w+|\".*\"|\d+)", check)
    if match:
      left_var, _, right_var = match.groups()
      left_type = variable_types.get(left_var, None)
      right_type = 'cadena' if right_var.startswith('"') or not right_var.isdigit() else 'entero'
      if left_type and right_type and left_type != right_type:
        errors.append(f"Error semántico en la condición 'si ({check})'. No se puede comparar {left_type} con {right_type}.")

  if not errors:
    return "Uso correcto de las estructuras semánticas"
  else:
    return " ".join(errors)

@app.route('/', methods=['GET', 'POST'])
def index():
    code = ''
    lexical_results = []
    total_results = {'PR': 0, 'ID': 0, 'NUM': 0, 'SYM': 0, 'ERR': 0}
    syntactic_result = ''
    semantic_result = ''
    if request.method == 'POST':
        code = request.form['code']
        lexical_results, total_results = analyze_lexical(code)
        syntactic_result = analyze_syntactic(code)
        semantic_result = analyze_semantic(code)
    return render_template_string(html_template, code=code, lexical=lexical_results, total=total_results, syntactic=syntactic_result, semantic=semantic_result)

if __name__ == '__main__':
    app.run(debug=True)

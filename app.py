import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Frame
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import datetime
import os


# Conexão com o banco de dados SQLite
conn = sqlite3.connect('orcamentos.db')
cursor = conn.cursor()

# Atualiza a tabela para garantir que a coluna 'validade' e 'observacoes' existam
cursor.execute('''CREATE TABLE IF NOT EXISTS orcamento
                (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, endereco TEXT, data TEXT, validade INTEGER, valor_total REAL, observacoes TEXT)''')
conn.commit()

# Configuração da empresa
config_file = 'config.txt'

def load_config():
    config_defaults = {'empresa': '', 'logo': '', 'telefone': '', 'endereco': '', 'cnpj': '', 'email': '', 'validade': 30}
    
    if os.path.exists(config_file):
        with open(config_file, 'r') as file:
            lines = file.readlines()
            keys = list(config_defaults.keys())
            for i in range(min(len(lines), len(keys))):
                if keys[i] == 'validade':
                    config_defaults[keys[i]] = int(lines[i].strip())
                else:
                    config_defaults[keys[i]] = lines[i].strip()
    
    return config_defaults

def save_config(empresa, logo, telefone, endereco, cnpj, email, validade):
    with open(config_file, 'w') as file:
        file.write(f"{empresa}\n")
        file.write(f"{logo}\n")
        file.write(f"{telefone}\n")
        file.write(f"{endereco}\n")
        file.write(f"{cnpj}\n")
        file.write(f"{email}\n")
        file.write(f"{validade}\n")

config = load_config()

# Lista para armazenar os itens
itens = []

def adicionar_item():
    item = entry_item.get().strip().capitalize()
    
    try:
        quantidade = int(entry_quantidade.get())
        valor = float(entry_valor.get())
        
        if quantidade <= 0 or valor < 0:
            messagebox.showerror("Erro", "Quantidade deve ser positiva e valor não pode ser negativo.")
            return
        
        itens.append((item, quantidade, valor))
        atualizar_lista()
        clear_item_entries()

    except ValueError:
        messagebox.showerror("Erro", "Por favor, insira valores válidos para quantidade e valor.")

def clear_item_entries():
    entry_item.delete(0, tk.END)
    entry_quantidade.delete(0, tk.END)
    entry_valor.delete(0, tk.END)

def atualizar_lista():
    lista_itens.delete(0, tk.END)
    for item, quantidade, valor in itens:
        lista_itens.insert(tk.END, f"{item} (x{quantidade}): R$ {valor:.2f}")

def salvar_orcamento():
    nome = entry_nome.get().strip().capitalize()
    telefone = entry_telefone.get().strip()
    cidade = entry_cidade.get().strip().capitalize()
    bairro = entry_bairro.get().strip().capitalize()
    
    if not all([nome, telefone, cidade, bairro]):
        messagebox.showerror("Erro", "Todos os campos devem ser preenchidos.")
        return
    
    endereco = f"{cidade}, {bairro}"
    data = datetime.date.today().strftime("%d/%m/%Y")
    
    try:
        validade = int(entry_validade.get())
        if validade < 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Erro", "Validade deve ser um número inteiro não negativo.")
        return
    
    observacoes = entry_observacoes.get("1.0", tk.END).strip()
    valor_total = sum(quantidade * valor for item, quantidade, valor in itens)
    
    cursor.execute("INSERT INTO orcamento (nome, telefone, endereco, data, validade, valor_total, observacoes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (nome, telefone, endereco, data, validade, valor_total, observacoes))
    conn.commit()
    
    # Gera o PDF
    gerar_pdf(cursor.lastrowid, nome, telefone, endereco, data, validade, itens, valor_total, observacoes)
    messagebox.showinfo("Sucesso", "Orçamento salvo e PDF gerado!")
    clear_item_entries()
    itens.clear()
    atualizar_lista()

def gerar_pdf(orcamento_id, nome, telefone, endereco, data, validade, itens, valor_total, observacoes):
    pdf_file = f"orcamento_{orcamento_id}.pdf"
    doc = SimpleDocTemplate(pdf_file, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    estilo_normal = styles['Normal']

    # Estilos personalizados para centralização e alinhamento à direita
    estilo_centralizado = ParagraphStyle(name='Centralizado', parent=estilo_normal, alignment=TA_CENTER)
    estilo_direita = ParagraphStyle(name='Direita', parent=estilo_normal, alignment=TA_RIGHT)

    # Cabeçalho
    header_data = []

    # Adiciona o logo da empresa à esquerda, se existir
    if config['logo'] and os.path.exists(config['logo']):
        logo = Image(config['logo'])
        logo.drawHeight = 5 * cm
        logo.drawWidth = 5 * cm
        header_data.append([logo, ''])

    # Dados da Empresa à direita
    empresa_info = [
        [Paragraph(config['empresa'], estilo_centralizado)],  # Nome da empresa centralizado
        [Paragraph(f"Telefone: {config['telefone']}", estilo_centralizado)],  # Telefone centralizado
        [Paragraph(f"Endereço: {config['endereco']}", estilo_centralizado)],  # Endereço centralizado
        [Paragraph(f"CNPJ: {config['cnpj']}", estilo_centralizado)],  # CNPJ centralizado
        [Paragraph(f"E-mail: {config['email']}", estilo_centralizado)]  # E-mail centralizado
    ]

    # Converte os dados da empresa em uma tabela para melhor alinhamento
    empresa_table = Table(empresa_info)
    empresa_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza todos os elementos
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Alinhamento vertical no meio
        ('PAD', (0, 0), (-1, -1), 5),  # Adiciona padding de 10 unidades a todas as células
    ]))

    # Adiciona os dados da empresa ao cabeçalho à direita
    header_data[-1][1] = empresa_table

    # Cria a tabela para o cabeçalho (logo à esquerda, dados da empresa à direita)
    header_table = Table(header_data, colWidths=[5*cm, None])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 12))

    # Dados do Cliente
    cliente_data = [
        [Paragraph(f"Nome: {nome}", estilo_normal)],
        [Paragraph(f"Telefone: {telefone}", estilo_normal)],
        [Paragraph(f"Endereço: {endereco}", estilo_normal)],
    ]
    cliente_table = Table(cliente_data)
    cliente_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(cliente_table)
    elements.append(Spacer(1, 12))

    # Número do orçamento e data no canto direito
    elements.append(Paragraph(f"Número do Orçamento: {orcamento_id}", estilo_direita))
    elements.append(Paragraph(f"Data: {data}", estilo_direita))
    elements.append(Spacer(1, 12))

    # Tabela de itens
    tabela_dados = [['Serviço', 'Quantidade', 'Valor Unitário (R$)', 'Valor Total (R$)']]
    for item, quantidade, valor in itens:
        total_item = quantidade * valor
        tabela_dados.append([item, str(quantidade), f"{valor:.2f}", f"{total_item:.2f}"])

    tabela = Table(tabela_dados, colWidths=[7 * cm, 2 * cm, 3 * cm, 3 * cm])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(tabela)

    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Total: R$ {valor_total:.2f}", estilo_normal))
    elements.append(Spacer(1, 12))

    # Validade
    elements.append(Paragraph(f"Esse orçamento tem a validade de {validade} dias.", estilo_normal))
    elements.append(Spacer(1, 12))

    # Observações
    elements.append(Paragraph("Observações:", estilo_normal))
    elements.append(Paragraph(observacoes, estilo_normal))
    
    # Gera o PDF
    doc.build(elements)
    print(f"PDF gerado: {pdf_file}")


def escolher_logo():
    logo_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
    if logo_path:
        config['logo'] = logo_path
        save_config(config['empresa'], config['logo'], config['telefone'], config['endereco'], config['cnpj'], config['email'], config['validade'])
        messagebox.showinfo("Sucesso", "Logo atualizado com sucesso!")

def configurar_empresa():
    def salvar_configuracoes():
        empresa = entry_empresa.get().strip()
        logo = config['logo']
        telefone = entry_telefone.get().strip()
        endereco = entry_endereco.get().strip()
        cnpj = entry_cnpj.get().strip()
        email = entry_email.get().strip()
        validade = int(entry_validade.get())
        save_config(empresa, logo, telefone, endereco, cnpj, email, validade)
        messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")

    config_window = tk.Toplevel(root)
    config_window.title("Configurar Empresa")
    
    tk.Label(config_window, text="Nome da Empresa:").grid(row=0, column=0, padx=5, pady=5)
    entry_empresa = tk.Entry(config_window)
    entry_empresa.grid(row=0, column=1, padx=5, pady=5)
    entry_empresa.insert(0, config['empresa'])
    
    tk.Label(config_window, text="Telefone:").grid(row=1, column=0, padx=5, pady=5)
    entry_telefone = tk.Entry(config_window)
    entry_telefone.grid(row=1, column=1, padx=5, pady=5)
    entry_telefone.insert(0, config['telefone'])
    
    tk.Label(config_window, text="Endereço:").grid(row=2, column=0, padx=5, pady=5)
    entry_endereco = tk.Entry(config_window)
    entry_endereco.grid(row=2, column=1, padx=5, pady=5)
    entry_endereco.insert(0, config['endereco'])
    
    tk.Label(config_window, text="CNPJ:").grid(row=3, column=0, padx=5, pady=5)
    entry_cnpj = tk.Entry(config_window)
    entry_cnpj.grid(row=3, column=1, padx=5, pady=5)
    entry_cnpj.insert(0, config['cnpj'])
    
    tk.Label(config_window, text="E-mail:").grid(row=4, column=0, padx=5, pady=5)
    entry_email = tk.Entry(config_window)
    entry_email.grid(row=4, column=1, padx=5, pady=5)
    entry_email.insert(0, config['email'])
    
    tk.Label(config_window, text="Validade (dias):").grid(row=5, column=0, padx=5, pady=5)
    entry_validade = tk.Entry(config_window)
    entry_validade.grid(row=5, column=1, padx=5, pady=5)
    entry_validade.insert(0, config['validade'])
    
    tk.Button(config_window, text="Escolher Logo", command=escolher_logo).grid(row=6, column=0, padx=5, pady=5)
    tk.Button(config_window, text="Salvar Configurações", command=salvar_configuracoes).grid(row=6, column=1, padx=5, pady=5)

def criar_tema_claro(style):
    # Definindo o tema claro
    style.configure('TFrame', background='#ffffff')
    style.configure('TLabel', background='#ffffff', foreground='#000000')
    style.configure('TButton', background='#e0e0e0', foreground='#000000', borderwidth=1)
    style.map('TButton', background=[('active', '#d0d0d0')])
    
    # Atualizando estilos de widgets existentes
    for widget in root.winfo_children():
        if isinstance(widget, ttk.Widget):
            widget.configure(style=widget.winfo_class())

def criar_tema_escuro(style):
    # Definindo o tema escuro
    style.configure('TFrame', background='#2e2e2e')
    style.configure('TLabel', background='#2e2e2e', foreground='#ffffff')
    style.configure('TButton', background='#444444', foreground='#ffffff', borderwidth=1)
    style.map('TButton', background=[('active', '#555555')])
    
    # Atualizando estilos de widgets existentes
    for widget in root.winfo_children():
        if isinstance(widget, ttk.Widget):
            widget.configure(style=widget.winfo_class())

def mudar_tema(tema):
    try:
        if tema == 'light':
            criar_tema_claro(style)
        elif tema == 'dark':
            criar_tema_escuro(style)
        else:
            raise ValueError("Tema desconhecido")
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível aplicar o tema: {e}")


root = tk.Tk()
root.title("Orçamentos")

# Configura o estilo
style = ttk.Style()
criar_tema_claro(style)  # Definindo o tema claro como padrão inicial

# Adicionando uma barra de menus
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

# Menu de Configurações
menu_config = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Configurações", menu=menu_config)
menu_config.add_command(label="Configurar Empresa", command=configurar_empresa)

# Menu de Temas
#menu_temas = tk.Menu(menu_bar, tearoff=0)
#menu_bar.add_cascade(label="Temas", menu=menu_temas)
#temas_disponiveis = ["light", "dark"]
#for tema in temas_disponiveis:
#    menu_temas.add_command(label=tema.capitalize(), command=lambda t=tema: mudar_tema(t))


# Criação dos campos de entrada
tk.Label(root, text="Nome do Cliente:").grid(row=0, column=0, padx=5, pady=5)
entry_nome = tk.Entry(root)
entry_nome.grid(row=0, column=1, padx=5, pady=5)

tk.Label(root, text="Telefone:").grid(row=1, column=0, padx=5, pady=5)
entry_telefone = tk.Entry(root)
entry_telefone.grid(row=1, column=1, padx=5, pady=5)

tk.Label(root, text="Cidade:").grid(row=2, column=0, padx=5, pady=5)
entry_cidade = tk.Entry(root)
entry_cidade.grid(row=2, column=1, padx=5, pady=5)

tk.Label(root, text="Bairro:").grid(row=3, column=0, padx=5, pady=5)
entry_bairro = tk.Entry(root)
entry_bairro.grid(row=3, column=1, padx=5, pady=5)

tk.Label(root, text="Item:").grid(row=4, column=0, padx=5, pady=5)
entry_item = tk.Entry(root)
entry_item.grid(row=4, column=1, padx=5, pady=5)

tk.Label(root, text="Quantidade:").grid(row=5, column=0, padx=5, pady=5)
entry_quantidade = tk.Entry(root)
entry_quantidade.grid(row=5, column=1, padx=5, pady=5)

tk.Label(root, text="Valor Unitário:").grid(row=6, column=0, padx=5, pady=5)
entry_valor = tk.Entry(root)
entry_valor.grid(row=6, column=1, padx=5, pady=5)

tk.Button(root, text="Adicionar Item", command=adicionar_item).grid(row=7, column=0, columnspan=2, padx=5, pady=5)

tk.Label(root, text="Observações:").grid(row=8, column=0, padx=5, pady=5)
entry_observacoes = tk.Text(root, height=4, width=40)
entry_observacoes.grid(row=8, column=1, padx=5, pady=5)

tk.Label(root, text="Validade (dias):").grid(row=9, column=0, padx=5, pady=5)
entry_validade = tk.Entry(root)
entry_validade.grid(row=9, column=1, padx=5, pady=5)

tk.Button(root, text="Salvar Orçamento", command=salvar_orcamento).grid(row=10, column=0, columnspan=2, padx=5, pady=5)

# Lista de itens
lista_itens = tk.Listbox(root, width=50, height=10)
lista_itens.grid(row=1, column=2, rowspan=6, padx=18, pady=4)

root.mainloop()

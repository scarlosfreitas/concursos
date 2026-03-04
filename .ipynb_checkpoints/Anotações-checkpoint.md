# Configuração do ambiente

# Configuração do Projeto
uv init
uv sync

# Instalação do git
choco install git

# Configuração do Git
git init
git add .

git config --global user.email scarlosfreitas@gmail.com
git config --global user.name "Carlos"

git commit -m "first commit"
git branch -M main

git remote add origin https://github.com/scarlosfreitas/concursos.git
git branch -M main
git push -u origin main



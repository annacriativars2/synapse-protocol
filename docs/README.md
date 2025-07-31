# Levo+ - README

## 🚀 Aplicativo de Entregas Rápidas

O **Levo+** é um aplicativo multiplataforma completo que conecta clientes a entregadores autônomos para entregas rápidas de documentos, objetos pequenos e encomendas leves.

### ✨ Funcionalidades Principais

- 📱 **Interface Responsiva** - Funciona em mobile, tablet e desktop
- 🔐 **Sistema de Login** - Perfis separados para clientes e entregadores
- 📦 **Solicitação de Entregas** - Formulário completo com estimativas
- 🗺️ **Rastreamento em Tempo Real** - Acompanhamento da entrega
- 💬 **Chat Integrado** - Comunicação direta entre cliente e entregador
- 💰 **Painel de Ganhos** - Estatísticas completas para entregadores
- 📊 **Histórico Completo** - Registro de todas as entregas
- ⭐ **Sistema de Avaliações** - Feedback mútuo

### 🛠️ Tecnologias

**Frontend:**
- React 18 + Vite
- Tailwind CSS + Shadcn/UI
- React Router DOM
- Lucide Icons

**Backend:**
- Flask + Python 3.11
- SQLAlchemy + SQLite
- Flask-CORS

### 🚀 Como Executar

1. **Backend:**
```bash
cd levo-plus-backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python src/main.py
```

2. **Frontend:**
```bash
cd levo-plus-frontend
pnpm install
pnpm run dev --host
```

3. **Acesso:**
- Frontend: http://localhost:5173
- Backend: http://localhost:5000

### 📱 Como Testar

1. Acesse http://localhost:5173
2. Escolha "Sou Cliente" ou "Sou Entregador"
3. Faça login com qualquer email/senha
4. Explore as funcionalidades:
   - Cliente: Solicitar entrega → Chat → Histórico
   - Entregador: Ver entregas → Ganhos → Chat

### 💬 Sistema de Chat

- Chat em tempo real por entrega
- Mensagens rápidas pré-definidas
- Interface estilo WhatsApp
- Histórico persistente

### 📁 Estrutura do Projeto

```
levo-plus/
├── levo-plus-frontend/    # React App
├── levo-plus-backend/     # Flask API
├── documentacao/          # Docs e especificações
└── assets/               # Imagens e recursos
```

### 🎯 Status do Projeto

✅ **Completo e Funcional**
- Todas as telas implementadas
- Chat funcionando
- Backend integrado
- Design responsivo
- Pronto para deploy

### 📖 Documentação

Consulte `levo_plus_documentacao_final.pdf` para documentação técnica completa, incluindo:
- Manual de deploy
- Especificações técnicas
- Guia de desenvolvimento
- APIs documentadas

---

**Desenvolvido para conectar pessoas através de entregas rápidas e eficientes.**


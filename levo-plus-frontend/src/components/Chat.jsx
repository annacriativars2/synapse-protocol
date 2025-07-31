import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft, Send, MessageCircle, Clock } from 'lucide-react'

const Chat = () => {
  const { deliveryId } = useParams()
  const navigate = useNavigate()
  const messagesEndRef = useRef(null)
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender_id: 2,
      sender_name: 'João Silva',
      message: 'Olá! Estou a caminho da retirada.',
      message_type: 'text',
      created_at: '2024-12-11T14:10:00Z',
      isOwn: false
    },
    {
      id: 2,
      sender_id: 1,
      sender_name: 'Cliente',
      message: 'Perfeito! Obrigado.',
      message_type: 'text',
      created_at: '2024-12-11T14:11:00Z',
      isOwn: true
    },
    {
      id: 3,
      sender_id: 2,
      sender_name: 'João Silva',
      message: 'Cheguei no local de retirada',
      message_type: 'predefined',
      created_at: '2024-12-11T14:15:00Z',
      isOwn: false
    }
  ])
  
  const [quickMessages] = useState([
    "Estou a caminho da retirada",
    "Cheguei no local de retirada",
    "Item coletado, a caminho da entrega",
    "Chegando no local de entrega",
    "Não encontrei o endereço",
    "Pode deixar na portaria?",
    "Obrigado!"
  ])
  
  const [showQuickMessages, setShowQuickMessages] = useState(false)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async (messageText, messageType = 'text') => {
    if (!messageText.trim()) return

    const newMessage = {
      id: messages.length + 1,
      sender_id: 1, // Current user ID
      sender_name: 'Você',
      message: messageText,
      message_type: messageType,
      created_at: new Date().toISOString(),
      isOwn: true
    }

    setMessages(prev => [...prev, newMessage])
    setMessage('')
    setShowQuickMessages(false)

    // Simulate API call
    try {
      await fetch(`http://localhost:5000/api/chat/${deliveryId}/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sender_id: 1,
          message: messageText,
          message_type: messageType
        }),
      })
    } catch (error) {
      console.error('Error sending message:', error)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    sendMessage(message)
  }

  const handleQuickMessage = (quickMsg) => {
    sendMessage(quickMsg, 'predefined')
  }

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="min-h-screen levo-bg-dark flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 levo-bg-card border-b border-gray-600">
        <div className="flex items-center">
          <Button
            onClick={() => navigate(`/tracking/${deliveryId}`)}
            className="levo-button-secondary mr-4"
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-lg font-bold text-white">Chat da Entrega</h1>
            <p className="text-sm levo-text-secondary">Entrega #{deliveryId}</p>
          </div>
        </div>
        <MessageCircle className="w-6 h-6 levo-text-primary" />
      </div>

      {/* Messages Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.isOwn ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                msg.isOwn
                  ? 'levo-primary text-black'
                  : 'levo-bg-card text-white border border-gray-600'
              }`}
            >
              <div className="text-sm">{msg.message}</div>
              <div className={`text-xs mt-1 flex items-center ${
                msg.isOwn ? 'text-gray-700' : 'levo-text-secondary'
              }`}>
                <Clock className="w-3 h-3 mr-1" />
                {formatTime(msg.created_at)}
                {msg.message_type === 'predefined' && (
                  <span className="ml-2 text-xs opacity-75">• Mensagem rápida</span>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Messages */}
      {showQuickMessages && (
        <div className="p-4 levo-bg-card border-t border-gray-600">
          <div className="mb-3">
            <h3 className="text-sm font-semibold text-white mb-2">Mensagens Rápidas</h3>
            <div className="grid grid-cols-1 gap-2">
              {quickMessages.map((quickMsg, index) => (
                <Button
                  key={index}
                  onClick={() => handleQuickMessage(quickMsg)}
                  className="text-left justify-start levo-button-secondary text-sm h-auto py-2"
                >
                  {quickMsg}
                </Button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="p-4 levo-bg-card border-t border-gray-600">
        <div className="flex items-center space-x-2 mb-2">
          <Button
            onClick={() => setShowQuickMessages(!showQuickMessages)}
            className={`levo-button-secondary text-xs ${
              showQuickMessages ? 'levo-primary' : ''
            }`}
          >
            Mensagens Rápidas
          </Button>
        </div>
        
        <form onSubmit={handleSubmit} className="flex items-center space-x-2">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Digite sua mensagem..."
            className="levo-input flex-1"
          />
          <Button
            type="submit"
            disabled={!message.trim()}
            className="levo-button-primary"
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}

export default Chat

